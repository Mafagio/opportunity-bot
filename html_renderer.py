"""
Générateur du site web statique — SPA 3 pages.

Pages :
  - Explorer : toutes les opportunités, groupées par fenêtre temporelle, filtrables par catégorie
  - Candidatures : pipeline de mes applications (statut + étape), tracker tout en localStorage
  - Favoris : opportunités sauvegardées, click sur card = modal détail + pré-application

Le state utilisateur (favoris, statuts candidatures) vit en localStorage (par-appareil).
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

OPPORTUNITIES_FILE = Path("state/opportunities.json")
OUTPUT_FILE = Path("docs/index.html")


# Fallback metadata si Claude n'a pas renseigné firm_category
# (utile pour les anciennes opportunités générées avant l'ajout du champ)
FIRM_CATEGORY_FALLBACK = {
    # Quant HFT / Market Making / Prop / Research
    "Jane Street": "quant", "Optiver Europe": "quant", "Optiver": "quant",
    "IMC": "quant", "IMC Trading": "quant",
    "Hudson River Trading": "quant", "HRT": "quant",
    "Jump Trading": "quant", "DRW": "quant",
    "Five Rings": "quant", "Five Rings Capital": "quant",
    "SIG (Susquehanna)": "quant", "SIG": "quant", "Susquehanna": "quant",
    "XTX Markets": "quant", "XTX": "quant",
    "Tower Research Capital": "quant", "Tower Research": "quant",
    "Akuna Capital": "quant", "Akuna": "quant",
    "Old Mission Capital": "quant", "Tibra Capital": "quant",
    "Citadel Securities": "quant", "Citadel": "quant",
    "Flow Traders": "quant", "Da Vinci Trading": "quant",
    "Maven Securities": "quant", "Vatic Investments": "quant",
    "D.E. Shaw": "quant", "Two Sigma": "quant",
    "G-Research": "quant", "WorldQuant": "quant",
    "AQR Capital": "quant", "AQR": "quant",
    "Marshall Wace": "quant", "Capula Investment Management": "quant",
    "Quadrature Capital": "quant", "GSA Capital": "quant",
    "Trexquant": "quant", "Squarepoint Capital": "quant",
    "Verition Fund Management": "quant", "The Voleon Group": "quant", "Voleon": "quant",
    "Keyrock": "quant", "DV Trading": "quant", "Wincent": "quant",
    # Hedge funds
    "Schonfeld": "hedge_fund", "Brevan Howard": "hedge_fund",
    "Man Group": "hedge_fund", "Millennium": "hedge_fund",
    "BlueCrest Capital": "hedge_fund", "Lansdowne Partners": "hedge_fund",
    # Bulge brackets
    "Goldman Sachs": "bulge_bracket", "Goldman Sachs (Students)": "bulge_bracket",
    "JPMorgan": "bulge_bracket", "JPMorgan (Students)": "bulge_bracket", "JP Morgan": "bulge_bracket",
    "Morgan Stanley": "bulge_bracket", "Barclays": "bulge_bracket",
    "Deutsche Bank": "bulge_bracket", "BNP Paribas": "bulge_bracket",
    "Nomura": "bulge_bracket", "Macquarie": "bulge_bracket",
    "UBS": "bulge_bracket", "HSBC": "bulge_bracket", "Citi": "bulge_bracket",
    "BofA": "bulge_bracket", "Bank of America": "bulge_bracket",
    "Societe Generale": "bulge_bracket",
    # Asset managers / Private banking
    "Pictet Asset Management": "asset_manager", "Pictet": "asset_manager",
    "Partners Group": "asset_manager",
    "BlackRock": "asset_manager", "State Street Global Advisors": "asset_manager",
    "State Street": "asset_manager", "Vanguard": "asset_manager", "PIMCO": "asset_manager",
    "Vontobel": "asset_manager", "Lombard Odier": "asset_manager",
    "Julius Baer": "asset_manager",
    # Other
    "Swiss Re": "other", "Zurich Insurance Group": "other", "Zurich Insurance": "other",
    "Banque Heritage": "other",
    "QuantNet Forum": "other", "RateMyPlacement (Finance UK)": "other",
}


CATEGORY_LABELS = {
    "quant": "Quant",
    "hedge_fund": "Hedge Fund",
    "bulge_bracket": "Bulge Bracket",
    "asset_manager": "Asset Manager",
    "other": "Autres",
}


# Mapping firme → domaine pour récupérer les logos via Clearbit
# (https://logo.clearbit.com/{domain})
FIRM_DOMAINS = {
    # Quant HFT / Market Making
    "Jane Street": "janestreet.com",
    "Optiver": "optiver.com", "Optiver Europe": "optiver.com",
    "IMC": "imc.com", "IMC Trading": "imc.com",
    "Hudson River Trading": "hudsonrivertrading.com", "HRT": "hudsonrivertrading.com",
    "Jump Trading": "jumptrading.com",
    "DRW": "drw.com",
    "Five Rings": "fiverings.com", "Five Rings Capital": "fiverings.com",
    "SIG": "sig.com", "Susquehanna": "sig.com", "SIG (Susquehanna)": "sig.com",
    "XTX": "xtxmarkets.com", "XTX Markets": "xtxmarkets.com",
    "Tower Research": "tower-research.com", "Tower Research Capital": "tower-research.com",
    "Akuna": "akunacapital.com", "Akuna Capital": "akunacapital.com",
    "Old Mission Capital": "oldmissioncapital.com",
    "Tibra Capital": "tibra.com",
    "Citadel Securities": "citadelsecurities.com",
    "Citadel": "citadel.com",
    "Flow Traders": "flowtraders.com",
    "Da Vinci Trading": "davincitrading.com",
    "Maven Securities": "mavensecurities.com",
    "Vatic Investments": "vaticinvestments.com",
    "Wincent": "wincent.io",
    "DV Trading": "dvtrading.co",
    "Keyrock": "keyrock.com",
    # Quant Research
    "D.E. Shaw": "deshaw.com",
    "Two Sigma": "twosigma.com",
    "G-Research": "gresearch.com",
    "WorldQuant": "worldquant.com",
    "AQR": "aqr.com", "AQR Capital": "aqr.com",
    "Marshall Wace": "mwam.com",
    "Capula Investment Management": "capula.com",
    "Quadrature Capital": "quadraturecapital.com",
    "GSA Capital": "gsacapital.com",
    "Trexquant": "trexquant.com",
    "Squarepoint Capital": "squarepoint-capital.com",
    "Verition Fund Management": "veritionfund.com",
    "The Voleon Group": "voleon.com", "Voleon": "voleon.com",
    # Hedge funds
    "Schonfeld": "schonfeld.com",
    "Brevan Howard": "brevanhoward.com",
    "Man Group": "man.com",
    "Millennium": "mlp.com",
    "BlueCrest Capital": "bluecrestcapital.com",
    "Lansdowne Partners": "lansdownepartners.com",
    "Hartree Partners": "hartreepartners.com",
    # Bulge brackets
    "Goldman Sachs": "goldmansachs.com",
    "Goldman Sachs (Students)": "goldmansachs.com",
    "JPMorgan": "jpmorgan.com", "JPMorgan (Students)": "jpmorgan.com", "JP Morgan": "jpmorgan.com",
    "Morgan Stanley": "morganstanley.com",
    "Barclays": "barclays.com",
    "Deutsche Bank": "db.com",
    "BNP Paribas": "bnpparibas.com",
    "Nomura": "nomura.com",
    "Macquarie": "macquarie.com",
    "UBS": "ubs.com",
    "HSBC": "hsbc.com",
    "Citi": "citi.com", "Citigroup": "citi.com",
    "Bank of America": "bofa.com", "BofA": "bofa.com",
    "Societe Generale": "societegenerale.com",
    # Asset managers
    "BlackRock": "blackrock.com",
    "State Street": "statestreet.com",
    "State Street Global Advisors": "ssga.com",
    "Vanguard": "vanguard.com",
    "PIMCO": "pimco.com",
    "Pictet": "pictet.com", "Pictet Asset Management": "pictet.com",
    "Partners Group": "partnersgroup.com",
    "Vontobel": "vontobel.com",
    "Lombard Odier": "lombardodier.com",
    "Julius Baer": "juliusbaer.com",
    # Other
    "Swiss Re": "swissre.com",
    "Zurich Insurance": "zurich.com", "Zurich Insurance Group": "zurich.com",
    "Banque Heritage": "heritage.ch",
}


def get_firm_domain(firm):
    """Retourne le domaine pour Clearbit, ou None pour fallback initials."""
    if not firm:
        return None
    return FIRM_DOMAINS.get(firm)


def get_category(opp):
    """Récupère la catégorie d'une opportunité (Claude > fallback dict > 'other')."""
    cat = opp.get("firm_category")
    if cat and cat in CATEGORY_LABELS:
        return cat
    firm = opp.get("firm", "")
    if firm in FIRM_CATEGORY_FALLBACK:
        return FIRM_CATEGORY_FALLBACK[firm]
    return "other"


def normalize_opportunities(opps):
    """Nettoie / enrichit chaque opportunité avant injection dans le HTML."""
    out = []
    for o in opps:
        cat = get_category(o)
        firm = o.get("firm") or "?"
        out.append({
            "id": o.get("id", ""),
            "firm": firm,
            "firm_domain": get_firm_domain(firm),
            "program_name": o.get("program_name"),
            "deadline": o.get("deadline"),
            "deadline_iso": o.get("deadline_iso"),
            "start_date": o.get("start_date"),
            "start_date_iso": o.get("start_date_iso"),
            "location": o.get("location"),
            "eligibility": o.get("eligibility"),
            "format": o.get("format"),
            "key_info": o.get("key_info"),
            "apply_url": o.get("apply_url"),
            "priority_score": o.get("priority_score") or 0,
            "firm_category": cat,
            "firm_category_label": CATEGORY_LABELS.get(cat, "Autres"),
            "pre_application": o.get("pre_application"),
            "action_required": o.get("action_required") or "add_to_watchlist",
            "source": o.get("source"),
            "first_seen": o.get("first_seen"),
            "last_seen": o.get("last_seen"),
        })
    return out


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow, noarchive, nosnippet">
<meta name="googlebot" content="noindex, nofollow">
<title>Opportunités · Quant Tracker</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Geist+Mono:wght@400;500&display=swap" rel="stylesheet">
<script>
// Restore theme before render to prevent flash
(function() {
  try {
    var t = localStorage.getItem("qt_theme_v1");
    if (t === "light") document.documentElement.setAttribute("data-theme", "light");
  } catch (e) {}
})();
</script>
<style>
:root {
  --bg-0: #0a0a0a;
  --bg-1: #111111;
  --bg-2: #161616;
  --bg-3: #1c1c1c;
  --bg-hover: #1f1f1f;
  --border-subtle: #1f1f1f;
  --border: #262626;
  --border-strong: #333333;
  --text-1: #f5f5f5;
  --text-2: #a3a3a3;
  --text-3: #737373;
  --text-4: #525252;
  --red: #ef4444;
  --red-soft: rgba(239, 68, 68, 0.12);
  --orange: #f59e0b;
  --orange-soft: rgba(245, 158, 11, 0.12);
  --green: #22c55e;
  --green-soft: rgba(34, 197, 94, 0.12);
  --blue: #3b82f6;
  --blue-soft: rgba(59, 130, 246, 0.12);
  --accent: #f5f5f5;
  --radius: 10px;
  --radius-lg: 14px;
  /* Catégories — couleurs distinctives mais sobres */
  --cat-quant: #06b6d4;          /* cyan */
  --cat-quant-soft: rgba(6, 182, 212, 0.14);
  --cat-hedge: #a855f7;          /* purple */
  --cat-hedge-soft: rgba(168, 85, 247, 0.14);
  --cat-bulge: #eab308;          /* gold */
  --cat-bulge-soft: rgba(234, 179, 8, 0.14);
  --cat-asset: #ec4899;          /* pink */
  --cat-asset-soft: rgba(236, 72, 153, 0.14);
  --cat-other: #94a3b8;          /* slate */
  --cat-other-soft: rgba(148, 163, 184, 0.14);
  /* Texte "non vu" — légèrement plus brillant et bleuté */
  --text-unseen: #ffffff;
  --unseen-marker: #60a5fa;
}

/* === LIGHT MODE === */
:root[data-theme="light"] {
  --bg-0: #ffffff;
  --bg-1: #fafafa;
  --bg-2: #f4f4f5;
  --bg-3: #e7e7e9;
  --bg-hover: #ededed;
  --border-subtle: #ececec;
  --border: #e0e0e0;
  --border-strong: #cccccc;
  --text-1: #0a0a0a;
  --text-2: #525252;
  --text-3: #737373;
  --text-4: #a3a3a3;
  --red: #dc2626;
  --red-soft: rgba(220, 38, 38, 0.10);
  --orange: #d97706;
  --orange-soft: rgba(217, 119, 6, 0.10);
  --green: #16a34a;
  --green-soft: rgba(22, 163, 74, 0.10);
  --blue: #2563eb;
  --blue-soft: rgba(37, 99, 235, 0.10);
  --accent: #0a0a0a;
  --cat-quant: #0891b2;
  --cat-quant-soft: rgba(8, 145, 178, 0.10);
  --cat-hedge: #9333ea;
  --cat-hedge-soft: rgba(147, 51, 234, 0.10);
  --cat-bulge: #b45309;
  --cat-bulge-soft: rgba(180, 83, 9, 0.10);
  --cat-asset: #db2777;
  --cat-asset-soft: rgba(219, 39, 119, 0.10);
  --cat-other: #64748b;
  --cat-other-soft: rgba(100, 116, 139, 0.10);
  --text-unseen: #0a0a0a;
  --unseen-marker: #2563eb;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

html, body {
  background: var(--bg-0);
  color: var(--text-1);
  font-family: 'Geist', system-ui, -apple-system, sans-serif;
  font-feature-settings: "cv11", "ss01";
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  font-size: 15px;
  line-height: 1.5;
  min-height: 100vh;
}

button {
  font-family: inherit;
  font-size: inherit;
  cursor: pointer;
  border: none;
  background: none;
  color: inherit;
}

a { color: inherit; text-decoration: none; }

/* ============ TOP NAV ============ */
.topnav {
  position: sticky; top: 0; z-index: 10;
  display: flex; align-items: center;
  padding: 14px 32px;
  background: rgba(10, 10, 10, 0.85);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--border-subtle);
}

.topnav-logo {
  display: flex; align-items: center; justify-content: center;
  width: 32px; height: 32px;
  border-radius: 8px;
  background: linear-gradient(135deg, #3b82f6, #1e40af);
  color: white; font-weight: 700; font-size: 15px;
  letter-spacing: -0.02em;
}

.topnav-brand {
  margin-left: 12px;
  font-weight: 600;
  font-size: 16px;
  letter-spacing: -0.01em;
}

.topnav-tabs {
  display: flex; align-items: center; gap: 4px;
  margin-left: 32px;
}

.topnav-tab {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 14px;
  border-radius: 8px;
  color: var(--text-2);
  font-weight: 500;
  font-size: 14px;
  transition: color 0.15s, background 0.15s;
  position: relative;
}

.topnav-tab:hover { color: var(--text-1); background: var(--bg-2); }

.topnav-tab.active {
  color: var(--text-1);
}
.topnav-tab.active::after {
  content: '';
  position: absolute;
  bottom: -15px; left: 12px; right: 12px;
  height: 2px;
  background: var(--text-1);
  border-radius: 2px 2px 0 0;
}

.topnav-tab .tab-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  opacity: 0.8;
}

.topnav-tab .tab-count {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 20px; height: 20px;
  padding: 0 6px;
  border-radius: 10px;
  background: var(--bg-3);
  color: var(--text-2);
  font-size: 11px;
  font-weight: 600;
}

.topnav-tab.active .tab-count { background: #fbbf24; color: #422006; }

.topnav-right {
  margin-left: auto;
  display: flex; align-items: center; gap: 10px;
}

.topnav-icon-btn {
  width: 36px; height: 36px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 8px;
  border: 1px solid var(--border);
  color: var(--text-2);
  transition: background 0.15s, color 0.15s;
}
.topnav-icon-btn:hover { background: var(--bg-2); color: var(--text-1); }
.topnav-icon-btn svg { width: 16px; height: 16px; }

/* Le toggle theme : on affiche soleil OU lune selon le mode */
.theme-toggle .icon-sun { display: none; }
.theme-toggle .icon-moon { display: block; }
:root[data-theme="light"] .theme-toggle .icon-sun { display: block; }
:root[data-theme="light"] .theme-toggle .icon-moon { display: none; }

.topnav-avatar {
  width: 36px; height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #22c55e, #16a34a);
  display: flex; align-items: center; justify-content: center;
  color: #052e16;
  font-weight: 700;
  font-size: 12px;
  letter-spacing: 0.02em;
}

/* ============ MAIN ============ */
main {
  max-width: 1100px;
  margin: 0 auto;
  padding: 40px 32px 80px;
}

.view { display: none; }
.view.active { display: block; animation: fadein 0.25s ease-out; }

@keyframes fadein {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

.view-header {
  display: flex; align-items: flex-start; justify-content: space-between;
  gap: 24px;
  margin-bottom: 28px;
}

.view-title {
  font-size: 28px;
  font-weight: 600;
  letter-spacing: -0.02em;
  line-height: 1.2;
}

.view-subtitle {
  margin-top: 4px;
  font-size: 14px;
  color: var(--text-3);
}

/* ============ EXPLORER : chips de filtre ============ */
.filter-row {
  display: flex; align-items: center; gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 28px;
}

.chip {
  padding: 6px 14px;
  border-radius: 999px;
  background: var(--bg-2);
  color: var(--text-2);
  font-size: 13px;
  font-weight: 500;
  border: 1px solid transparent;
  transition: all 0.15s;
  white-space: nowrap;
}

.chip:hover { background: var(--bg-3); color: var(--text-1); }

.chip.active {
  background: var(--text-1);
  color: var(--bg-0);
  font-weight: 600;
}

.chip .chip-count {
  margin-left: 4px;
  opacity: 0.7;
  font-weight: 400;
}

/* ============ EXPLORER : timeline groups ============ */
.tgroup {
  margin-bottom: 32px;
}

.tgroup-header {
  display: flex; align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border-subtle);
}

.tgroup-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.tgroup-dot.red { background: var(--red); }
.tgroup-dot.orange { background: var(--orange); }
.tgroup-dot.green { background: var(--green); }
.tgroup-dot.gray { background: var(--text-4); }

.tgroup-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-1);
  letter-spacing: -0.01em;
}

.tgroup-count {
  margin-left: auto;
  font-size: 12px;
  color: var(--text-3);
  font-variant-numeric: tabular-nums;
}

/* ============ EXPLORER : ligne d'opportunité ============ */
.opp-row {
  display: grid;
  grid-template-columns: 10px 50px 36px 1fr auto auto;
  align-items: center;
  gap: 14px;
  padding: 14px 4px;
  border-bottom: 1px solid var(--border-subtle);
  cursor: pointer;
  transition: background 0.12s;
}

.opp-row:hover { background: var(--bg-1); }

.opp-row:last-child { border-bottom: none; }

/* Dot "non vu" + indicateur fort */
.opp-unseen {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--unseen-marker);
  box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.18);
  justify-self: center;
  transition: opacity 0.2s, background 0.2s;
}
.opp-row.seen .opp-unseen {
  background: transparent;
  box-shadow: none;
}

/* Vu = fade vers ~55% d'opacité sur tout sauf le bookmark */
.opp-row.seen .opp-date,
.opp-row.seen .firm-logo,
.opp-row.seen .opp-main,
.opp-row.seen .opp-dleft-wrap {
  opacity: 0.55;
}
.opp-row.seen:hover .opp-date,
.opp-row.seen:hover .firm-logo,
.opp-row.seen:hover .opp-main,
.opp-row.seen:hover .opp-dleft-wrap {
  opacity: 0.85;
}

/* Bordure latérale bleue sur les non-vues */
.opp-row.unseen {
  position: relative;
}
.opp-row.unseen::before {
  content: '';
  position: absolute;
  left: -8px; top: 6px; bottom: 6px;
  width: 3px;
  background: var(--unseen-marker);
  border-radius: 2px;
}

.opp-date {
  text-align: center;
  font-family: 'Geist Mono', monospace;
  line-height: 1;
}

.opp-date-month {
  font-size: 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-3);
  margin-bottom: 4px;
}

.opp-date-day {
  font-size: 18px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.opp-date.red .opp-date-day { color: var(--red); }
.opp-date.orange .opp-date-day { color: var(--orange); }
.opp-date.green .opp-date-day { color: var(--green); }
.opp-date.gray .opp-date-day { color: var(--text-3); }

/* Firm logo (Clearbit) ou fallback initiales coloré par catégorie */
.firm-logo {
  width: 32px; height: 32px;
  border-radius: 6px;
  background: var(--bg-2);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  overflow: hidden;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.02em;
  border: 1px solid var(--border-subtle);
}
.firm-logo img {
  width: 100%; height: 100%; object-fit: contain;
  background: #fff;  /* la plupart des logos Clearbit ont besoin d'un fond blanc */
}
.firm-logo.cat-quant         { background: var(--cat-quant-soft); color: var(--cat-quant); border-color: var(--cat-quant-soft); }
.firm-logo.cat-hedge_fund    { background: var(--cat-hedge-soft); color: var(--cat-hedge); border-color: var(--cat-hedge-soft); }
.firm-logo.cat-bulge_bracket { background: var(--cat-bulge-soft); color: var(--cat-bulge); border-color: var(--cat-bulge-soft); }
.firm-logo.cat-asset_manager { background: var(--cat-asset-soft); color: var(--cat-asset); border-color: var(--cat-asset-soft); }
.firm-logo.cat-other         { background: var(--cat-other-soft); color: var(--cat-other); border-color: var(--cat-other-soft); }

.opp-main { min-width: 0; }

.opp-firm {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-2);
  letter-spacing: -0.01em;
  margin-bottom: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: flex; align-items: center; gap: 8px;
}
.opp-row.unseen .opp-firm { color: var(--text-unseen); font-weight: 650; }

/* Pastille catégorie inline */
.cat-pill {
  display: inline-flex; align-items: center;
  padding: 2px 7px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  font-family: 'Geist Mono', monospace;
  flex-shrink: 0;
}
.cat-pill.cat-quant         { background: var(--cat-quant-soft); color: var(--cat-quant); }
.cat-pill.cat-hedge_fund    { background: var(--cat-hedge-soft); color: var(--cat-hedge); }
.cat-pill.cat-bulge_bracket { background: var(--cat-bulge-soft); color: var(--cat-bulge); }
.cat-pill.cat-asset_manager { background: var(--cat-asset-soft); color: var(--cat-asset); }
.cat-pill.cat-other         { background: var(--cat-other-soft); color: var(--cat-other); }

.opp-meta {
  font-size: 13px;
  color: var(--text-3);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.opp-row.unseen .opp-meta { color: var(--text-2); }

/* Ligne supplémentaire pour start_date / detected */
.opp-meta-extra {
  font-size: 12px;
  color: var(--text-4);
  margin-top: 3px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-family: 'Geist Mono', monospace;
}
.opp-meta-extra .sep { opacity: 0.5; margin: 0 6px; }
.opp-meta-extra .start { color: var(--text-3); }
.opp-meta-extra .detected { color: var(--text-4); }

.opp-dleft-wrap {
  text-align: right;
}
.opp-dleft {
  font-family: 'Geist Mono', monospace;
  font-size: 12px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.02em;
  display: inline-block;
  padding: 3px 8px;
  border-radius: 5px;
}
.opp-dleft.red    { color: var(--red);    background: var(--red-soft); }
.opp-dleft.orange { color: var(--orange); background: var(--orange-soft); }
.opp-dleft.green  { color: var(--green);  background: var(--green-soft); }
.opp-dleft.gray   { color: var(--text-3); background: var(--bg-3); }

.opp-dleft-friendly {
  display: block;
  font-size: 10px;
  color: var(--text-4);
  margin-top: 3px;
  font-family: 'Geist Mono', monospace;
}

.opp-bookmark {
  width: 32px; height: 32px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 6px;
  color: var(--text-3);
  transition: all 0.15s;
  border: 1px solid var(--border);
}
.opp-bookmark:hover { background: var(--bg-2); color: var(--text-1); border-color: var(--border-strong); }
.opp-bookmark.active {
  background: #fbbf2418;
  color: var(--orange);
  border-color: #f59e0b40;
}

/* ============ CANDIDATURES : pipeline ============ */
.cand-table {
  display: grid;
  border-top: 1px solid var(--border-subtle);
}

.cand-table-header,
.cand-row {
  display: grid;
  grid-template-columns: minmax(180px, 1fr) minmax(280px, 1.4fr) auto auto;
  align-items: center;
  gap: 24px;
  padding: 16px 4px;
  border-bottom: 1px solid var(--border-subtle);
}

.cand-table-header {
  padding: 10px 4px;
  font-size: 11px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-3);
  font-weight: 500;
}

.cand-row {
  cursor: pointer;
  transition: background 0.12s;
}
.cand-row:hover { background: var(--bg-1); }

.cand-row.offer { background: rgba(34, 197, 94, 0.06); }
.cand-row.rejected .cand-firm,
.cand-row.rejected .cand-program { text-decoration: line-through; color: var(--text-4); }

.cand-firm {
  font-size: 15px;
  font-weight: 600;
  letter-spacing: -0.01em;
}
.cand-program {
  font-size: 13px;
  color: var(--text-3);
  margin-top: 2px;
}

/* Pipeline bar */
.pipeline {
  display: flex;
  gap: 4px;
  height: 6px;
  width: 100%;
}
.pipeline-seg {
  flex: 1;
  height: 100%;
  border-radius: 2px;
  background: var(--bg-3);
  transition: background 0.2s;
}
.pipeline-seg.done { background: var(--green); }
.pipeline-seg.current { background: var(--orange); }
.pipeline-seg.current-oa { background: var(--blue); }
.pipeline-seg.failed { background: var(--red); }

.cand-stage {
  font-size: 13px;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.cand-stage.orange { color: var(--orange); }
.cand-stage.blue { color: var(--blue); }
.cand-stage.green { color: var(--green); }
.cand-stage.red { color: var(--red); }

.cand-action {
  font-size: 13px;
  font-family: 'Geist Mono', monospace;
  color: var(--text-2);
  white-space: nowrap;
}
.cand-action.red { color: var(--red); }
.cand-action.orange { color: var(--orange); }

.cand-empty,
.view-empty {
  padding: 80px 20px;
  text-align: center;
  color: var(--text-3);
}
.view-empty-title { font-size: 16px; color: var(--text-2); margin-bottom: 6px; }
.view-empty-sub { font-size: 13px; }

.cand-hint {
  text-align: center;
  margin-top: 20px;
  font-size: 12px;
  color: var(--text-4);
}

/* ============ FAVORIS : cards ============ */
.fav-alert {
  display: flex; align-items: center; gap: 12px;
  padding: 14px 18px;
  margin-bottom: 24px;
  background: rgba(245, 158, 11, 0.08);
  border: 1px solid rgba(245, 158, 11, 0.25);
  border-radius: var(--radius);
  color: var(--orange);
  font-size: 14px;
  font-weight: 500;
}

.fav-card {
  position: relative;
  display: block;
  padding: 18px 20px 18px 24px;
  margin-bottom: 12px;
  background: var(--bg-1);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius);
  cursor: pointer;
  transition: all 0.15s;
  overflow: hidden;
}
.fav-card:hover { background: var(--bg-2); border-color: var(--border); }
.fav-card.unseen { background: rgba(59, 130, 246, 0.06); border-color: rgba(96, 165, 250, 0.22); }
.fav-card.unseen:hover { background: rgba(59, 130, 246, 0.10); }
/* Vu : opacité réduite, l'effet "déjà lu" */
.fav-card:not(.unseen) .fav-card-firm,
.fav-card:not(.unseen) .fav-card-program,
.fav-card:not(.unseen) .fav-card-dates,
.fav-card:not(.unseen) .firm-logo {
  opacity: 0.6;
}
.fav-card:not(.unseen):hover .fav-card-firm,
.fav-card:not(.unseen):hover .fav-card-program,
.fav-card:not(.unseen):hover .fav-card-dates,
.fav-card:not(.unseen):hover .firm-logo {
  opacity: 0.95;
}

.fav-card::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 3px;
  background: var(--text-4);
}
.fav-card.urgency-red::before { background: var(--red); }
.fav-card.urgency-orange::before { background: var(--orange); }
.fav-card.urgency-green::before { background: var(--green); }

.fav-card-top {
  display: flex; align-items: flex-start; gap: 12px;
}

.fav-card-header {
  display: flex; align-items: flex-start; justify-content: space-between;
  gap: 16px;
  flex: 1; min-width: 0;
}

.fav-card-firm {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-2);
  letter-spacing: -0.01em;
  margin-bottom: 4px;
  display: flex; align-items: center; gap: 8px;
}
.fav-card.unseen .fav-card-firm { color: var(--text-unseen); font-weight: 650; }

.fav-card-program {
  font-size: 13px;
  color: var(--text-3);
}
.fav-card.unseen .fav-card-program { color: var(--text-2); }

.fav-card-dates {
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-4);
  font-family: 'Geist Mono', monospace;
}
.fav-card-dates .sep { opacity: 0.5; margin: 0 6px; }
.fav-card-dates .start { color: var(--text-3); }

.fav-card-badge {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 3px 9px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  font-family: 'Geist Mono', monospace;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.02em;
  white-space: nowrap;
  flex-shrink: 0;
}
.fav-card-badge.red { background: var(--red-soft); color: var(--red); }
.fav-card-badge.orange { background: var(--orange-soft); color: var(--orange); }
.fav-card-badge.green { background: var(--green-soft); color: var(--green); }
.fav-card-badge.gray { background: var(--bg-3); color: var(--text-3); }

.fav-card-actions {
  margin-top: 14px;
  display: flex; align-items: center; gap: 8px;
}

.btn-primary {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 7px 14px;
  border-radius: 6px;
  background: var(--blue-soft);
  border: 1px solid rgba(59, 130, 246, 0.25);
  color: var(--blue);
  font-size: 13px;
  font-weight: 500;
  transition: all 0.15s;
}
.btn-primary:hover { background: rgba(59, 130, 246, 0.18); }

.btn-secondary {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 7px 12px;
  border-radius: 6px;
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-2);
  font-size: 13px;
  font-weight: 500;
  transition: all 0.15s;
}
.btn-secondary:hover { background: var(--bg-2); color: var(--text-1); }

.fav-more {
  text-align: center;
  margin-top: 16px;
  font-size: 13px;
  color: var(--text-3);
}

/* ============ DETAIL MODAL ============ */
.modal-backdrop {
  display: none;
  position: fixed; inset: 0;
  background: rgba(0, 0, 0, 0.7);
  z-index: 100;
  align-items: flex-start;
  justify-content: center;
  padding: 60px 20px;
  overflow-y: auto;
  animation: fadein 0.2s;
}
.modal-backdrop.open { display: flex; }

.modal {
  width: 100%;
  max-width: 720px;
  background: var(--bg-1);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 32px;
  position: relative;
  margin-bottom: 60px;
}

.modal-close {
  position: absolute;
  top: 16px; right: 16px;
  width: 32px; height: 32px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 6px;
  color: var(--text-3);
  transition: all 0.15s;
}
.modal-close:hover { background: var(--bg-3); color: var(--text-1); }

.modal-firm {
  font-size: 24px;
  font-weight: 600;
  letter-spacing: -0.02em;
  margin-bottom: 4px;
}

.modal-program {
  font-size: 15px;
  color: var(--text-2);
  margin-bottom: 20px;
}

.modal-logo-row {
  display: flex; align-items: flex-start; gap: 14px;
  margin-bottom: 20px;
}
.modal-logo-row .firm-logo {
  width: 48px; height: 48px;
  font-size: 15px;
}
.modal-firm-block { flex: 1; min-width: 0; }
.modal-firm-block .modal-firm { margin-bottom: 4px; }
.modal-firm-block .modal-program { margin-bottom: 0; }

.modal-meta-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px 24px;
  padding: 16px;
  background: var(--bg-2);
  border-radius: var(--radius);
  margin-bottom: 20px;
}

.modal-meta-item {
  font-size: 13px;
}
.modal-meta-item.accent .modal-meta-value {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  font-family: 'Geist Mono', monospace;
}
.modal-meta-item.accent.cat-quant         .modal-meta-value { background: var(--cat-quant-soft); color: var(--cat-quant); }
.modal-meta-item.accent.cat-hedge_fund    .modal-meta-value { background: var(--cat-hedge-soft); color: var(--cat-hedge); }
.modal-meta-item.accent.cat-bulge_bracket .modal-meta-value { background: var(--cat-bulge-soft); color: var(--cat-bulge); }
.modal-meta-item.accent.cat-asset_manager .modal-meta-value { background: var(--cat-asset-soft); color: var(--cat-asset); }
.modal-meta-item.accent.cat-other         .modal-meta-value { background: var(--cat-other-soft); color: var(--cat-other); }
.modal-meta-label {
  color: var(--text-3);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 4px;
}
.modal-meta-value { color: var(--text-1); }

.modal-section {
  margin-top: 18px;
}
.modal-section-title {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-3);
  margin-bottom: 8px;
}
.modal-section-body {
  font-size: 14px;
  color: var(--text-1);
  line-height: 1.6;
  white-space: pre-wrap;
}

.modal-preapp {
  padding: 18px;
  background: var(--bg-2);
  border-radius: var(--radius);
  font-size: 13.5px;
  line-height: 1.65;
  color: var(--text-1);
  white-space: pre-wrap;
  font-feature-settings: "ss01";
}

.modal-copy {
  margin-top: 10px;
  font-size: 12px;
  color: var(--text-3);
  display: inline-flex; align-items: center; gap: 6px;
  cursor: pointer;
  padding: 6px 10px;
  border-radius: 6px;
  transition: all 0.15s;
}
.modal-copy:hover { color: var(--text-1); background: var(--bg-2); }

.modal-actions {
  display: flex; gap: 10px;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--border-subtle);
}

/* Pipeline picker dans modal */
.stage-picker {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
  margin-top: 12px;
}
.stage-btn {
  padding: 8px 10px;
  border-radius: 6px;
  background: var(--bg-2);
  color: var(--text-2);
  font-size: 12px;
  font-weight: 500;
  border: 1px solid var(--border-subtle);
  transition: all 0.15s;
  text-align: left;
}
.stage-btn:hover { background: var(--bg-3); color: var(--text-1); }
.stage-btn.active {
  background: rgba(59, 130, 246, 0.15);
  color: var(--blue);
  border-color: rgba(59, 130, 246, 0.4);
}
.stage-btn.offer.active { background: var(--green-soft); color: var(--green); border-color: rgba(34, 197, 94, 0.4); }
.stage-btn.rejected.active { background: var(--red-soft); color: var(--red); border-color: rgba(239, 68, 68, 0.4); }

/* ============ FOOTER ============ */
.app-footer {
  max-width: 1100px;
  margin: 60px auto 0;
  padding: 24px 32px;
  border-top: 1px solid var(--border-subtle);
  font-size: 12px;
  color: var(--text-4);
  text-align: center;
}

/* ============ RESPONSIVE ============ */
@media (max-width: 720px) {
  .topnav { padding: 12px 16px; }
  .topnav-brand { display: none; }
  .topnav-tabs { margin-left: 12px; gap: 0; }
  .topnav-tab { padding: 8px 10px; font-size: 13px; }
  .topnav-tab .tab-icon { display: none; }
  main { padding: 24px 16px 60px; }
  .view-title { font-size: 22px; }
  .opp-row { grid-template-columns: 8px 44px 30px 1fr auto; gap: 10px; padding: 12px 0; }
  .opp-bookmark { display: none; }
  .firm-logo { width: 28px; height: 28px; }
  .opp-meta-extra { font-size: 11px; }
  .cat-table-header,
  .cand-row { grid-template-columns: 1fr; gap: 8px; padding: 14px 4px; }
  .cand-table-header { display: none; }
  .pipeline { width: 100%; max-width: none; }
  .modal { padding: 24px 20px; }
  .modal-firm { font-size: 20px; }
  .modal-meta-grid { grid-template-columns: 1fr; gap: 10px; }
  .stage-picker { grid-template-columns: repeat(2, 1fr); }
}
</style>
</head>
<body>

<header class="topnav">
  <div class="topnav-logo">M</div>
  <div class="topnav-brand">Quant Tracker</div>
  <nav class="topnav-tabs">
    <button class="topnav-tab active" data-tab="explorer">
      <span class="tab-icon">⌖</span>
      Explorer
    </button>
    <button class="topnav-tab" data-tab="candidatures">
      <span class="tab-icon">▤</span>
      Candidatures
      <span class="tab-count" id="count-cand">0</span>
    </button>
    <button class="topnav-tab" data-tab="favoris">
      <span class="tab-icon">★</span>
      Favoris
      <span class="tab-count" id="count-fav">0</span>
    </button>
  </nav>
  <div class="topnav-right">
    <button class="topnav-icon-btn theme-toggle" id="theme-toggle" title="Changer de thème" aria-label="Changer de thème">
      <svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
      <svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>
    </button>
    <div class="topnav-avatar">MG</div>
  </div>
</header>

<main>
  <!-- ========== EXPLORER ========== -->
  <section class="view active" id="view-explorer">
    <div class="view-header">
      <div>
        <h1 class="view-title">Explorer</h1>
        <div class="view-subtitle" id="explorer-subtitle">— offres détectées</div>
      </div>
    </div>
    <div class="filter-row" id="filter-row"></div>
    <div id="explorer-list"></div>
  </section>

  <!-- ========== CANDIDATURES ========== -->
  <section class="view" id="view-candidatures">
    <div class="view-header">
      <div>
        <h1 class="view-title">Mes candidatures</h1>
        <div class="view-subtitle" id="cand-subtitle">— en cours</div>
      </div>
    </div>
    <div id="cand-list"></div>
    <div class="cand-hint">Cliquer sur une ligne pour modifier l'étape</div>
  </section>

  <!-- ========== FAVORIS ========== -->
  <section class="view" id="view-favoris">
    <div class="view-header">
      <div>
        <h1 class="view-title">Favoris</h1>
        <div class="view-subtitle" id="fav-subtitle">— offres sauvegardées</div>
      </div>
    </div>
    <div id="fav-alert-box"></div>
    <div id="fav-list"></div>
  </section>
</main>

<div class="app-footer">
  Mis à jour <span id="footer-updated">—</span> · Le state local (favoris, candidatures) est stocké uniquement sur cet appareil.
</div>

<!-- DETAIL MODAL -->
<div class="modal-backdrop" id="modal-backdrop">
  <div class="modal">
    <button class="modal-close" id="modal-close">✕</button>
    <div id="modal-body"></div>
  </div>
</div>

<script>
// ============================================================
// DATA — injecté côté serveur
// ============================================================
const OPPS = __OPPS_JSON__;
const GENERATED_AT = "__GENERATED_AT__";

// ============================================================
// CONSTANTS
// ============================================================
const CATEGORIES = {
  all: "Toutes",
  quant: "Quant",
  hedge_fund: "Hedge Fund",
  bulge_bracket: "Bulge Bracket",
  asset_manager: "Asset Manager",
  other: "Autres",
};

const STAGES = [
  { id: "applied",    label: "Postulé",       color: "blue"   },
  { id: "oa",         label: "OA / Test",     color: "blue"   },
  { id: "hirevue",    label: "HireVue",       color: "orange" },
  { id: "round1",     label: "Round 1",       color: "orange" },
  { id: "round2",     label: "Round 2",       color: "orange" },
  { id: "final",      label: "Final",         color: "orange" },
  { id: "offer",      label: "Offre",         color: "green", terminal: true  },
  { id: "rejected",   label: "Refus",         color: "red",   terminal: true  },
];

// ============================================================
// LOCAL STORAGE
// ============================================================
const LS_FAV = "qt_favorites_v1";
const LS_CAND = "qt_candidatures_v1";
const LS_SEEN = "qt_seen_v1";

function getFavorites() {
  try { return JSON.parse(localStorage.getItem(LS_FAV) || "[]"); }
  catch { return []; }
}
function setFavorites(arr) {
  localStorage.setItem(LS_FAV, JSON.stringify(arr));
}
function isFavorite(id) {
  return getFavorites().includes(id);
}
function toggleFavorite(id) {
  const favs = getFavorites();
  const idx = favs.indexOf(id);
  if (idx === -1) favs.push(id);
  else favs.splice(idx, 1);
  setFavorites(favs);
}

function getCandidatures() {
  try { return JSON.parse(localStorage.getItem(LS_CAND) || "{}"); }
  catch { return {}; }
}
function setCandidatures(obj) {
  localStorage.setItem(LS_CAND, JSON.stringify(obj));
}
function getCandidatureStage(id) {
  return getCandidatures()[id] || null;
}
function setCandidatureStage(id, stage) {
  const c = getCandidatures();
  if (stage === null) {
    delete c[id];
  } else {
    c[id] = stage;
  }
  setCandidatures(c);
}

function getSeen() {
  try { return new Set(JSON.parse(localStorage.getItem(LS_SEEN) || "[]")); }
  catch { return new Set(); }
}
function isSeen(id) {
  return getSeen().has(id);
}
function markSeen(id) {
  const s = getSeen();
  if (s.has(id)) return false;
  s.add(id);
  localStorage.setItem(LS_SEEN, JSON.stringify([...s]));
  return true;
}

const LS_THEME = "qt_theme_v1";
function getTheme() {
  return localStorage.getItem(LS_THEME) || "dark";
}
function setTheme(theme) {
  if (theme === "light") {
    document.documentElement.setAttribute("data-theme", "light");
  } else {
    document.documentElement.removeAttribute("data-theme");
  }
  localStorage.setItem(LS_THEME, theme);
}
function toggleTheme() {
  setTheme(getTheme() === "light" ? "dark" : "light");
}

// ============================================================
// DATE HELPERS
// ============================================================
const MONTHS = ["JAN", "FÉV", "MAR", "AVR", "MAI", "JUN", "JUL", "AOÛ", "SEP", "OCT", "NOV", "DÉC"];

function parseISO(s) {
  if (!s) return null;
  const d = new Date(s);
  return isNaN(d) ? null : d;
}

function daysUntil(iso) {
  const d = parseISO(iso);
  if (!d) return null;
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  const target = new Date(d);
  target.setHours(0, 0, 0, 0);
  return Math.round((target - now) / 86400000);
}

function urgencyClass(iso) {
  const days = daysUntil(iso);
  if (days === null) return "gray";
  if (days < 0) return "gray";
  if (days <= 7) return "red";
  if (days <= 21) return "orange";
  return "green";
}

function formatDateBadge(iso) {
  const d = parseISO(iso);
  if (!d) return null;
  return {
    month: MONTHS[d.getMonth()],
    day: String(d.getDate()).padStart(2, "0"),
  };
}

function formatDLeft(iso) {
  const days = daysUntil(iso);
  if (days === null) return "—";
  if (days < 0) return "passé";
  if (days === 0) return "ajd";
  return "J-" + days;
}

function formatFriendlyDate(iso) {
  const d = parseISO(iso);
  if (!d) return "—";
  return d.toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" });
}

function formatShortMonth(iso) {
  // Pour start_date qui est souvent imprécis : "juin 2027" plutôt que "1 juin 2027"
  const d = parseISO(iso);
  if (!d) return "—";
  return d.toLocaleDateString("fr-FR", { month: "long", year: "numeric" });
}

/* Relative time : "dans 10 jours", "dans 2 semaines", "dans ~6 mois", "il y a 3 jours" */
function relativeTime(iso, opts) {
  opts = opts || {};
  const d = parseISO(iso);
  if (!d) return "";
  const now = new Date(); now.setHours(0, 0, 0, 0);
  const t = new Date(d); t.setHours(0, 0, 0, 0);
  const diffDays = Math.round((t - now) / 86400000);
  const abs = Math.abs(diffDays);
  const past = diffDays < 0;
  let txt;
  if (abs === 0) txt = "aujourd'hui";
  else if (abs === 1) txt = past ? "hier" : "demain";
  else if (abs < 14) txt = past ? `il y a ${abs} jours` : `dans ${abs} jours`;
  else if (abs < 60) {
    const w = Math.round(abs / 7);
    txt = past ? `il y a ${w} semaines` : `dans ${w} semaines`;
  } else if (abs < 365) {
    const m = Math.round(abs / 30);
    txt = past ? `il y a ~${m} mois` : `dans ~${m} mois`;
  } else {
    const y = (abs / 365).toFixed(1).replace(".0", "");
    txt = past ? `il y a ~${y} an${y > 1 ? "s" : ""}` : `dans ~${y} an${y > 1 ? "s" : ""}`;
  }
  return txt;
}

/* Logo HTML : tag <img> Clearbit avec fallback initiales colorées par catégorie */
function logoHTML(opp) {
  const cls = "firm-logo cat-" + (opp.firm_category || "other");
  if (opp.firm_domain) {
    // Image avec fallback onerror vers initiales
    const initials = getInitials(opp.firm);
    return `<div class="${cls}">
      <img src="https://logo.clearbit.com/${opp.firm_domain}" alt=""
           onerror="this.style.display='none';this.parentElement.textContent='${esc(initials)}'">
    </div>`;
  }
  return `<div class="${cls}">${esc(getInitials(opp.firm))}</div>`;
}

function getInitials(firm) {
  if (!firm) return "?";
  // "Jane Street" → "JS", "Goldman Sachs (Students)" → "GS"
  const cleaned = firm.replace(/\([^)]*\)/g, "").trim();
  const parts = cleaned.split(/\s+/).filter(Boolean);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

// ============================================================
// FILTERING & SORTING
// ============================================================
let CURRENT_CATEGORY = "all";

function filteredOpps() {
  if (CURRENT_CATEGORY === "all") return OPPS;
  return OPPS.filter(o => o.firm_category === CURRENT_CATEGORY);
}

function sortByDeadline(arr) {
  return [...arr].sort((a, b) => {
    const da = daysUntil(a.deadline_iso);
    const db = daysUntil(b.deadline_iso);
    if (da === null && db === null) return (b.priority_score || 0) - (a.priority_score || 0);
    if (da === null) return 1;
    if (db === null) return -1;
    return da - db;
  });
}

// ============================================================
// RENDER : EXPLORER
// ============================================================
function renderExplorerSubtitle() {
  const total = OPPS.length;
  const open = OPPS.filter(o => {
    const d = daysUntil(o.deadline_iso);
    return d === null || d >= 0;
  }).length;
  document.getElementById("explorer-subtitle").textContent =
    total + " offre" + (total === 1 ? "" : "s") + " · " + open + " ouverte" + (open === 1 ? "" : "s") + " maintenant";
}

function renderFilters() {
  const row = document.getElementById("filter-row");
  const counts = { all: OPPS.length };
  for (const o of OPPS) {
    const c = o.firm_category || "other";
    counts[c] = (counts[c] || 0) + 1;
  }
  row.innerHTML = "";
  Object.entries(CATEGORIES).forEach(([key, label]) => {
    if (key !== "all" && !counts[key]) return; // hide empty categories
    const btn = document.createElement("button");
    btn.className = "chip" + (CURRENT_CATEGORY === key ? " active" : "");
    btn.innerHTML = label + ' <span class="chip-count">· ' + (counts[key] || 0) + '</span>';
    btn.onclick = () => { CURRENT_CATEGORY = key; renderExplorer(); };
    row.appendChild(btn);
  });
}

function renderExplorer() {
  renderExplorerSubtitle();
  renderFilters();

  const list = document.getElementById("explorer-list");
  list.innerHTML = "";

  const opps = sortByDeadline(filteredOpps());

  // Groupement temporel
  const buckets = {
    "Cette semaine":          { dot: "red",    items: [] },
    "Deux prochaines semaines":{ dot: "orange", items: [] },
    "Le mois prochain":       { dot: "green",  items: [] },
    "Plus tard":              { dot: "gray",   items: [] },
    "Sans deadline":          { dot: "gray",   items: [] },
    "Passées":                { dot: "gray",   items: [] },
  };

  for (const o of opps) {
    const days = daysUntil(o.deadline_iso);
    if (days === null) buckets["Sans deadline"].items.push(o);
    else if (days < 0) buckets["Passées"].items.push(o);
    else if (days <= 7) buckets["Cette semaine"].items.push(o);
    else if (days <= 21) buckets["Deux prochaines semaines"].items.push(o);
    else if (days <= 60) buckets["Le mois prochain"].items.push(o);
    else buckets["Plus tard"].items.push(o);
  }

  if (opps.length === 0) {
    list.innerHTML = '<div class="view-empty"><div class="view-empty-title">Aucune offre pour ce filtre</div><div class="view-empty-sub">Essaie une autre catégorie ou attends le prochain run du bot.</div></div>';
    return;
  }

  Object.entries(buckets).forEach(([name, { dot, items }]) => {
    if (items.length === 0) return;
    const group = document.createElement("div");
    group.className = "tgroup";
    group.innerHTML = `
      <div class="tgroup-header">
        <div class="tgroup-dot ${dot}"></div>
        <div class="tgroup-title">${name}</div>
        <div class="tgroup-count">${items.length}</div>
      </div>
      <div class="tgroup-items"></div>
    `;
    const itemsEl = group.querySelector(".tgroup-items");
    items.forEach(o => itemsEl.appendChild(buildOppRow(o)));
    list.appendChild(group);
  });
}

function buildOppRow(o) {
  const row = document.createElement("div");
  const seen = isSeen(o.id);
  row.className = "opp-row " + (seen ? "seen" : "unseen");

  const badge = formatDateBadge(o.deadline_iso);
  const urgency = urgencyClass(o.deadline_iso);
  const dleftText = formatDLeft(o.deadline_iso);

  const fav = isFavorite(o.id);

  const dateHtml = badge
    ? `<div class="opp-date ${urgency}">
         <div class="opp-date-month">${badge.month}</div>
         <div class="opp-date-day">${badge.day}</div>
       </div>`
    : `<div class="opp-date gray">
         <div class="opp-date-month">—</div>
         <div class="opp-date-day">—</div>
       </div>`;

  const meta = [o.program_name, o.location].filter(Boolean).join(" · ") || "—";

  // 3e ligne meta-extra : début + détecté
  const extras = [];
  if (o.start_date_iso || o.start_date) {
    const startTxt = o.start_date || formatShortMonth(o.start_date_iso);
    const rel = o.start_date_iso ? " (" + relativeTime(o.start_date_iso) + ")" : "";
    extras.push(`<span class="start">→ Début : ${esc(startTxt)}${esc(rel)}</span>`);
  }
  if (o.first_seen) {
    extras.push(`<span class="detected">détecté ${esc(relativeTime(o.first_seen))}</span>`);
  }
  const extraHtml = extras.length
    ? `<div class="opp-meta-extra">${extras.join('<span class="sep">·</span>')}</div>`
    : "";

  // J-N avec date friendly en dessous
  let friendlyDeadline = "";
  if (o.deadline_iso) {
    friendlyDeadline = `<div class="opp-dleft-friendly">${esc(relativeTime(o.deadline_iso))}</div>`;
  }

  row.innerHTML = `
    <div class="opp-unseen"></div>
    ${dateHtml}
    ${logoHTML(o)}
    <div class="opp-main">
      <div class="opp-firm">${esc(o.firm)}<span class="cat-pill cat-${esc(o.firm_category)}">${esc(o.firm_category_label || "")}</span></div>
      <div class="opp-meta">${esc(meta)}</div>
      ${extraHtml}
    </div>
    <div class="opp-dleft-wrap">
      <span class="opp-dleft ${urgency}">${dleftText}</span>
      ${friendlyDeadline}
    </div>
    <button class="opp-bookmark ${fav ? "active" : ""}" data-id="${o.id}" title="${fav ? "Retirer des favoris" : "Ajouter aux favoris"}">
      ${fav ? "★" : "☆"}
    </button>
  `;

  row.querySelector(".opp-bookmark").addEventListener("click", (e) => {
    e.stopPropagation();
    toggleFavorite(o.id);
    renderAll();
  });

  row.addEventListener("click", () => openDetail(o.id));
  return row;
}

// ============================================================
// RENDER : CANDIDATURES
// ============================================================
function renderCandidatures() {
  const cand = getCandidatures();
  const ids = Object.keys(cand);
  const oppMap = Object.fromEntries(OPPS.map(o => [o.id, o]));

  const sub = document.getElementById("cand-subtitle");
  const actives = ids.filter(id => {
    const stage = cand[id];
    return stage && stage !== "offer" && stage !== "rejected";
  });
  const offers = ids.filter(id => cand[id] === "offer");
  let subtext = ids.length + " candidature" + (ids.length === 1 ? "" : "s");
  if (actives.length) subtext += " · " + actives.length + " active" + (actives.length === 1 ? "" : "s");
  if (offers.length) subtext += " · " + offers.length + " offre" + (offers.length === 1 ? "" : "s") + " reçue" + (offers.length === 1 ? "" : "s");
  sub.textContent = subtext;

  document.getElementById("count-cand").textContent = actives.length || ids.length;

  const list = document.getElementById("cand-list");
  list.innerHTML = "";

  if (ids.length === 0) {
    list.innerHTML = '<div class="view-empty"><div class="view-empty-title">Aucune candidature en cours</div><div class="view-empty-sub">Marque une offre comme postulée depuis les Favoris pour la voir ici.</div></div>';
    return;
  }

  const table = document.createElement("div");
  table.className = "cand-table";
  table.innerHTML = `
    <div class="cand-table-header">
      <div>ENTREPRISE</div>
      <div>ÉTAPE ACTUELLE</div>
      <div>STATUT</div>
      <div>DEADLINE</div>
    </div>
  `;

  // Tri : actives d'abord (par urgence deadline), puis terminées
  const sorted = ids.sort((a, b) => {
    const sa = cand[a], sb = cand[b];
    const ta = (sa === "offer" || sa === "rejected") ? 1 : 0;
    const tb = (sb === "offer" || sb === "rejected") ? 1 : 0;
    if (ta !== tb) return ta - tb;
    const oa = oppMap[a], ob = oppMap[b];
    const da = oa ? (daysUntil(oa.deadline_iso) ?? 999) : 999;
    const db = ob ? (daysUntil(ob.deadline_iso) ?? 999) : 999;
    return da - db;
  });

  sorted.forEach(id => {
    const o = oppMap[id];
    const stage = cand[id];
    const stageInfo = STAGES.find(s => s.id === stage);
    if (!o || !stageInfo) return;

    const row = document.createElement("div");
    row.className = "cand-row " + (stage === "offer" ? "offer" : stage === "rejected" ? "rejected" : "");

    // Pipeline visualization (excluding the two terminal states from the bar)
    const stageOrder = ["applied", "oa", "hirevue", "round1", "round2", "final"];
    const stageIdx = stageOrder.indexOf(stage);
    const isTerminal = stage === "offer" || stage === "rejected";

    let pipeline = "";
    if (isTerminal) {
      const cls = stage === "offer" ? "done" : "failed";
      pipeline = stageOrder.map(() => `<div class="pipeline-seg ${cls}"></div>`).join("");
    } else {
      pipeline = stageOrder.map((s, i) => {
        if (i < stageIdx) return '<div class="pipeline-seg done"></div>';
        if (i === stageIdx) {
          const segCls = (s === "oa") ? "current-oa" : "current";
          return `<div class="pipeline-seg ${segCls}"></div>`;
        }
        return '<div class="pipeline-seg"></div>';
      }).join("");
    }

    const daysL = daysUntil(o.deadline_iso);
    let action = "—";
    let actionCls = "";
    if (daysL !== null && daysL >= 0 && !isTerminal) {
      action = "J-" + daysL;
      if (daysL <= 7) actionCls = "red";
      else if (daysL <= 21) actionCls = "orange";
    } else if (stage === "offer") {
      action = "→ rép.";
    }

    row.innerHTML = `
      <div>
        <div class="cand-firm">${esc(o.firm)}</div>
        <div class="cand-program">${esc(o.program_name || "")}</div>
      </div>
      <div class="pipeline">${pipeline}</div>
      <div class="cand-stage ${stageInfo.color}">${esc(stageInfo.label)}</div>
      <div class="cand-action ${actionCls}">${esc(action)}</div>
    `;
    row.addEventListener("click", () => openDetail(o.id));
    table.appendChild(row);
  });

  list.appendChild(table);
}

// ============================================================
// RENDER : FAVORIS
// ============================================================
function renderFavoris() {
  const favs = getFavorites();
  const cand = getCandidatures();
  const oppMap = Object.fromEntries(OPPS.map(o => [o.id, o]));
  const items = favs.map(id => oppMap[id]).filter(Boolean);

  // Cacher les favoris déjà devenus candidatures actives
  const visible = items.filter(o => !cand[o.id]);

  document.getElementById("count-fav").textContent = visible.length;
  document.getElementById("fav-subtitle").textContent =
    visible.length + " offre" + (visible.length === 1 ? "" : "s") + " sauvegardée" + (visible.length === 1 ? "" : "s") + " à postuler";

  // Alert box pour les favoris qui ferment bientôt
  const alertBox = document.getElementById("fav-alert-box");
  const closingSoon = visible.filter(o => {
    const d = daysUntil(o.deadline_iso);
    return d !== null && d >= 0 && d <= 7;
  });
  alertBox.innerHTML = "";
  if (closingSoon.length > 0) {
    const alert = document.createElement("div");
    alert.className = "fav-alert";
    alert.innerHTML = `<span>⏰</span><span>${closingSoon.length} favori${closingSoon.length === 1 ? "" : "s"} ferme${closingSoon.length === 1 ? "" : "nt"} dans les 7 jours</span>`;
    alertBox.appendChild(alert);
  }

  const list = document.getElementById("fav-list");
  list.innerHTML = "";

  if (visible.length === 0) {
    list.innerHTML = '<div class="view-empty"><div class="view-empty-title">Aucun favori</div><div class="view-empty-sub">Marque une offre depuis Explorer en cliquant sur ★.</div></div>';
    return;
  }

  // Tri par urgence
  const sorted = sortByDeadline(visible);

  sorted.forEach(o => {
    const card = document.createElement("div");
    const urg = urgencyClass(o.deadline_iso);
    const seen = isSeen(o.id);
    card.className = "fav-card urgency-" + urg + (seen ? "" : " unseen");

    const days = daysUntil(o.deadline_iso);
    let badgeText, badgeCls;
    if (days === null) { badgeText = "—"; badgeCls = "gray"; }
    else if (days < 0) { badgeText = "passé"; badgeCls = "gray"; }
    else if (days === 0) { badgeText = "ajd"; badgeCls = "red"; }
    else { badgeText = "J-" + days; badgeCls = urg; }

    const meta = [o.program_name, o.location].filter(Boolean).join(" · ") || "—";

    // Dates explicites
    const dateParts = [];
    if (o.deadline_iso) {
      dateParts.push(`Postuler d'ici le ${esc(formatFriendlyDate(o.deadline_iso))} (${esc(relativeTime(o.deadline_iso))})`);
    } else if (o.deadline) {
      dateParts.push(`Postuler : ${esc(o.deadline)}`);
    }
    if (o.start_date_iso || o.start_date) {
      const startTxt = o.start_date || formatShortMonth(o.start_date_iso);
      const rel = o.start_date_iso ? " (" + relativeTime(o.start_date_iso) + ")" : "";
      dateParts.push(`<span class="start">→ Début : ${esc(startTxt)}${esc(rel)}</span>`);
    }
    const datesHtml = dateParts.length
      ? `<div class="fav-card-dates">${dateParts.join('<span class="sep">·</span>')}</div>`
      : "";

    card.innerHTML = `
      <div class="fav-card-top">
        ${logoHTML(o)}
        <div class="fav-card-header">
          <div>
            <div class="fav-card-firm">${esc(o.firm)}<span class="cat-pill cat-${esc(o.firm_category)}">${esc(o.firm_category_label || "")}</span></div>
            <div class="fav-card-program">${esc(meta)}</div>
            ${datesHtml}
          </div>
          <div class="fav-card-badge ${badgeCls}">${esc(badgeText)}</div>
        </div>
      </div>
      <div class="fav-card-actions">
        <button class="btn-primary" data-action="apply">✓ Marquer comme postulé</button>
        ${o.apply_url ? `<a class="btn-secondary" href="${esc(o.apply_url)}" target="_blank" rel="noopener" onclick="event.stopPropagation()">↗ Lien</a>` : ""}
        <button class="btn-secondary" data-action="unfav" title="Retirer des favoris">✕</button>
      </div>
    `;

    card.querySelector('[data-action="apply"]').addEventListener("click", (e) => {
      e.stopPropagation();
      setCandidatureStage(o.id, "applied");
      renderAll();
      switchTab("candidatures");
    });
    card.querySelector('[data-action="unfav"]').addEventListener("click", (e) => {
      e.stopPropagation();
      toggleFavorite(o.id);
      renderAll();
    });

    card.addEventListener("click", () => openDetail(o.id));
    list.appendChild(card);
  });
}

// ============================================================
// MODAL DETAIL
// ============================================================
function openDetail(id) {
  const o = OPPS.find(x => x.id === id);
  if (!o) return;

  // Marquer comme vu (avec re-render différé pour ne pas casser le DOM en cours)
  const wasUnseen = markSeen(id);

  const body = document.getElementById("modal-body");
  const stage = getCandidatureStage(id);
  const fav = isFavorite(id);

  // Dates explicites avec relative time
  let deadlineDisp = "—";
  if (o.deadline_iso) {
    deadlineDisp = formatFriendlyDate(o.deadline_iso) + " · " + relativeTime(o.deadline_iso);
  } else if (o.deadline) {
    deadlineDisp = o.deadline;
  }
  let startDisp = "—";
  if (o.start_date_iso) {
    startDisp = formatShortMonth(o.start_date_iso) + " · " + relativeTime(o.start_date_iso);
  } else if (o.start_date) {
    startDisp = o.start_date;
  }
  const detectedDisp = o.first_seen
    ? formatFriendlyDate(o.first_seen) + " · " + relativeTime(o.first_seen)
    : "—";

  const meta = [
    { label: "Catégorie",     value: o.firm_category_label, accent: true },
    { label: "Localisation",  value: o.location },
    { label: "Deadline",      value: deadlineDisp },
    { label: "Début du stage", value: startDisp },
    { label: "Détecté",       value: detectedDisp },
    { label: "Score",         value: (o.priority_score || "—") + "/10" },
    { label: "Éligibilité",   value: o.eligibility },
    { label: "Format",        value: o.format },
  ].filter(m => m.value && m.value !== "—" || ["Deadline", "Début du stage", "Détecté"].includes(m.label));

  let logoBlock = `<div class="modal-logo-row">${logoHTML(o)}<div class="modal-firm-block">
    <div class="modal-firm">${esc(o.firm)}</div>
    <div class="modal-program">${esc(o.program_name || "")}</div>
  </div></div>`;

  let html = logoBlock + `
    <div class="modal-meta-grid">
      ${meta.map(m => `
        <div class="modal-meta-item${m.accent ? " accent cat-" + esc(o.firm_category) : ""}">
          <div class="modal-meta-label">${esc(m.label)}</div>
          <div class="modal-meta-value">${esc(m.value)}</div>
        </div>
      `).join("")}
    </div>
  `;

  if (o.key_info) {
    html += `
      <div class="modal-section">
        <div class="modal-section-title">À préparer</div>
        <div class="modal-section-body">${esc(o.key_info)}</div>
      </div>
    `;
  }

  // Pré-application : seulement si c'est un favori OU une candidature en cours
  if (o.pre_application && (fav || stage)) {
    html += `
      <div class="modal-section">
        <div class="modal-section-title">Pré-application</div>
        <div class="modal-preapp">${esc(o.pre_application)}</div>
        <button class="modal-copy" id="copy-preapp">📋 Copier</button>
      </div>
    `;
  }

  // Pipeline picker (toujours visible : permet d'avancer dans le process)
  html += `
    <div class="modal-section">
      <div class="modal-section-title">Étape du processus</div>
      <div class="stage-picker">
        ${STAGES.map(s => `
          <button class="stage-btn ${s.id} ${stage === s.id ? "active" : ""}" data-stage="${s.id}">
            ${esc(s.label)}
          </button>
        `).join("")}
      </div>
      ${stage ? '<button class="modal-copy" id="clear-stage">Retirer de mes candidatures</button>' : ""}
    </div>
  `;

  // Action buttons
  html += `<div class="modal-actions">`;
  if (o.apply_url) {
    html += `<a class="btn-primary" href="${esc(o.apply_url)}" target="_blank" rel="noopener">↗ Ouvrir l'annonce</a>`;
  }
  html += `<button class="btn-secondary" data-action="toggle-fav">${fav ? "★ Retirer des favoris" : "☆ Ajouter aux favoris"}</button>`;
  html += `</div>`;

  body.innerHTML = html;

  // Listeners
  body.querySelectorAll(".stage-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const newStage = btn.dataset.stage;
      setCandidatureStage(id, newStage);
      renderAll();
      openDetail(id); // Re-render modal
    });
  });

  const clearBtn = body.querySelector("#clear-stage");
  if (clearBtn) {
    clearBtn.addEventListener("click", () => {
      setCandidatureStage(id, null);
      renderAll();
      openDetail(id);
    });
  }

  const toggleFavBtn = body.querySelector('[data-action="toggle-fav"]');
  if (toggleFavBtn) {
    toggleFavBtn.addEventListener("click", () => {
      toggleFavorite(id);
      renderAll();
      openDetail(id);
    });
  }

  const copyBtn = body.querySelector("#copy-preapp");
  if (copyBtn) {
    copyBtn.addEventListener("click", () => {
      navigator.clipboard.writeText(o.pre_application).then(() => {
        copyBtn.textContent = "✓ Copié";
        setTimeout(() => { copyBtn.textContent = "📋 Copier"; }, 1500);
      });
    });
  }

  document.getElementById("modal-backdrop").classList.add("open");

  // Re-render listes en arrière-plan pour appliquer le seen
  if (wasUnseen) renderAll();
}

function closeModal() {
  document.getElementById("modal-backdrop").classList.remove("open");
}

// ============================================================
// TABS
// ============================================================
function switchTab(name) {
  document.querySelectorAll(".topnav-tab").forEach(b => {
    b.classList.toggle("active", b.dataset.tab === name);
  });
  document.querySelectorAll(".view").forEach(v => {
    v.classList.toggle("active", v.id === "view-" + name);
  });
  // Update URL hash for shareability + reload memory
  if (history.replaceState) {
    history.replaceState(null, "", "#" + name);
  }
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// ============================================================
// UTILITIES
// ============================================================
function esc(s) {
  if (s === null || s === undefined) return "";
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function renderAll() {
  renderExplorer();
  renderCandidatures();
  renderFavoris();
}

// ============================================================
// INIT
// ============================================================
document.addEventListener("DOMContentLoaded", () => {
  // Restore theme ASAP (FOUC mitigation)
  setTheme(getTheme());

  // Theme toggle
  const themeBtn = document.getElementById("theme-toggle");
  if (themeBtn) themeBtn.addEventListener("click", toggleTheme);

  // Set footer
  if (GENERATED_AT) {
    document.getElementById("footer-updated").textContent = formatFriendlyDate(GENERATED_AT);
  }

  // Tabs
  document.querySelectorAll(".topnav-tab").forEach(b => {
    b.addEventListener("click", () => switchTab(b.dataset.tab));
  });

  // Modal close
  document.getElementById("modal-close").addEventListener("click", closeModal);
  document.getElementById("modal-backdrop").addEventListener("click", (e) => {
    if (e.target.id === "modal-backdrop") closeModal();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeModal();
  });

  // Restore tab from URL hash
  const hash = window.location.hash.slice(1);
  if (hash && ["explorer", "candidatures", "favoris"].includes(hash)) {
    switchTab(hash);
  }

  renderAll();
});
</script>
</body>
</html>
"""


# ============================================================
# Entry point
# ============================================================

def generate_site():
    """Génère docs/index.html à partir de state/opportunities.json."""
    opps = []
    if OPPORTUNITIES_FILE.exists():
        try:
            opps = json.loads(OPPORTUNITIES_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            opps = []

    normalized = normalize_opportunities(opps)
    now_iso = datetime.now(timezone.utc).isoformat()

    # JSON-encode safely for embedding inside <script>
    opps_json = (
        json.dumps(normalized, ensure_ascii=False)
        .replace("</", "<\\/")  # protège contre </script>
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )

    html = HTML_TEMPLATE.replace(
        "__OPPS_JSON__", opps_json
    ).replace(
        "__GENERATED_AT__", now_iso
    )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"  → site généré : {len(normalized)} opportunité(s) dans {OUTPUT_FILE}")


if __name__ == "__main__":
    generate_site()
