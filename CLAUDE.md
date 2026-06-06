# CLAUDE.md — GEVIRO Dropshipping Bot

## But du projet
Bot Python de product research dropshipping. Entrée : signaux produits/marché (collectés ou simulés). Sortie : produits scorés sur 100, décision BUY/TEST/WATCHLIST/REJECT, raisons exploitables, forecast de demande.

Ce n'est PAS un oracle. C'est un moteur d'aide à la décision multicritère, fondé sur :
- product research,
- validation de tendance (momentum + stabilité),
- estimation financière (marges, ROI, retours),
- analyse concurrence/saturation,
- risque composite (fournisseur, logistique, qualité, hype),
- forecast simple backtesté.

## Architecture
Pipeline en couches strictes. Le flux est unidirectionnel :

```
collectors → enrich raw dicts
            ↓
            _to_product (validation)
            ↓
analyzers   financial_analyzer  (marges, ROI nets de retours)
            risk_analyzer        (risk_score composite)
            ↓
scorers     scoring_engine       (13 sous-scores + bonus/malus → final_score)
            decision_rules       (BUY/TEST/WATCHLIST/REJECT + garde-fous)
            ↓
analyzers   forecast_analyzer    (historique simulé + forecast naïf + MAE/MAPE/WMAPE)
            ↓
exporters   report.csv, report.json, forecasts.json
```

## Conventions
- Python 3.10+, stdlib uniquement.
- Dataclasses pour les modèles. Pas de Pydantic (overkill ici).
- Pas d'I/O dans les analyzers (pure functions sur Product).
- Random seedé partout (`config.settings.seed`) → résultats reproductibles.
- Logging via `utils.logger.get_logger(name)`.
- Normalisation centralisée dans `utils.normalization` (clamp, min_max, to_100).

## Lancer le projet
```bash
python -m app.main --n 30 --seed 42 --out outputs
```
Sortie : `outputs/report.csv`, `outputs/report.json`, `outputs/forecasts.json`.

## Lancer les tests
```bash
python -m unittest discover -s tests -v
```

## Règles à ne PAS casser

### Invariants du modèle Product
Les 23 champs d'entrée listés dans `models/product.py` sont le contrat. Les analyzers consomment ces champs, les scorers les pondèrent, les exporters les écrivent. Toute modification du schéma DOIT être propagée à :
- `collectors/*` (génération),
- `analyzers/*` (consommation),
- `scorers/scoring_engine.py` (pondération),
- `utils/exporters.py` (sérialisation),
- `tests/*` (fixtures).

### Garde-fous de décision (NON NÉGOCIABLES)
Un produit ne peut PAS être BUY si UN seul des suivants est vrai :
- `supplier_reliability < MIN_SUPPLIER_RELIABILITY_BUY` (0.70)
- `risk_score > MAX_RISK_BUY` (0.55)
- `market_saturation > MAX_SATURATION_BUY` (0.80)
- `net_margin < MIN_NET_MARGIN_BUY` (0.18)
- `virality_score > 0.75 AND durability_score < 0.55` (hype instable)

Ces seuils sont dans `config/constants.py`. Si on les ajuste, mettre à jour `tests/test_decisions.py`.

### Cohérence du scoring
- `final_score ∈ [0, 100]`. Toujours.
- La somme pondérée des sous-scores est divisée par `weights.total()`, donc les poids n'ont pas besoin de sommer à 1.
- `bonus`/`malus` s'appliquent APRÈS la base pondérée, puis clip à [0, 100].

## Comment ajouter un nouveau collector
1. Créer `collectors/my_collector.py` héritant de `BaseCollector` ou exposant `enrich(products: list[dict]) -> list[dict]`.
2. Ajouter les nouveaux champs au dataclass `Product` (`models/product.py`).
3. Mettre à jour `_to_product` dans `app/pipeline.py` pour mapper les champs.
4. Appeler le collector dans `run_pipeline` AVANT `_to_product`.
5. Ajouter un test smoke dans `tests/test_pipeline.py`.

## Comment ajouter un nouveau score
1. Ajouter le poids dans `scorers/weights.py` (dataclass `Weights`).
2. Calculer le sous-score dans `scoring_engine.compute_scorecard` à partir d'un champ Product (normalisé via `utils.normalization`).
3. Ajouter `score_xxx` au dataclass `Scorecard` (`models/scorecard.py`).
4. Pondérer dans la somme `base = ...`.
5. Ajouter un test ciblé : un produit faible sur ce critère doit avoir un score final inférieur.

## Comment brancher de vraies APIs
Les collectors simulent aujourd'hui. Pour brancher une vraie source (Shopify, AliExpress, Google Trends, etc.) :
1. Garder l'interface `enrich(products: list[dict]) -> list[dict]` ou `collect() -> list[dict]`.
2. Mettre les clés API dans `.env` (lues via `config/settings.py`).
3. Conserver les champs de sortie identiques pour ne pas casser le pipeline.
4. Cap raisonnable : `MAX_PRODUCTS_PER_RUN` dans `config/constants.py`.

## Données simulées
- `collectors/marketplace_collector.py` génère N produits avec cost/price réalistes (multiplicateur 2.2–4.5x).
- `collectors/trends_collector.py` ajoute demande/momentum/stabilité.
- `collectors/supplier_collector.py` ajoute fiabilité fournisseur.
- `collectors/competitor_collector.py` ajoute concurrence/saturation.
- `analyzers/forecast_analyzer.py` simule une série temporelle de 30 jours, forecast naïf 14 jours, backtest sur la queue.

Toute cette simulation est seedée — `seed=42` donne le même run à chaque exécution.

---

# Service 24/7 + console Telegram

## Vue d'ensemble
Le repo expose deux modes :
- **batch** : `python -m app.main` (scoring ponctuel, inchangé).
- **service** : `python -m app.run_service` (always-on, supervisé, piloté par Telegram).

Toujours **stdlib only** : `sqlite3` (état), `urllib` (Telegram long polling),
`threading` (workers + polling). Aucune dépendance ajoutée.

## Flux du service
```
run_service  -> recovery (réenfile les jobs 'running' laissés par un crash)
             -> N worker-threads : claim_next -> handler -> retry/circuit/dead_letter
             -> telegram-thread  : long polling -> auth -> dispatch -> audit
             -> supervisor loop  : scheduler.tick + heartbeat + watchdog
state.db (SQLite) : state | jobs | incidents | audit | metrics | heartbeats | circuit_breakers
```

## Couches ajoutées
- `runtime/` : service_state (Store SQLite + flags), job_queue, scheduler,
  worker, retry_policy, circuit_breaker, heartbeat, watchdog, recovery.
- `monitoring/` : metrics_store (+heartbeats), incident_store, audit_log,
  alerts, healthcheck.
- `integrations/telegram/` : bot (client urllib), auth, formatter, commands,
  handlers, notifier.
- `app/` : supervisor (coeur), telegram_admin (console), run_service (entrée).

## États des jobs
`pending -> running -> success` ou `-> retrying -> ... -> dead_letter`,
plus `failed` (terminal manuel) et `cancelled`. Constantes : `models/enums.JobState`.

## Invariants service à NE PAS casser
- **Telegram = admin only.** Tout passe par `integrations/telegram/auth.Auth`.
  Un non-admin reçoit un refus explicite + ligne d'audit. JAMAIS de commande
  qui exécute du shell ou du code arbitraire.
- **Aucun secret en clair.** Token uniquement via `TELEGRAM_BOT_TOKEN`.
  `formatter.mask_secret` pour tout affichage. Ne jamais logger le token.
- **Actions sensibles confirmées.** `safe_mode_on` et `restart_failed_jobs`
  exigent `confirm` (voir `commands.COMMANDS[...]['confirm']`).
- **Safe mode / pause** => les workers ne prennent plus de jobs, mais le
  service reste vivant et répond à Telegram (`ServiceState.is_blocked`).
- **Recovery** : tout job `running` au démarrage est réenfilé en `pending`.
- **Backoff** : un échec passe par `RetryPolicy` (exponentiel, capé) avant
  `dead_letter`. Le `CircuitBreaker` par type de job coupe après N échecs.

## Comment ajouter une commande Telegram
1. Écrire `cmd_xxx(supervisor, args, user_id) -> str` dans
   `integrations/telegram/commands.py`.
2. L'enregistrer dans `COMMANDS` (help + `confirm` si sensible).
3. Exposer la méthode correspondante sur `Supervisor` si besoin.
4. Ajouter un test dans `tests/test_telegram_commands.py`.

## Comment ajouter un job récurrent
1. Ajouter un type dans `config/constants.py` (`JOB_TYPE_xxx`).
2. Écrire `_handle_xxx(self, payload)` sur `Supervisor` et l'enregistrer
   dans `self.registry`.
3. `self.scheduler.add("xxx", interval, JOB_TYPE_xxx, ...)` dans `__init__`.
4. Ajouter un intervalle dans `config/settings.py` + `.env.example`.

## Lancer / tester le service
```bash
python -m app.run_service --scan-now --max-runtime 5   # smoke local
python -m unittest discover -s tests -v                # 64 tests
```

## Déploiement VPS (systemd)
1. `git clone` dans `/opt/geviro-dropbot`, créer `.venv`, `pip install -r requirements.txt`.
2. Copier `.env` (token + admin IDs).
3. `cp deploy/bot-service.service /etc/systemd/system/` (adapter User/paths).
4. `systemctl daemon-reload && systemctl enable --now bot-service`.
5. Logs : `journalctl -u bot-service -f`. Restart auto via `Restart=always`.
