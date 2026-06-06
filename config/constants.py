MAX_PRODUCTS_PER_RUN: int = 500
DEFAULT_FORECAST_HORIZON: int = 14
HISTORY_WINDOW: int = 30

# Seuils de décision (sur 100)
SCORE_BUY: float = 75.0
SCORE_TEST: float = 60.0
SCORE_WATCHLIST: float = 45.0

# Garde-fous BUY (non négociables)
MIN_SUPPLIER_RELIABILITY_BUY: float = 0.70
MAX_RISK_BUY: float = 0.55
MAX_SATURATION_BUY: float = 0.80
MIN_NET_MARGIN_BUY: float = 0.18
MIN_VIRALITY_FOR_HYPE_FLAG: float = 0.75
MIN_DURABILITY_FOR_HYPE_OK: float = 0.55

# --- Service 24/7 ---
# Types de jobs reconnus par le scheduler / les workers.
JOB_TYPE_SCAN: str = "scan"
JOB_TYPE_EXPORT: str = "export"

# Noms des heartbeats persistés.
HEARTBEAT_SUPERVISOR: str = "supervisor"

# Commandes Telegram considérées comme sensibles (confirmation requise).
CONFIRM_TOKEN: str = "confirm"

