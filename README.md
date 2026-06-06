# GEVIRO Dropshipping Bot

Moteur de product research, scoring multicritère et recommandation décisionnelle pour dropshipping.

## Installation

```bash
git clone <repo>
cd geviro-dropbot
python -m venv .venv
.venv\Scripts\activate         # Windows
# source .venv/bin/activate    # Linux/macOS
pip install -r requirements.txt
cp .env.example .env
```

Aucune dépendance externe par défaut — stdlib uniquement.

## Utilisation

### CLI
```bash
python -m app.main --n 30 --seed 42 --out outputs
```

Options :
- `--n` : nombre de produits à analyser (défaut : `N_PRODUCTS` env, fallback 30).
- `--seed` : seed RNG (défaut : 42).
- `--out` : dossier de sortie (défaut : `outputs/`).

### Sortie
- `outputs/report.csv` : un produit par ligne avec tous les champs, le `final_score`, la `decision`, les `reasons`.
- `outputs/report.json` : version JSON enrichie (produit + scorecard).
- `outputs/forecasts.json` : série historique simulée + forecast par produit + MAE/MAPE/WMAPE.

## Décisions
| Décision | Sens |
|---|---|
| `BUY` | Score ≥ 75 et aucun garde-fou violé. Lancer la campagne. |
| `TEST` | Score ≥ 60 et ≤ 1 garde-fou violé. Petite campagne test avant scale. |
| `WATCHLIST` | Score ≥ 45. Garder en observation, peut décoller. |
| `REJECT` | Score < 45 ou ratios financiers inacceptables. |

## Service 24/7 + console Telegram

En plus du mode batch ci-dessus, le bot tourne en **service continu** avec
contrôle admin par Telegram. Toujours **zéro dépendance** (sqlite3 + urllib +
threading de la stdlib).

### Lancer le service
```bash
python -m app.run_service                 # tourne en continu (VPS/systemd)
python -m app.run_service --scan-now      # enfile un scan immédiat au démarrage
python -m app.run_service --max-runtime 5 # s'arrête après 5s (smoke test)
```

Le service : exécute des jobs planifiés (scan + export), les relance avec
backoff exponentiel, ouvre un circuit breaker sur les pannes répétées,
surveille sa santé (heartbeat + watchdog), persiste son état dans SQLite,
récupère après un crash, et alerte les admins Telegram.

### Console Telegram
1. Créer un bot via @BotFather → récupérer le token.
2. Récupérer votre ID Telegram (via @userinfobot).
3. Renseigner `.env` :
   ```
   TELEGRAM_BOT_TOKEN=123456:ABC...
   TELEGRAM_ADMIN_IDS=123456789
   ```
4. Sans token, la console est simplement désactivée (no-op sûr) ; le reste
   du service fonctionne.

Commandes : `/help` les liste toutes. Accès **réservé aux IDs admin** ;
toute action est journalisée (audit). Voir `CLAUDE.md` pour la matrice.

### Déploiement VPS (systemd)
Voir `deploy/bot-service.service` et la section déploiement de `CLAUDE.md`.

## Tests
```bash
python -m unittest discover -s tests -v
```

## Architecture
Voir `CLAUDE.md` pour les conventions et invariants.
