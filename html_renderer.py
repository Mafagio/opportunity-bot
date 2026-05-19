"""
html_renderer.py — Phase 1 : refonte visuelle complète.

Améliorations vs v1 :
  - Sections visuelles par action_required (À POSTULER / À PRÉPARER / WATCHLIST)
  - Sous-groupement par tier de firm (Quant HFT / Quant Research / Banques / etc.)
  - Logos des firms via Clearbit (fallback initiales si absent)
  - Deadlines colorées par urgence (basé sur deadline_iso fourni par Claude)
  - Theme orange/ambre
  - 3 modes de tri (priorité / deadline / récent)
  - Toggle "Cacher fermés" et "Cacher postulés"
  - Animations fade-in stagger, hover lift desktop
  - Empty state soigné
"""
import json
from pathlib import Path
from datetime import datetime, timezone


OPPORTUNITIES_FILE = Path("state/opportunities.json")
OUTPUT_FILE = Path("docs/index.html")


# ============================================================
# Firm metadata : tier + domain pour logo Clearbit
# Matching : substring case-insensitive sur le nom de firm.
# ============================================================

FIRM_METADATA = {
    # Tier 1 — Quant HFT / Market making
    "jane street": ("Quant HFT", "janestreet.com"),
    "optiver": ("Quant HFT", "optiver.com"),
    "imc": ("Quant HFT", "imc.com"),
    "citadel securities": ("Quant HFT", "citadelsecurities.com"),
    "citadel": ("Quant HFT", "citadel.com"),
    "hudson river": ("Quant HFT", "hudsonrivertrading.com"),
    "jump trading": ("Quant HFT", "jumptrading.com"),
    "drw": ("Quant HFT", "drw.com"),
    "five rings": ("Quant HFT", "fiverings.com"),
    "flow traders": ("Quant HFT", "flowtraders.com"),
    "sig ": ("Quant HFT", "sig.com"),
    "susquehanna": ("Quant HFT", "sig.com"),
    "xtx markets": ("Quant HFT", "xtxmarkets.com"),
    "tower research": ("Quant HFT", "tower-research.com"),
    "akuna": ("Quant HFT", "akunacapital.com"),
    "old mission": ("Quant HFT", "oldmissioncapital.com"),
    "vatic": ("Quant HFT", "vaticinvestments.com"),
    "tibra": ("Quant HFT", "tibra.com"),
    "da vinci": ("Quant HFT", "davincitrading.com"),
    "maven securities": ("Quant HFT", "mavensecurities.com"),

    # Tier 2 — Quant Research / Systematic Hedge Funds
    "d.e. shaw": ("Quant Research", "deshaw.com"),
    "de shaw": ("Quant Research", "deshaw.com"),
    "two sigma": ("Quant Research", "twosigma.com"),
    "g-research": ("Quant Research", "gresearch.com"),
    "g research": ("Quant Research", "gresearch.com"),
    "worldquant": ("Quant Research", "worldquant.com"),
    "aqr": ("Quant Research", "aqr.com"),
    "marshall wace": ("Quant Research", "mwam.com"),
    "capula": ("Quant Research", "capula.com"),
    "man group": ("Quant Research", "man.com"),
    "quadrature": ("Quant Research", "quadraturecapital.com"),
    "gsa capital": ("Quant Research", "gsacapital.com"),
    "trexquant": ("Quant Research", "trexquant.com"),
    "verition": ("Quant Research", "veritionfund.com"),
    "squarepoint": ("Quant Research", "squarepoint-capital.com"),
    "schonfeld": ("Quant Research", "schonfeld.com"),
    "millennium": ("Quant Research", "mlp.com"),
    "brevan howard": ("Quant Research", "brevanhoward.com"),
    "bluecrest": ("Quant Research", "bluecrestcapital.com"),
    "lansdowne": ("Quant Research", "lansdownepartners.com"),
    "point72": ("Quant Research", "point72.com"),
    "wincent": ("Quant Research", "wincent.com"),

    # Tier 3 — Investment Banks (London focus)
    "goldman sachs": ("Banques", "goldmansachs.com"),
    "jpmorgan": ("Banques", "jpmorgan.com"),
    "jp morgan": ("Banques", "jpmorgan.com"),
    "j.p. morgan": ("Banques", "jpmorgan.com"),
    "morgan stanley": ("Banques", "morganstanley.com"),
    "barclays": ("Banques", "barclays.com"),
    "deutsche bank": ("Banques", "db.com"),
    "bnp paribas": ("Banques", "bnpparibas.com"),
    "nomura": ("Banques", "nomura.com"),
    "macquarie": ("Banques", "macquarie.com"),
    "citi": ("Banques", "citigroup.com"),
    "bank of america": ("Banques", "bankofamerica.com"),
    "merrill lynch": ("Banques", "bankofamerica.com"),
    "hsbc": ("Banques", "hsbc.com"),
    "socgen": ("Banques", "societegenerale.com"),
    "societe generale": ("Banques", "societegenerale.com"),
    "société générale": ("Banques", "societegenerale.com"),

    # Tier 4 — Suisse
    "ubs": ("Suisse", "ubs.com"),
    "pictet": ("Suisse", "group.pictet"),
    "vontobel": ("Suisse", "vontobel.com"),
    "lombard odier": ("Suisse", "lombardodier.com"),
    "partners group": ("Suisse", "partnersgroup.com"),
    "swiss re": ("Suisse", "swissre.com"),
    "zurich insurance": ("Suisse", "zurich.com"),
    "julius baer": ("Suisse", "juliusbaer.com"),
    "mirabaud": ("Suisse", "mirabaud.com"),
    "edmond de rothschild": ("Suisse", "edmond-de-rothschild.com"),

    # Tier 5 — Asset Managers
    "blackrock": ("Asset Managers", "blackrock.com"),
    "state street": ("Asset Managers", "statestreet.com"),
    "vanguard": ("Asset Managers", "vanguard.com"),
    "alliancebernstein": ("Asset Managers", "alliancebernstein.com"),
    "pimco": ("Asset Managers", "pimco.com"),

    # Aggregators
    "quantnet": ("Aggregators", "quantnet.com"),
    "ratemyplacement": ("Aggregators", "ratemyplacement.co.uk"),
    "google alerts": ("Aggregators", None),
    "linkedin": ("Aggregators", "linkedin.com"),
}

TIER_ORDER = [
    "Quant HFT",
    "Quant Research",
    "Banques",
    "Suisse",
    "Asset Managers",
    "Aggregators",
    "Autres",
]

ACTION_ORDER = ["apply_now", "prepare_for_open", "add_to_watchlist"]


def lookup_firm(firm_name):
    """Returns (tier, domain) for a firm name. Case-insensitive substring match."""
    if not firm_name:
        return ("Autres", None)
    key = firm_name.lower()
    for pattern, (tier, domain) in FIRM_METADATA.items():
        if pattern in key:
            return (tier, domain)
    return ("Autres", None)


def enrich_opportunities(opps):
    """Ajoute _tier et _domain à chaque opportunity."""
    for opp in opps:
        tier, domain = lookup_firm(opp.get("firm", ""))
        opp["_tier"] = tier
        opp["_domain"] = domain
    return opps


# ============================================================
# Template HTML
# ============================================================

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex, nofollow, noarchive, nosnippet">
<meta name="googlebot" content="noindex, nofollow">
<meta name="theme-color" content="#0a0a0b" media="(prefers-color-scheme: dark)">
<meta name="theme-color" content="#fafafa" media="(prefers-color-scheme: light)">
<title>Opportunités Quant</title>
<style>
:root {
  --bg: #0a0a0b;
  --bg-card: #18181b;
  --bg-elevated: #27272a;
  --bg-hover: #2e2e32;
  --border: rgba(255,255,255,0.07);
  --border-strong: rgba(255,255,255,0.14);
  --text: #fafafa;
  --text-muted: #a1a1aa;
  --text-faint: #71717a;
  --accent: #f59e0b;
  --accent-hover: #d97706;
  --accent-soft: rgba(245,158,11,0.12);
  --green: #34d399;
  --green-soft: rgba(52,211,153,0.13);
  --red: #f87171;
  --red-soft: rgba(248,113,113,0.14);
  --shadow: 0 1px 2px rgba(0,0,0,0.4), 0 4px 14px rgba(0,0,0,0.25);
}
@media (prefers-color-scheme: light) {
  :root {
    --bg: #fafafa;
    --bg-card: #ffffff;
    --bg-elevated: #f4f4f5;
    --bg-hover: #ebebec;
    --border: rgba(0,0,0,0.07);
    --border-strong: rgba(0,0,0,0.13);
    --text: #18181b;
    --text-muted: #52525b;
    --text-faint: #71717a;
    --accent: #d97706;
    --accent-hover: #b45309;
    --accent-soft: rgba(217,119,6,0.10);
    --green: #059669;
    --green-soft: rgba(5,150,105,0.10);
    --red: #dc2626;
    --red-soft: rgba(220,38,38,0.10);
    --shadow: 0 1px 2px rgba(0,0,0,0.06), 0 4px 14px rgba(0,0,0,0.06);
  }
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { -webkit-text-size-adjust: 100%; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", system-ui, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.5;
  padding-bottom: 80px;
  -webkit-font-smoothing: antialiased;
  font-feature-settings: "cv02", "cv03", "cv11";
}
.container { max-width: 920px; margin: 0 auto; padding: 0 16px; }

/* HEADER */
header {
  position: sticky; top: 0;
  background: color-mix(in srgb, var(--bg) 88%, transparent);
  -webkit-backdrop-filter: saturate(180%) blur(16px);
  backdrop-filter: saturate(180%) blur(16px);
  border-bottom: 1px solid var(--border);
  padding: 14px 0 12px;
  z-index: 20;
}
h1 {
  font-size: 17px; font-weight: 650; letter-spacing: -0.015em;
  display: flex; align-items: center; gap: 8px;
}
h1::before {
  content: ""; width: 8px; height: 8px; border-radius: 50%;
  background: var(--accent); box-shadow: 0 0 12px var(--accent);
}
.stats {
  display: flex; gap: 18px; margin-top: 6px;
  font-size: 13px; color: var(--text-muted);
}
.stats strong { color: var(--text); font-weight: 600; }
.stats .urgent strong { color: var(--accent); }

/* CONTROLS */
.controls-wrap {
  position: sticky;
  top: 73px;
  background: color-mix(in srgb, var(--bg) 88%, transparent);
  -webkit-backdrop-filter: saturate(180%) blur(16px);
  backdrop-filter: saturate(180%) blur(16px);
  border-bottom: 1px solid var(--border);
  z-index: 15;
}
.controls {
  padding: 12px 0;
  display: flex; flex-wrap: wrap; gap: 8px;
  align-items: center;
}
.controls + .controls { padding-top: 0; }
.search {
  flex: 1; min-width: 180px;
  background: var(--bg-card); border: 1px solid var(--border); color: var(--text);
  padding: 9px 13px; border-radius: 10px; font-size: 14px;
  font-family: inherit; transition: border-color 0.15s;
}
.search:focus { outline: none; border-color: var(--accent); }
.search::placeholder { color: var(--text-faint); }
.sort-select {
  background: var(--bg-card); border: 1px solid var(--border); color: var(--text);
  padding: 9px 30px 9px 13px; border-radius: 10px; font-size: 13.5px;
  font-family: inherit; cursor: pointer; appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23a1a1aa' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 8px center;
  background-size: 14px;
}
.sort-select:focus { outline: none; border-color: var(--accent); }
.pill {
  background: var(--bg-card); border: 1px solid var(--border);
  padding: 7px 14px; border-radius: 999px; font-size: 13px;
  cursor: pointer; color: var(--text-muted); font-family: inherit;
  transition: all 0.12s;
  white-space: nowrap;
  display: inline-flex; align-items: center; gap: 5px;
}
.pill.active {
  background: var(--accent); border-color: var(--accent); color: #1a1100;
  font-weight: 600;
}
.pill:not(.active):hover { color: var(--text); border-color: var(--border-strong); }

/* SECTIONS */
.action-section { margin: 32px 0 8px; }
.action-section:first-child { margin-top: 20px; }
.section-header {
  display: flex; align-items: center; gap: 10px;
  padding: 0 4px 12px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 16px;
}
.section-emoji { font-size: 20px; }
.section-title {
  font-size: 11.5px; font-weight: 700; letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text);
}
.section-count {
  background: var(--bg-elevated); color: var(--text-muted);
  font-size: 12px; font-weight: 600;
  padding: 2px 9px; border-radius: 999px;
  border: 1px solid var(--border);
}

.action-section[data-action="apply_now"] .section-emoji { filter: drop-shadow(0 0 8px rgba(248,113,113,0.5)); }

.tier-group { margin-bottom: 24px; }
.tier-header {
  display: flex; align-items: center; gap: 8px;
  font-size: 11px; font-weight: 600; letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-faint);
  padding: 0 4px 8px;
}
.tier-count {
  color: var(--text-faint);
  font-weight: 500;
}

/* CARDS */
.cards { display: flex; flex-direction: column; gap: 10px; }
.card {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 14px; padding: 16px;
  transition: opacity 0.2s, transform 0.15s, box-shadow 0.15s, border-color 0.15s;
  animation: fadeInUp 0.35s ease-out both;
  animation-delay: var(--card-delay, 0ms);
}
@media (hover: hover) {
  .card:hover {
    transform: translateY(-1px);
    border-color: var(--border-strong);
    box-shadow: var(--shadow);
  }
}
.card.applied { opacity: 0.42; }
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* CARD HEAD */
.card-head {
  display: flex; align-items: flex-start; gap: 12px;
  margin-bottom: 12px;
}
.logo {
  width: 38px; height: 38px; border-radius: 9px; flex-shrink: 0;
  background: var(--bg-elevated);
  overflow: hidden;
  display: flex; align-items: center; justify-content: center;
  border: 1px solid var(--border);
}
.logo img {
  width: 100%; height: 100%; object-fit: contain;
}
.logo-initials {
  width: 100%; height: 100%;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 600; letter-spacing: -0.02em;
  color: var(--text-muted);
  background: var(--bg-elevated);
}
.firm-info { flex: 1; min-width: 0; }
.firm-name {
  font-size: 15.5px; font-weight: 600; letter-spacing: -0.012em;
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
}
.source-tag {
  font-size: 10px; padding: 2px 7px; border-radius: 4px; font-weight: 500;
  background: var(--bg-elevated); color: var(--text-faint);
  text-transform: uppercase; letter-spacing: 0.05em;
  border: 1px solid var(--border);
}
.program { font-size: 13px; color: var(--text-muted); margin-top: 3px; line-height: 1.4; }
.score-badge {
  flex-shrink: 0; padding: 5px 10px; border-radius: 8px;
  font-size: 12.5px; font-weight: 700;
  background: var(--bg-elevated); color: var(--text-muted);
  letter-spacing: -0.015em;
  border: 1px solid var(--border);
  font-variant-numeric: tabular-nums;
}
.score-badge.high { background: var(--red-soft); color: var(--red); border-color: transparent; }
.score-badge.med { background: var(--accent-soft); color: var(--accent); border-color: transparent; }
.score-badge.low { background: var(--bg-elevated); }

/* META */
.meta {
  display: flex; flex-direction: column; gap: 4px;
  font-size: 13px; padding: 10px 0 0;
  border-top: 1px solid var(--border);
}
.meta-row {
  display: grid; grid-template-columns: 86px 1fr; gap: 12px;
  padding: 2px 0;
}
.meta dt { color: var(--text-faint); font-weight: 500; }
.meta dd { color: var(--text); }
.deadline {
  display: inline-block;
  font-variant-numeric: tabular-nums;
}
.deadline.urgent { color: var(--red); font-weight: 600; }
.deadline.soon { color: var(--accent); font-weight: 600; }
.deadline.ok { color: var(--green); }
.deadline.past { color: var(--text-faint); text-decoration: line-through; }

/* INFO BLOCK */
.info-block {
  font-size: 13.5px; margin: 12px 0; padding: 11px 14px;
  background: var(--accent-soft); border-radius: 9px;
  border-left: 3px solid var(--accent);
  color: var(--text);
  line-height: 1.55;
}

/* PRE-APPLICATION */
.preapp {
  margin: 12px 0; border-radius: 10px;
  background: var(--bg-elevated); overflow: hidden;
  border: 1px solid var(--border);
}
.preapp summary {
  padding: 11px 14px; cursor: pointer; font-size: 13px;
  color: var(--text-muted); font-weight: 500;
  list-style: none;
  display: flex; align-items: center; justify-content: space-between;
  transition: background 0.12s;
}
.preapp summary::-webkit-details-marker { display: none; }
.preapp summary:hover { background: var(--bg-hover); }
.preapp summary::after {
  content: "▾"; transition: transform 0.18s; font-size: 10px; color: var(--text-faint);
}
.preapp[open] summary::after { transform: rotate(180deg); }
.preapp[open] summary { border-bottom: 1px solid var(--border); }
.preapp-content {
  padding: 14px; font-size: 13.5px; line-height: 1.65;
  white-space: pre-wrap; color: var(--text);
}

/* ACTIONS */
.actions {
  display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap;
}
.btn {
  flex: 1; min-width: 130px; padding: 10px 14px; text-align: center;
  border-radius: 10px; font-size: 13.5px; font-weight: 500;
  border: 1px solid var(--border); background: var(--bg-elevated);
  color: var(--text); text-decoration: none; cursor: pointer;
  font-family: inherit;
  transition: all 0.12s;
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
}
.btn:hover { border-color: var(--border-strong); background: var(--bg-hover); }
.btn-primary {
  background: var(--accent); border-color: var(--accent); color: #1a1100;
  font-weight: 600;
}
.btn-primary:hover { background: var(--accent-hover); border-color: var(--accent-hover); }
.btn-toggle.active {
  background: var(--green-soft); border-color: var(--green); color: var(--green);
  font-weight: 600;
}

/* EMPTY */
.empty {
  text-align: center; padding: 80px 24px;
}
.empty-icon { font-size: 38px; margin-bottom: 12px; opacity: 0.7; }
.empty-text { color: var(--text-muted); font-size: 14px; }

/* FOOTER */
.last-update {
  font-size: 11.5px; color: var(--text-faint);
  text-align: center; margin-top: 40px;
  letter-spacing: 0.01em;
}

/* MOBILE */
@media (max-width: 520px) {
  .controls-wrap { top: 70px; }
  .controls { gap: 6px; padding: 10px 0; }
  .pill { padding: 6px 11px; font-size: 12.5px; }
  .card { padding: 14px; border-radius: 12px; }
  .stats { gap: 14px; font-size: 12.5px; }
  .section-emoji { font-size: 17px; }
  .meta-row { grid-template-columns: 78px 1fr; }
  .firm-name { font-size: 15px; }
}
</style>
</head>
<body>
<header>
  <div class="container">
    <h1>Opportunités Quant</h1>
    <div class="stats">
      <span><strong id="stat-total">0</strong> total</span>
      <span class="urgent"><strong id="stat-apply">0</strong> à postuler</span>
      <span><strong id="stat-week">0</strong> cette semaine</span>
    </div>
  </div>
</header>

<div class="controls-wrap">
  <div class="container">
    <div class="controls">
      <input type="search" id="search" class="search" placeholder="Rechercher firm, programme, lieu…" autocomplete="off" enterkeyhint="search">
      <select id="sort" class="sort-select">
        <option value="priority">Priorité</option>
        <option value="deadline">Deadline</option>
        <option value="recent">Récent</option>
      </select>
    </div>
    <div class="controls">
      <button class="pill active" data-filter="all">Tout</button>
      <button class="pill" data-filter="apply_now">🔥 À postuler</button>
      <button class="pill" data-filter="prepare_for_open">⏳ À préparer</button>
      <button class="pill" data-filter="add_to_watchlist">👀 Watchlist</button>
      <button class="pill" id="toggle-closed">Cacher fermés</button>
      <button class="pill" id="toggle-applied">Cacher postulés</button>
    </div>
  </div>
</div>

<main class="container">
  <div id="feed"></div>
  <div class="last-update" id="last-update"></div>
</main>

<script>
const DATA = __DATA__;
const GENERATED_AT = "__GENERATED_AT__";

const ACTION_EMOJI = { apply_now: "🔥", prepare_for_open: "⏳", add_to_watchlist: "👀" };
const ACTION_LABEL = { apply_now: "À POSTULER", prepare_for_open: "À PRÉPARER", add_to_watchlist: "WATCHLIST" };
const ACTION_ORDER = ["apply_now", "prepare_for_open", "add_to_watchlist"];
const TIER_ORDER = ["Quant HFT", "Quant Research", "Banques", "Suisse", "Asset Managers", "Aggregators", "Autres"];

let state = {
  search: "",
  filter: "all",
  hideClosed: false,
  hideApplied: false,
  sort: "priority",
};

let applied = {};
try { applied = JSON.parse(localStorage.getItem("applied_v1") || "{}"); } catch(e) { applied = {}; }

function daysUntil(iso) {
  if (!iso) return null;
  const d = new Date(iso + "T23:59:59");
  const today = new Date();
  return Math.floor((d.getTime() - today.getTime()) / 86400000);
}

function deadlineStatus(opp) {
  const days = daysUntil(opp.deadline_iso);
  if (days === null) return "unknown";
  if (days < 0) return "past";
  if (days < 7) return "urgent";
  if (days < 30) return "soon";
  return "ok";
}

function isClosed(opp) {
  return deadlineStatus(opp) === "past";
}

function escapeHtml(s) {
  if (s === null || s === undefined) return "";
  return String(s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function getInitials(firm) {
  if (!firm) return "?";
  const cleaned = firm.replace(/[^a-zA-Z\\s]/g, "").trim();
  if (!cleaned) return "?";
  const words = cleaned.split(/\\s+/);
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[1][0]).toUpperCase();
}

function formatRelative(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  const days = Math.floor((Date.now() - d.getTime()) / 86400000);
  if (days <= 0) return "aujourd'hui";
  if (days === 1) return "hier";
  if (days < 7) return "il y a " + days + "j";
  if (days < 30) return "il y a " + Math.floor(days/7) + " sem.";
  return d.toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
}

function deadlineSuffix(opp) {
  const days = daysUntil(opp.deadline_iso);
  if (days === null) return "";
  if (days < 0) return " · passé";
  if (days === 0) return " · aujourd'hui";
  if (days === 1) return " · demain";
  if (days < 31) return " · dans " + days + "j";
  return "";
}

function sourceLabel(kind) {
  const labels = { careers_page: "Careers", google_alerts: "Google", linkedin_alerts: "LinkedIn" };
  return labels[kind] || "";
}

function filterOpps(opps) {
  return opps.filter(o => {
    if (state.hideApplied && applied[o.id]) return false;
    if (state.filter !== "all" && o.action_required !== state.filter) return false;
    if (state.hideClosed && isClosed(o)) return false;
    if (state.search) {
      const hay = (o.firm + " " + (o.program_name||"") + " " + (o.location||"") + " " + (o.key_info||"")).toLowerCase();
      if (!hay.includes(state.search)) return false;
    }
    return true;
  });
}

function sortOpps(opps) {
  const arr = [...opps];
  if (state.sort === "deadline") {
    arr.sort((a, b) => {
      const ad = daysUntil(a.deadline_iso);
      const bd = daysUntil(b.deadline_iso);
      if (ad === null && bd === null) return (b.priority_score||0) - (a.priority_score||0);
      if (ad === null) return 1;
      if (bd === null) return -1;
      return ad - bd;
    });
  } else if (state.sort === "recent") {
    arr.sort((a, b) => (b.first_seen||"").localeCompare(a.first_seen||""));
  } else {
    arr.sort((a, b) => {
      const ai = ACTION_ORDER.indexOf(a.action_required);
      const bi = ACTION_ORDER.indexOf(b.action_required);
      const av = ai === -1 ? 99 : ai;
      const bv = bi === -1 ? 99 : bi;
      if (av !== bv) return av - bv;
      return (b.priority_score||0) - (a.priority_score||0);
    });
  }
  return arr;
}

function groupByActionAndTier(opps) {
  const groups = {};
  for (const action of ACTION_ORDER) groups[action] = {};
  for (const opp of opps) {
    const action = opp.action_required || "add_to_watchlist";
    if (action === "not_relevant") continue;
    if (!groups[action]) groups[action] = {};
    const tier = opp._tier || "Autres";
    if (!groups[action][tier]) groups[action][tier] = [];
    groups[action][tier].push(opp);
  }
  return groups;
}

function renderCard(opp, index) {
  const isApplied = !!applied[opp.id];
  const score = opp.priority_score || "—";
  const scoreClass = (opp.priority_score >= 8) ? "high" : (opp.priority_score >= 5) ? "med" : "low";
  const dStatus = deadlineStatus(opp);
  const dSuffix = deadlineSuffix(opp);
  const initials = getInitials(opp.firm);
  const logoUrl = opp._domain ? "https://logo.clearbit.com/" + opp._domain + "?size=80" : "";
  const src = sourceLabel(opp.source);
  const delay = Math.min(index * 25, 500);

  return [
    '<article class="card ' + (isApplied ? 'applied' : '') + '" style="--card-delay:' + delay + 'ms" data-id="' + opp.id + '">',
      '<div class="card-head">',
        '<div class="logo">',
          (logoUrl ? '<img src="' + logoUrl + '" alt="" onerror="this.style.display=&#39;none&#39;;this.nextElementSibling.style.display=&#39;flex&#39;">' : ''),
          '<div class="logo-initials"' + (logoUrl ? ' style="display:none"' : '') + '>' + initials + '</div>',
        '</div>',
        '<div class="firm-info">',
          '<div class="firm-name">' + escapeHtml(opp.firm) + (src ? '<span class="source-tag">' + escapeHtml(src) + '</span>' : '') + '</div>',
          '<div class="program">' + escapeHtml(opp.program_name || "Programme non spécifié") + '</div>',
        '</div>',
        '<div class="score-badge ' + scoreClass + '">' + score + '/10</div>',
      '</div>',
      '<dl class="meta">',
        (opp.deadline ? '<div class="meta-row"><dt>Deadline</dt><dd><span class="deadline ' + dStatus + '">' + escapeHtml(opp.deadline) + escapeHtml(dSuffix) + '</span></dd></div>' : ''),
        (opp.location ? '<div class="meta-row"><dt>Lieu</dt><dd>' + escapeHtml(opp.location) + '</dd></div>' : ''),
        (opp.eligibility ? '<div class="meta-row"><dt>Éligibilité</dt><dd>' + escapeHtml(opp.eligibility) + '</dd></div>' : ''),
        (opp.format ? '<div class="meta-row"><dt>Format</dt><dd>' + escapeHtml(opp.format) + '</dd></div>' : ''),
        '<div class="meta-row"><dt>Détecté</dt><dd>' + formatRelative(opp.first_seen) + '</dd></div>',
      '</dl>',
      (opp.key_info ? '<div class="info-block">' + escapeHtml(opp.key_info) + '</div>' : ''),
      (opp.pre_application ? [
        '<details class="preapp">',
          '<summary>Voir la pré-application</summary>',
          '<div class="preapp-content">' + escapeHtml(opp.pre_application) + '</div>',
        '</details>'
      ].join('') : ''),
      '<div class="actions">',
        (opp.apply_url ? '<a class="btn btn-primary" href="' + escapeHtml(opp.apply_url) + '" target="_blank" rel="noopener noreferrer">Postuler →</a>' : ''),
        '<button class="btn btn-toggle ' + (isApplied ? 'active' : '') + '" data-toggle="' + opp.id + '">' + (isApplied ? '✓ Postulé' : 'Marquer postulé') + '</button>',
      '</div>',
    '</article>'
  ].join('');
}

function render() {
  const feed = document.getElementById("feed");
  const opps = sortOpps(filterOpps(DATA));

  if (opps.length === 0) {
    feed.innerHTML = '<div class="empty"><div class="empty-icon">🌙</div><div class="empty-text">Rien à voir ici. Tu as peut-être trop filtré, ou tout est calme aujourd\\u2019hui.</div></div>';
    updateStats();
    return;
  }

  const groups = groupByActionAndTier(opps);
  let html = "";
  let cardIndex = 0;

  for (const action of ACTION_ORDER) {
    const tierGroups = groups[action];
    if (!tierGroups) continue;
    const total = Object.values(tierGroups).reduce((s, a) => s + a.length, 0);
    if (total === 0) continue;

    html += '<section class="action-section" data-action="' + action + '">';
    html += '<header class="section-header">';
    html +=   '<span class="section-emoji">' + ACTION_EMOJI[action] + '</span>';
    html +=   '<span class="section-title">' + ACTION_LABEL[action] + '</span>';
    html +=   '<span class="section-count">' + total + '</span>';
    html += '</header>';

    for (const tier of TIER_ORDER) {
      const tierOpps = tierGroups[tier];
      if (!tierOpps || tierOpps.length === 0) continue;
      html += '<div class="tier-group">';
      html +=   '<div class="tier-header">' + tier + ' <span class="tier-count">· ' + tierOpps.length + '</span></div>';
      html +=   '<div class="cards">';
      for (const o of tierOpps) html += renderCard(o, cardIndex++);
      html +=   '</div>';
      html += '</div>';
    }
    html += '</section>';
  }

  feed.innerHTML = html;

  feed.querySelectorAll('[data-toggle]').forEach(btn => {
    btn.addEventListener("click", () => toggleApplied(btn.dataset.toggle));
  });

  updateStats();
}

function updateStats() {
  document.getElementById("stat-total").textContent = DATA.length;
  document.getElementById("stat-apply").textContent =
    DATA.filter(o => o.action_required === "apply_now" && !applied[o.id]).length;
  const weekAgo = Date.now() - 7 * 86400000;
  document.getElementById("stat-week").textContent =
    DATA.filter(o => o.first_seen && new Date(o.first_seen).getTime() > weekAgo).length;
}

function toggleApplied(id) {
  if (applied[id]) delete applied[id];
  else applied[id] = new Date().toISOString();
  localStorage.setItem("applied_v1", JSON.stringify(applied));
  render();
}

// Filter pills (action_required)
document.querySelectorAll(".pill[data-filter]").forEach(p => {
  p.addEventListener("click", () => {
    document.querySelectorAll(".pill[data-filter]").forEach(x => x.classList.remove("active"));
    p.classList.add("active");
    state.filter = p.dataset.filter;
    render();
  });
});

document.getElementById("toggle-closed").addEventListener("click", function() {
  state.hideClosed = !state.hideClosed;
  this.classList.toggle("active", state.hideClosed);
  render();
});

document.getElementById("toggle-applied").addEventListener("click", function() {
  state.hideApplied = !state.hideApplied;
  this.classList.toggle("active", state.hideApplied);
  render();
});

document.getElementById("sort").addEventListener("change", function() {
  state.sort = this.value;
  render();
});

document.getElementById("search").addEventListener("input", function() {
  state.search = this.value.toLowerCase().trim();
  render();
});

document.getElementById("last-update").textContent =
  "Mis à jour " + new Date(GENERATED_AT).toLocaleString("fr-FR", { dateStyle: "medium", timeStyle: "short" });

render();
</script>
</body>
</html>
"""


def generate_site():
    """Génère docs/index.html à partir de state/opportunities.json."""
    OUTPUT_FILE.parent.mkdir(exist_ok=True, parents=True)

    if OPPORTUNITIES_FILE.exists():
        try:
            opportunities = json.loads(OPPORTUNITIES_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            opportunities = []
    else:
        opportunities = []

    opportunities = enrich_opportunities(opportunities)

    # Tri par défaut (Python side) — JS peut re-trier après
    def action_idx(o):
        a = o.get("action_required", "add_to_watchlist")
        return ACTION_ORDER.index(a) if a in ACTION_ORDER else 99

    opportunities.sort(
        key=lambda o: (
            action_idx(o),
            -(o.get("priority_score") or 0),
            o.get("last_seen", ""),
        )
    )

    # Injection sûre dans le script
    data_json = json.dumps(opportunities, ensure_ascii=False, default=str)
    data_json = data_json.replace("<", "\\u003C").replace(">", "\\u003E")

    generated_at = datetime.now(timezone.utc).isoformat()

    html = HTML_TEMPLATE.replace("__DATA__", data_json)
    html = html.replace("__GENERATED_AT__", generated_at)

    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"  → site généré : {len(opportunities)} opportunité(s) dans {OUTPUT_FILE}")


if __name__ == "__main__":
    generate_site()
