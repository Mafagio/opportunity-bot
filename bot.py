"""
Bot de veille des opportunités stages/discovery trading.
Tourne quotidiennement via GitHub Actions, détecte les changements
sur les pages careers, analyse avec Claude, notifie sur Telegram.
"""
import os
import json
import hashlib
import time
import requests
import yaml
from pathlib import Path
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from anthropic import Anthropic

STATE_FILE = Path("state/hashes.json")
PROFILE_FILE = Path("profile.md")
FIRMS_FILE = Path("firms.yaml")
CLAUDE_MODEL = "claude-sonnet-4-6"

KEYWORDS = [
    "intern", "graduate", "discovery", "spring week", "kickstarter",
    "launchpad", "futurefocus", "future focus", "explore", "preview",
    "insight", "in focus", "qtc", "student", "early career",
    "campus", "off-cycle", "off cycle", "2027", "2028", "2029",
    "trader", "quant", "research", "engineer", "developer", "software",
]


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


def analyze_with_claude(client, firm_name, old_content, new_content, profile):
    """Demande à Claude d'analyser le changement et de générer une pré-application."""
    is_first_run = not old_content

    prompt = f"""Tu es un assistant qui aide un étudiant EPFL à détecter et postuler à des programmes de stage/discovery dans les firms de quant trading.

PROFIL DE L'ÉTUDIANT :
{profile}

FIRME : {firm_name}

{"=== PREMIÈRE ANALYSE (pas d'ancien contenu) ===" if is_first_run else "ANCIEN CONTENU DE LA PAGE CAREERS :"}
{old_content if old_content else "(N/A)"}

NOUVEAU CONTENU DE LA PAGE CAREERS :
{new_content}

TÂCHE :
1. Identifie s'il y a une opportunité (programme discovery, internship, spring week, kickstarter, graduate role, etc.) qui correspond au profil de l'étudiant et dont la candidature est ACTUELLEMENT OUVERTE (ou ouvre bientôt).
2. {"Comme c'est la première analyse, signale toutes les opportunités pertinentes actuellement visibles." if is_first_run else "Compare l'ancien et le nouveau contenu : signale uniquement les NOUVEAUTÉS, pas ce qui était déjà là."}
3. Extrait toutes les infos disponibles (deadline, éligibilité, format, localisation).
4. Génère une PRÉ-APPLICATION : lettre de motivation de ~180 mots, en anglais (sauf si la firme est francophone), personnalisée pour CE programme spécifique, qui met en avant les forces du profil EPFL.
5. Score la priorité de 1 à 10 selon : pertinence (profil maths/CS), prestige de la firme, urgence de la deadline, alignement géographique (Europe/UK préféré).

Réponds UNIQUEMENT en JSON valide, sans markdown, sans backticks. Schéma :
{{
  "is_new_opportunity": true ou false,
  "program_name": "nom du programme" ou null,
  "deadline": "date ou période" ou null,
  "location": "ville(s)" ou null,
  "eligibility": "critères clés" ou null,
  "format": "durée, in-person/remote, etc." ou null,
  "key_info": "autres infos importantes (2-3 phrases max)" ou null,
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
        print(f"  ⚠ JSON invalide pour {firm_name}: {e}")
        print(f"  Raw: {raw[:500]}")
        return {"is_new_opportunity": False, "reasoning": "JSON parse error"}


def send_telegram(token, chat_id, message):
    """Envoie un message Telegram, découpé si > 4000 chars."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for i in range(0, len(message), 4000):
        chunk = message[i : i + 4000]
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


def format_message(firm_name, fallback_url, analysis):
    score = analysis.get("priority_score") or 0
    if score >= 8:
        emoji = "🔥"
    elif score >= 5:
        emoji = "⭐"
    else:
        emoji = "📍"

    parts = [f"{emoji} *Nouvelle opportunité — {md_escape(firm_name)}*", ""]

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
    parts.append(f"*Score priorité :* {score}/10")
    parts.append("")

    if analysis.get("key_info"):
        parts.append(f"*Info clé :*\n{md_escape(analysis['key_info'])}\n")

    if analysis.get("pre_application"):
        parts.append(f"*Pré-application :*\n{md_escape(analysis['pre_application'])}\n")

    apply_url = analysis.get("apply_url") or fallback_url
    parts.append(f"🔗 {apply_url}")
    return "\n".join(parts)


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

            if analysis.get("is_new_opportunity"):
                msg = format_message(name, url, analysis)
                send_telegram(tg_token, tg_chat, msg)
                notified += 1
                print(f"  ✓ notifié (score {analysis.get('priority_score')})")
            else:
                print(f"  changement non pertinent : {analysis.get('reasoning', '')[:80]}")

            state[name] = {"hash": new_hash, "content": filtered[:6000]}
            time.sleep(1)

        except requests.HTTPError as e:
            print(f"  ⚠ HTTP {e.response.status_code}")
            errors += 1
        except Exception as e:
            print(f"  ⚠ erreur : {type(e).__name__}: {e}")
            errors += 1

    save_state(state)
    print(f"\nFini. {notified} notif(s), {errors} erreur(s).")


if __name__ == "__main__":
    main()
