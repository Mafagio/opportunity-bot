"""
Génère le site web statique (docs/index.html) à partir de state/opportunities.json.
Servi par GitHub Pages à https://<username>.github.io/<repo>/

Design : single-file HTML avec données JSON embeddées, dark mode automatique,
filtres par action_required, recherche, localStorage pour marquer "postulé".
"""
import json
from pathlib import Path
from datetime import datetime, timezone


OPPORTUNITIES_FILE = Path("state/opportunities.json")
OUTPUT_FILE = Path("docs/index.html")


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex, nofollow, noarchive, nosnippet">
<meta name="googlebot" content="noindex, nofollow">
<meta name="theme-color" content="#0f0f10" media="(prefers-color-scheme: dark)">
<meta name="theme-color" content="#fafafa" media="(prefers-color-scheme: light)">
<title>Opportunités Quant</title>
<style>
:root {
  --bg: #0f0f10;
  --bg-card: #1a1a1c;
  --bg-elevated: #232326;
  --border: rgba(255,255,255,0.08);
  --border-strong: rgba(255,255,255,0.16);
  --text: #e8e8e8;
  --text-muted: #8a8a8a;
  --text-faint: #5a5a5a;
  --accent: #818cf8;
  --accent-dark: #6366f1;
  --warn: #fbbf24;
  --danger: #fca5a5;
  --success: #34d399;
}
@media (prefers-color-scheme: light) {
  :root {
    --bg: #fafafa;
    --bg-card: #ffffff;
    --bg-elevated: #f3f3f4;
    --border: rgba(0,0,0,0.08);
    --border-strong: rgba(0,0,0,0.14);
    --text: #1a1a1a;
    --text-muted: #6a6a6a;
    --text-faint: #9a9a9a;
    --accent: #4f46e5;
    --accent-dark: #4338ca;
    --warn: #b45309;
    --danger: #b91c1c;
    --success: #047857;
  }
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html { -webkit-text-size-adjust: 100%; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", system-ui, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.5;
  padding-bottom: 60px;
  -webkit-font-smoothing: antialiased;
}
.container { max-width: 880px; margin: 0 auto; padding: 0 16px; }
header {
  position: sticky; top: 0;
  background: color-mix(in srgb, var(--bg) 92%, transparent);
  -webkit-backdrop-filter: saturate(180%) blur(14px);
  backdrop-filter: saturate(180%) blur(14px);
  border-bottom: 1px solid var(--border);
  padding: 14px 0 12px;
  z-index: 10;
}
h1 { font-size: 17px; font-weight: 600; letter-spacing: -0.01em; }
.stats { display: flex; gap: 18px; margin-top: 6px; font-size: 13px; color: var(--text-muted); }
.stats strong { color: var(--text); font-weight: 600; }
.stats .urgent strong { color: var(--danger); }
.controls {
  padding: 14px 0 6px;
  display: flex; flex-wrap: wrap; gap: 8px;
  align-items: center;
}
.search {
  flex: 1; min-width: 180px;
  background: var(--bg-card); border: 1px solid var(--border); color: var(--text);
  padding: 9px 12px; border-radius: 10px; font-size: 14px;
  font-family: inherit;
}
.search:focus { outline: none; border-color: var(--accent); }
.pill {
  background: var(--bg-card); border: 1px solid var(--border);
  padding: 7px 13px; border-radius: 999px; font-size: 13px;
  cursor: pointer; color: var(--text-muted); font-family: inherit;
  transition: all 0.12s;
  white-space: nowrap;
}
.pill.active {
  background: var(--accent); border-color: var(--accent); color: white;
  font-weight: 500;
}
.pill:hover:not(.active) { color: var(--text); border-color: var(--border-strong); }
.card {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 14px; padding: 16px; margin-bottom: 12px;
  transition: opacity 0.2s, transform 0.2s;
}
.card.applied { opacity: 0.45; }
.card-head {
  display: flex; align-items: flex-start; gap: 12px;
  margin-bottom: 12px;
}
.action-emoji { font-size: 22px; line-height: 1.1; flex-shrink: 0; padding-top: 1px; }
.firm-info { flex: 1; min-width: 0; }
.firm-name {
  font-size: 16px; font-weight: 600; letter-spacing: -0.01em;
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
}
.source-tag {
  font-size: 10.5px; padding: 2px 7px; border-radius: 4px; font-weight: 500;
  background: var(--bg-elevated); color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.04em;
}
.program { font-size: 13.5px; color: var(--text-muted); margin-top: 3px; }
.score-badge {
  flex-shrink: 0; padding: 5px 11px; border-radius: 8px;
  font-size: 13px; font-weight: 600;
  background: var(--bg-elevated); color: var(--text-muted);
  letter-spacing: -0.01em;
}
.score-badge.high { background: rgba(252,165,165,0.14); color: var(--danger); }
.score-badge.med { background: rgba(251,191,36,0.14); color: var(--warn); }
.score-badge.low { background: rgba(129,140,248,0.14); color: var(--accent); }
.meta {
  display: grid; grid-template-columns: auto 1fr; gap: 5px 14px;
  font-size: 13px; padding: 10px 0; border-top: 1px solid var(--border);
}
.meta dt { color: var(--text-muted); }
.meta dd { color: var(--text); }
.info-block {
  font-size: 13.5px; margin: 12px 0; padding: 10px 12px;
  background: var(--bg-elevated); border-radius: 8px;
  border-left: 3px solid var(--accent);
}
.preapp {
  margin: 12px 0; border-radius: 10px;
  background: var(--bg-elevated); overflow: hidden;
}
.preapp summary {
  padding: 11px 14px; cursor: pointer; font-size: 13px;
  color: var(--text-muted); font-weight: 500;
  list-style: none;
  display: flex; align-items: center; justify-content: space-between;
}
.preapp summary::after {
  content: "▾"; transition: transform 0.15s; font-size: 11px;
}
.preapp[open] summary::after { transform: rotate(180deg); }
.preapp[open] summary { border-bottom: 1px solid var(--border); }
.preapp-content {
  padding: 14px; font-size: 13.5px; line-height: 1.65;
  white-space: pre-wrap; color: var(--text);
}
.actions { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }
.btn {
  flex: 1; min-width: 130px; padding: 10px 14px; text-align: center;
  border-radius: 10px; font-size: 13.5px; font-weight: 500;
  border: 1px solid var(--border); background: var(--bg-elevated);
  color: var(--text); text-decoration: none; cursor: pointer;
  font-family: inherit;
  transition: all 0.12s;
}
.btn:hover { border-color: var(--border-strong); }
.btn-primary {
  background: var(--accent); border-color: var(--accent); color: white;
}
.btn-primary:hover { background: var(--accent-dark); border-color: var(--accent-dark); }
.btn-toggle.active {
  background: var(--success); border-color: var(--success); color: white;
}
.empty { text-align: center; color: var(--text-muted); padding: 64px 24px; font-size: 14px; }
.last-update {
  font-size: 12px; color: var(--text-faint);
  text-align: center; margin-top: 32px;
}
@media (max-width: 480px) {
  .controls { gap: 6px; }
  .pill { padding: 6px 11px; font-size: 12.5px; }
  .card { padding: 14px; }
  .stats { gap: 14px; font-size: 12.5px; }
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

<main class="container">
  <div class="controls">
    <input type="search" id="search" class="search" placeholder="Rechercher firm, programme, lieu…" autocomplete="off">
  </div>
  <div class="controls" style="padding-top:0;">
    <button class="pill active" data-filter="all">Tout</button>
    <button class="pill" data-filter="apply_now">🔥 À postuler</button>
    <button class="pill" data-filter="prepare_for_open">⏳ À préparer</button>
    <button class="pill" data-filter="add_to_watchlist">👀 Watchlist</button>
    <button class="pill" data-filter="hide_applied">Masquer postulés</button>
  </div>
  <div id="feed"></div>
  <div class="last-update" id="last-update"></div>
</main>

<script>
const DATA = __DATA_PLACEHOLDER__;
const GENERATED_AT = "__GENERATED_AT__";

const APPLIED_KEY = "applied_v1";
let applied = {};
try { applied = JSON.parse(localStorage.getItem(APPLIED_KEY) || "{}"); } catch(e) { applied = {}; }

let activeFilter = "all";
let hideApplied = false;
let searchQuery = "";

const ACTION_EMOJI = {
  apply_now: "🔥",
  prepare_for_open: "⏳",
  add_to_watchlist: "👀",
};

function scoreClass(s) {
  if (!s) return "";
  if (s >= 8) return "high";
  if (s >= 5) return "med";
  return "low";
}

function formatRelative(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  const days = Math.floor((Date.now() - d.getTime()) / 86400000);
  if (days <= 0) return "aujourd'hui";
  if (days === 1) return "hier";
  if (days < 7) return "il y a " + days + " jours";
  if (days < 30) return "il y a " + Math.floor(days/7) + " sem.";
  return d.toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
}

function escapeHtml(s) {
  if (s === null || s === undefined) return "";
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function sourceLabel(kind) {
  const labels = {
    careers_page: "Careers",
    google_alerts: "Google Alert",
    linkedin_alerts: "LinkedIn",
  };
  return labels[kind] || kind || "";
}

function render() {
  const feed = document.getElementById("feed");
  const filtered = DATA.filter(o => {
    if (hideApplied && applied[o.id]) return false;
    if (activeFilter !== "all" && activeFilter !== "hide_applied" && o.action_required !== activeFilter) return false;
    if (searchQuery) {
      const hay = (o.firm + " " + (o.program_name||"") + " " + (o.location||"") + " " + (o.key_info||"")).toLowerCase();
      if (!hay.includes(searchQuery)) return false;
    }
    return true;
  });

  if (filtered.length === 0) {
    feed.innerHTML = '<div class="empty">Aucune opportunité ne correspond à ce filtre.</div>';
    return;
  }

  feed.innerHTML = filtered.map(o => {
    const isApplied = !!applied[o.id];
    const emoji = ACTION_EMOJI[o.action_required] || "📍";
    const sc = scoreClass(o.priority_score);
    const score = o.priority_score || "—";
    const src = sourceLabel(o.source);
    return [
      '<article class="card ' + (isApplied ? 'applied' : '') + '" data-id="' + o.id + '">',
        '<div class="card-head">',
          '<span class="action-emoji">' + emoji + '</span>',
          '<div class="firm-info">',
            '<div class="firm-name">' + escapeHtml(o.firm) + (src ? '<span class="source-tag">' + escapeHtml(src) + '</span>' : '') + '</div>',
            '<div class="program">' + escapeHtml(o.program_name || "Programme non spécifié") + '</div>',
          '</div>',
          '<div class="score-badge ' + sc + '">' + score + '/10</div>',
        '</div>',
        '<dl class="meta">',
          (o.deadline ? '<dt>Deadline</dt><dd>' + escapeHtml(o.deadline) + '</dd>' : ''),
          (o.location ? '<dt>Lieu</dt><dd>' + escapeHtml(o.location) + '</dd>' : ''),
          (o.eligibility ? '<dt>Éligibilité</dt><dd>' + escapeHtml(o.eligibility) + '</dd>' : ''),
          (o.format ? '<dt>Format</dt><dd>' + escapeHtml(o.format) + '</dd>' : ''),
          '<dt>Détecté</dt><dd>' + formatRelative(o.first_seen) + '</dd>',
        '</dl>',
        (o.key_info ? '<div class="info-block">' + escapeHtml(o.key_info) + '</div>' : ''),
        (o.pre_application ? [
          '<details class="preapp">',
            '<summary>Voir la pré-application</summary>',
            '<div class="preapp-content">' + escapeHtml(o.pre_application) + '</div>',
          '</details>'
        ].join('') : ''),
        '<div class="actions">',
          (o.apply_url ? '<a class="btn btn-primary" href="' + escapeHtml(o.apply_url) + '" target="_blank" rel="noopener noreferrer">Postuler →</a>' : ''),
          '<button class="btn btn-toggle ' + (isApplied ? 'active' : '') + '" data-id="' + o.id + '">' + (isApplied ? '✓ Postulé' : 'Marquer postulé') + '</button>',
        '</div>',
      '</article>'
    ].join('');
  }).join("");

  feed.querySelectorAll(".btn-toggle").forEach(btn => {
    btn.addEventListener("click", () => toggleApplied(btn.dataset.id));
  });
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
  localStorage.setItem(APPLIED_KEY, JSON.stringify(applied));
  render();
  updateStats();
}

document.querySelectorAll(".pill").forEach(p => {
  p.addEventListener("click", () => {
    if (p.dataset.filter === "hide_applied") {
      hideApplied = !hideApplied;
      p.classList.toggle("active", hideApplied);
    } else {
      document.querySelectorAll(".pill").forEach(x => {
        if (x.dataset.filter !== "hide_applied") x.classList.remove("active");
      });
      p.classList.add("active");
      activeFilter = p.dataset.filter;
    }
    render();
  });
});

document.getElementById("search").addEventListener("input", e => {
  searchQuery = e.target.value.toLowerCase().trim();
  render();
});

const updated = new Date(GENERATED_AT);
document.getElementById("last-update").textContent =
  "Mis à jour " + updated.toLocaleString("fr-FR", { dateStyle: "medium", timeStyle: "short" });

render();
updateStats();
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

    # Tri : action_required priority, puis score décroissant, puis last_seen
    action_order = {"apply_now": 0, "prepare_for_open": 1, "add_to_watchlist": 2}
    opportunities.sort(
        key=lambda o: (
            action_order.get(o.get("action_required", "add_to_watchlist"), 3),
            -(o.get("priority_score") or 0),
            o.get("last_seen", ""),
        )
    )

    # Échappement pour injection sûre dans <script>
    data_json = json.dumps(opportunities, ensure_ascii=False)
    data_json = data_json.replace("<", "\\u003C").replace(">", "\\u003E")

    generated_at = datetime.now(timezone.utc).isoformat()

    html = HTML_TEMPLATE.replace("__DATA_PLACEHOLDER__", data_json)
    html = html.replace("__GENERATED_AT__", generated_at)

    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"  → site généré : {len(opportunities)} opportunité(s) dans {OUTPUT_FILE}")


if __name__ == "__main__":
    generate_site()
