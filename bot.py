"""
Bot de veille des opportunités stages/discovery trading.

Pipeline :
  1. Scrape les pages careers de firms.yaml
  2. Lit les emails (Google Alerts + LinkedIn) via email_sources.py si configuré
  3. Pour chaque changement, demande à Claude d'analyser et de classifier
     l'urgence (apply_now / prepare_for_open / add_to_watchlist)
  4. Notifie sur Telegram + enregistre dans state/opportunities.json
  5. Génère le site web docs/index.html (servi par GitHub Pages)
"""
import os
import json
import hashlib
import time
import requests
import yaml
from pathlib import Path
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from anthropic import Anthropic

import html_renderer

STATE_FILE = Path("state/hashes.json")
OPPORTUNITIES_FILE = Path("state/opportunities.json")
PROFILE_FILE = Path("profile.md")
FIRMS_FILE = Path("firms.yaml")
CLAUDE_MODEL = "claude-sonnet-4-6"

OPPORTUNITY_RETENTION_DAYS = 60

KEYWORDS = [
    "intern", "graduate", "discovery", "spring week", "kickstarter",
    "launchpad", "futurefocus", "future focus", "explore", "preview",
    "insight", "in focus", "qtc", "student", "early career",
    "campus", "off-cycle", "off cycle", "2027", "2028", "2029",
    "trader", "quant", "research", "engineer", "developer", "software",
]


# ============================================================
# Scraping
# ============================================================

def fetch_page(url):
    """Récupère la page et extrait uniquement les lignes pertinentes."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        )
    }
    r = requests.get(url, headers=headers, timeout=25)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()

    main = soup.find("main") or soup.find(id="content") or soup.body
    if main is None:
        return ""

    text = main.get_text(separator="\n", strip=True)
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]

    relevant = [
        ln for ln in lines
        if any(kw in ln.lower() for kw in KEYWORDS) and len(ln) < 300
    ]

    links = []
    for a in main.find_all("a", href=True):
        label = a.get_text(strip=True)
        if label and any(kw in label.lower() for kw in KEYWORDS):
            href = a["href"]
            if href.startswith("/"):
                href = urljoin(url, href)
            links.append(f"{label} → {href}")

    combined = "\n".join(relevant + ["---LINKS---"] + links)
    return combined


def hash_content(content):
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# ============================================================
# State (hashes par firme)
# ============================================================

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def save_state(state):
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ============================================================
# Opportunities (historique pour le site web)
# ============================================================

def load_opportunities():
    if OPPORTUNITIES_FILE.exists():
        try:
            return json.loads(OPPORTUNITIES_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
    return []


def save_opportunities(opps):
    OPPORTUNITIES_FILE.parent.mkdir(exist_ok=True)
    OPPORTUNITIES_FILE.write_text(
        json.dumps(opps, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def record_opportunity(source_label, source_kind, fallback_url, analysis):
    """Stocke (ou met à jour) l'opportunité dans opportunities.json.
    Garde un historique de OPPORTUNITY_RETENTION_DAYS jours.

    Dedup par (firm, program_name). On préfère analysis.firm si Claude l'a extrait,
    sinon on retombe sur source_label.
    """
    opps = load_opportunities()
    firm = analysis.get("firm") or source_label
    program = analysis.get("program_name") or "Programme non spécifié"
    opp_id = hashlib.sha256(f"{firm}::{program}".encode("utf-8")).hexdigest()[:16]
    now = datetime.now(timezone.utc).isoformat()

    existing = next((o for o in opps if o.get("id") == opp_id), None)
    first_seen = existing.get("first_seen", now) if existing else now

    opp = {
        "id": opp_id,
        "firm": firm,
        "program_name": analysis.get("program_name"),
        "deadline": analysis.get("deadline"),
        "deadline_iso": analysis.get("deadline_iso"),
        "location": analysis.get("location"),
        "eligibility": analysis.get("eligibility"),
        "format": analysis.get("format"),
        "key_info": analysis.get("key_info"),
        "apply_url": analysis.get("apply_url") or fallback_url,
        "priority_score": analysis.get("priority_score"),
        "pre_application": analysis.get("pre_application"),
        "action_required": analysis.get("action_required") or "add_to_watchlist",
        "reasoning": analysis.get("reasoning"),
        "source": source_kind,  # ex: "careers_page", "google_alerts", "linkedin_alerts"
        "first_seen": first_seen,
        "last_seen": now,
    }

    opps = [o for o in opps if o.get("id") != opp_id]
    opps.append(opp)

    # Nettoie l'historique
    cutoff = (datetime.now(timezone.utc) - timedelta(days=OPPORTUNITY_RETENTION_DAYS)).isoformat()
    opps = [o for o in opps if o.get("last_seen", "") >= cutoff]

    save_opportunities(opps)


# ============================================================
# Analyse Claude
# ============================================================

def analyze_with_claude(client, source_label, old_content, new_content, profile):
    """Demande à Claude d'analyser le changement et de générer une pré-application."""
    is_first_run = not old_content

    prompt = f"""Tu es un assistant qui aide un étudiant EPFL / futur ETH Master à détecter et postuler à des programmes de stage/discovery dans les firms de quant trading.

PROFIL DE L'ÉTUDIANT :
{profile}

SOURCE : {source_label}

{"=== PREMIÈRE ANALYSE (pas d'ancien contenu) ===" if is_first_run else "ANCIEN CONTENU :"}
{old_content if old_content else "(N/A)"}

NOUVEAU CONTENU :
{new_content}

TÂCHE :
1. Identifie s'il y a une opportunité (programme discovery, internship, spring week, kickstarter, graduate role, off-cycle, etc.) qui correspond au profil.
2. {"Comme c'est la première analyse, signale toutes les opportunités pertinentes actuellement visibles." if is_first_run else "Compare l'ancien et le nouveau contenu : signale uniquement les NOUVEAUTÉS, pas ce qui était déjà là."}
3. Détermine l'**action_required** :
   - "apply_now" : candidature OUVERTE, deadline visible et imminente (< 4 semaines) → postuler maintenant
   - "prepare_for_open" : programme annoncé pour ouverture future (typiquement quelques mois) → préparer CV / cover letter / questions techniques à l'avance
   - "add_to_watchlist" : info encore vague (pas de deadline claire, programme à venir) → simplement à surveiller
   - "not_relevant" : changement détecté mais pas d'opportunité pertinente pour le profil
4. Extrait toutes les infos disponibles (deadline, éligibilité, format, localisation, nom officiel de la firme dans `firm`).
5. Dans `key_info`, sois CONCRET sur quoi préparer ET quand : CV à jour, cover letter, online assessment (HackerRank/Codility), video interview HireVue, math/probability test, case study, etc. + timing par rapport à aujourd'hui.
6. Si pertinent (apply_now ou prepare_for_open), génère une PRÉ-APPLICATION : lettre de motivation de ~180 mots, en anglais (sauf firme francophone), personnalisée pour CE programme spécifique. Valorise les forces concrètes du profil (Pictet 2nd place, IMC Prosperity Top 1%, recherche Malamud sur factor models / GARCH, présidence Financial Association EPFL avec speakers Jane Street / Jump / HRT, 6/6 en stats, double EPFL→ETH, etc.).
7. Score la priorité de 1 à 10 selon : pertinence (profil maths/CS), prestige de la firme, urgence de la deadline, alignement géographique (Londres > Amsterdam/EU > reste, pas de US).

Réponds UNIQUEMENT en JSON valide, sans markdown, sans backticks. Schéma :
{{
  "is_new_opportunity": true ou false,
  "action_required": "apply_now" | "prepare_for_open" | "add_to_watchlist" | "not_relevant",
  "firm": "Nom officiel de la firme (ex: Jane Street)" ou null,
  "program_name": "nom du programme" ou null,
  "deadline": "date ou période" ou null,
  "deadline_iso": "YYYY-MM-DD si une date concrète est identifiable (au moins année et mois ; jour = 01 si manquant), sinon null",
  "location": "ville(s)" ou null,
  "eligibility": "critères clés" ou null,
  "format": "durée, in-person/remote, etc." ou null,
  "key_info": "QUOI préparer concrètement et QUAND, 2-3 phrases max" ou null,
  "apply_url": "URL directe de candidature si trouvée" ou null,
  "priority_score": entier 1-10 ou null,
  "pre_application": "lettre de motivation ~180 mots" ou null,
  "reasoning": "pourquoi cette opportunité (ou pas) en max 80 mots"
}}"""

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2500,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip().rstrip("`").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  ⚠ JSON invalide pour {source_label}: {e}")
        print(f"  Raw: {raw[:500]}")
        return {"is_new_opportunity": False, "reasoning": "JSON parse error"}


# ============================================================
# Telegram
# ============================================================

def send_telegram(token, chat_id, message):
    """Envoie un message Telegram, découpé si > 4000 chars."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for i in range(0, len(message), 4000):
        chunk = message[i:i + 4000]
        r = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "Markdown",
                "disable_web_page_preview": False,
            },
            timeout=15,
        )
        if not r.ok:
            print(f"  ⚠ Telegram error: {r.status_code} {r.text[:200]}")
            requests.post(
                url,
                json={"chat_id": chat_id, "text": chunk},
                timeout=15,
            )


def md_escape(s):
    """Échappe les caractères Markdown problématiques pour Telegram."""
    if not s:
        return ""
    return str(s).replace("_", r"\_").replace("*", r"\*").replace("[", r"\[")


ACTION_EMOJI = {
    "apply_now": "🔥",
    "prepare_for_open": "⏳",
    "add_to_watchlist": "👀",
}
ACTION_LABEL = {
    "apply_now": "À POSTULER",
    "prepare_for_open": "À PRÉPARER",
    "add_to_watchlist": "WATCHLIST",
}


def format_message(source_label, fallback_url, analysis):
    action = analysis.get("action_required") or "add_to_watchlist"
    emoji = ACTION_EMOJI.get(action, "📍")
    label = ACTION_LABEL.get(action, "OPPORTUNITÉ")
    score = analysis.get("priority_score") or 0
    firm = analysis.get("firm") or source_label

    parts = [f"{emoji} *{label} — {md_escape(firm)}*", ""]

    if analysis.get("program_name"):
        parts.append(f"*Programme :* {md_escape(analysis['program_name'])}")
    if analysis.get("deadline"):
        parts.append(f"*Deadline :* {md_escape(analysis['deadline'])}")
    if analysis.get("location"):
        parts.append(f"*Localisation :* {md_escape(analysis['location'])}")
    if analysis.get("eligibility"):
        parts.append(f"*Éligibilité :* {md_escape(analysis['eligibility'])}")
    if analysis.get("format"):
        parts.append(f"*Format :* {md_escape(analysis['format'])}")
    parts.append(f"*Score :* {score}/10")
    parts.append("")

    if analysis.get("key_info"):
        parts.append(f"*À faire :*\n{md_escape(analysis['key_info'])}\n")

    if analysis.get("pre_application"):
        parts.append(f"*Pré-application :*\n{md_escape(analysis['pre_application'])}\n")

    apply_url = analysis.get("apply_url") or fallback_url
    if apply_url:
        parts.append(f"🔗 {apply_url}")
    return "\n".join(parts)


# ============================================================
# Main
# ============================================================

def main():
    api_key = os.environ["ANTHROPIC_API_KEY"]
    tg_token = os.environ["TELEGRAM_TOKEN"]
    tg_chat = os.environ["TELEGRAM_CHAT_ID"]

    client = Anthropic(api_key=api_key)
    state = load_state()
    profile = PROFILE_FILE.read_text(encoding="utf-8")
    firms = yaml.safe_load(FIRMS_FILE.read_text(encoding="utf-8"))

    notified = 0
    errors = 0

    print(f"=== Scan de {len(firms)} firms ===\n")

    for firm in firms:
        name = firm["name"]
        url = firm["url"]
        print(f"→ {name}")

        try:
            filtered = fetch_page(url)
            if not filtered:
                print("  page vide, skip")
                continue

            new_hash = hash_content(filtered)
            previous = state.get(name, {})
            old_hash = previous.get("hash")
            old_content = previous.get("content", "")

            if new_hash == old_hash:
                print("  pas de changement")
                continue

            print("  changement détecté → analyse Claude")
            analysis = analyze_with_claude(client, name, old_content, filtered, profile)

            action = analysis.get("action_required") or "add_to_watchlist"

            if analysis.get("is_new_opportunity") and action != "not_relevant":
                msg = format_message(name, url, analysis)
                send_telegram(tg_token, tg_chat, msg)
                record_opportunity(name, "careers_page", url, analysis)
                notified += 1
                print(f"  ✓ notifié [{action}] score {analysis.get('priority_score')}")
            else:
                print(f"  pas pertinent : {analysis.get('reasoning', '')[:80]}")

            state[name] = {"hash": new_hash, "content": filtered[:6000]}
            time.sleep(1)

        except requests.HTTPError as e:
            print(f"  ⚠ HTTP {e.response.status_code}")
            errors += 1
        except Exception as e:
            print(f"  ⚠ erreur : {type(e).__name__}: {e}")
            errors += 1

    save_state(state)

    # ====== Sources email (Google Alerts + LinkedIn Jobs) ======
    print("\n=== Sources email ===")
    try:
        from email_sources import process_email_sources
        email_notified = process_email_sources(
            client=client,
            profile=profile,
            analyze_fn=analyze_with_claude,
            format_fn=format_message,
            send_fn=send_telegram,
            record_fn=record_opportunity,
            tg_token=tg_token,
            tg_chat=tg_chat,
        )
        notified += email_notified
    except ImportError:
        print("⊘ email_sources non disponible")
    except Exception as e:
        print(f"⚠ Erreur sources email : {type(e).__name__}: {e}")

    # ====== Génération du site web statique ======
    print("\n=== Génération du site web ===")
    try:
        html_renderer.generate_site()
    except Exception as e:
        print(f"⚠ Erreur génération site : {type(e).__name__}: {e}")

    print(f"\n=== Fini. {notified} notif(s), {errors} erreur(s). ===")


if __name__ == "__main__":
    main()
