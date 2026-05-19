# Bot de veille — Marche à suivre

## Étape 0 — Pré-requis

Crée-toi des comptes (gratuits, 5 min total) :
- **GitHub** : github.com (si pas déjà fait)
- **Telegram** : installe l'app
- **Anthropic Console** : console.anthropic.com (compte SÉPARÉ de ton Claude Pro)

Installe sur ton ordi :
- Python 3.11+ (`python --version`)
- Git (`git --version`)
- Un éditeur (VS Code conseillé)

---

## Étape 1 — Crée le bot Telegram (3 min)

1. Ouvre Telegram, cherche **@BotFather**, démarre une conversation.
2. Envoie `/newbot`
3. Donne un nom à ton bot (ex : `Mon Bot Veille`)
4. Donne un username unique terminant par `bot` (ex : `epfl_veille_bot`)
5. **BotFather te donne un TOKEN** du genre `1234567890:ABCdefGHI...`. Garde-le.
6. Cherche maintenant ton bot dans Telegram (par son username), ouvre la conversation, clique **Démarrer** (/start).
7. Récupère ton **chat_id** : ouvre dans le navigateur (remplace `<TOKEN>`) :
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
   Tu verras un JSON. Cherche `"chat":{"id": 123456789, ...}` → **ce nombre est ton chat_id**.

Note quelque part : `TELEGRAM_TOKEN` et `TELEGRAM_CHAT_ID`.

---

## Étape 2 — Crée la clé API Anthropic (2 min)

1. Va sur **console.anthropic.com** et inscris-toi (compte séparé de Claude Pro).
2. Plans & Billing → **ajoute 5 USD de crédits** (assez pour 6+ mois à ce rythme).
3. API Keys → **Create Key** → copie la clé qui commence par `sk-ant-...`.

Note : `ANTHROPIC_API_KEY`.

---

## Étape 3 — Crée le repo GitHub (5 min)

1. Sur github.com → New repository → nom : `opportunity-bot` → **Private** → Create.
2. Sur ton ordi, dans le terminal :
   ```bash
   cd ~/Documents  # ou où tu veux
   mkdir opportunity-bot && cd opportunity-bot
   git init
   git remote add origin https://github.com/<ton-username>/opportunity-bot.git
   ```
3. Copie dans ce dossier les fichiers fournis : `bot.py`, `firms.yaml`, `profile.md`, `requirements.txt`, `.gitignore`, le dossier `.github/workflows/daily-check.yml`, et le dossier `state/hashes.json`.

---

## Étape 4 — Personnalise `profile.md`

Ouvre `profile.md` et remplis avec TES infos : nom, année de graduation, GPA, projets, compétitions. Plus c'est précis, meilleures seront les pré-applications générées.

---

## Étape 5 — Test local (optionnel mais recommandé)

Pour vérifier que ça marche avant de déployer :

```bash
python -m venv .venv
source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install -r requirements.txt

export ANTHROPIC_API_KEY="sk-ant-..."
export TELEGRAM_TOKEN="1234567890:ABC..."
export TELEGRAM_CHAT_ID="123456789"

python bot.py
```

Tu devrais voir le bot vérifier chaque firm. Au premier run, il considère TOUT comme nouveau, donc tu vas recevoir une rafale de notifications Telegram avec les programmes actuellement ouverts pour chaque firm. C'est normal et utile : ça te donne un état des lieux immédiat.

Si une firm donne une erreur HTTP 403 ou 404 : commente sa ligne dans `firms.yaml` ou trouve la bonne URL.

---

## Étape 6 — Configure les secrets GitHub

1. Repo GitHub → Settings → Secrets and variables → Actions → **New repository secret**.
2. Crée 3 secrets :
   - `ANTHROPIC_API_KEY` = ta clé
   - `TELEGRAM_TOKEN` = le token BotFather
   - `TELEGRAM_CHAT_ID` = ton chat_id

---

## Étape 7 — Push sur GitHub

```bash
git add .
git commit -m "Initial bot setup"
git branch -M main
git push -u origin main
```

---

## Étape 8 — Active GitHub Actions

1. Sur le repo → onglet **Actions** → si message "Workflows aren't being run on this fork", clique pour activer.
2. Tu verras "Daily opportunity check" dans la liste.
3. **Pour le premier run**, lance manuellement : Actions → Daily opportunity check → **Run workflow** → Run.
4. Le workflow tourne (~2 min). Va dans le run pour voir les logs.
5. Tu devrais recevoir tes premières notifications Telegram dans la foulée.

---

## C'est en route !

Ensuite, le bot tourne tout seul tous les matins à 06h00 UTC (07h ou 08h Zurich selon la saison). Le state est commité dans le repo, donc chaque jour seul le delta déclenche une notification.

### Pour ajouter des firms

Édite `firms.yaml`, commit, push. Au prochain run, les nouvelles firms seront analysées (et toutes leurs opportunités actuelles seront notifiées comme "nouvelles").

### Pour modifier ton profil

Édite `profile.md`, commit, push. Les futures analyses utiliseront le nouveau profil.

### Pour changer l'heure du cron

Édite `.github/workflows/daily-check.yml`, ligne `- cron: '0 6 * * *'`. C'est en UTC, format `min hour * * *`. Exemples :
- `0 5 * * *` → 06h Zurich (été 07h)
- `30 5 * * 1-5` → 06h30 du lundi au vendredi seulement

### Si ça déconne

- Onglet Actions → clique sur un run échoué → vois les logs.
- Erreurs HTTP fréquentes : certaines firms (Workday, Greenhouse) chargent les jobs en JavaScript. Le scraper voit alors une page presque vide. Solution simple : retirer ces firms et créer manuellement une Google Alert pour elles.

### Pour aller plus loin

- **Sélecteurs CSS par firm** : ajouter un champ `selector` dans `firms.yaml` pour extraire précisément la zone "current openings" et ignorer le reste.
- **Mode digest** : grouper toutes les opportunités du jour dans un seul message au lieu d'un par firm.
- **Tracking des applications** : ajouter une commande Telegram `/applied JaneStreet` qui marque comme postulé et arrête les notifs pour cette firm.
- **Playwright** pour les pages JS-heavy : remplacer `requests` par un headless Chromium. Plus lourd à setup mais ouvre Workday/Greenhouse/etc.
