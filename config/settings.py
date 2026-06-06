import os
from dataclasses import dataclass, field
from typing import List


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        return default


def _env_bool(key: str, default: bool) -> bool:
    return os.getenv(key, str(default)).lower() in ("1", "true", "yes")


def _env_list_int(key: str, default: List[int]) -> List[int]:
    raw = os.getenv(key, "")
    if not raw.strip():
        return list(default)
    out: List[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(int(part))
        except ValueError:
            continue
    return out


@dataclass
class Settings:
    # --- coeur scoring (existant) ---
    seed: int = _env_int("BOT_SEED", 42)
    n_products: int = _env_int("N_PRODUCTS", 30)
    forecast_horizon: int = _env_int("FORECAST_HORIZON", 14)
    output_dir: str = os.getenv("OUTPUT_DIR", "outputs")
    sample_csv: str = os.getenv("SAMPLE_CSV", "data/sample_products.csv")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    use_sample: bool = _env_bool("USE_SAMPLE", False)

    # --- service 24/7 ---
    state_db_path: str = os.getenv("STATE_DB_PATH", "data/state.db")
    log_file: str = os.getenv("LOG_FILE", "logs/service.log")
    worker_count: int = _env_int("WORKER_COUNT", 2)
    tick_interval: float = _env_float("TICK_INTERVAL", 1.0)
    scan_interval: float = _env_float("SCAN_INTERVAL", 1800.0)
    export_interval: float = _env_float("EXPORT_INTERVAL", 3600.0)
    heartbeat_interval: float = _env_float("HEARTBEAT_INTERVAL", 15.0)
    heartbeat_max_age: float = _env_float("HEARTBEAT_MAX_AGE", 90.0)
    watchdog_interval: float = _env_float("WATCHDOG_INTERVAL", 30.0)
    job_timeout: float = _env_float("JOB_TIMEOUT", 300.0)

    # --- retry / circuit breaker ---
    max_retries: int = _env_int("MAX_RETRIES", 4)
    retry_base_delay: float = _env_float("RETRY_BASE_DELAY", 2.0)
    retry_factor: float = _env_float("RETRY_FACTOR", 2.0)
    retry_max_delay: float = _env_float("RETRY_MAX_DELAY", 300.0)
    cb_failure_threshold: int = _env_int("CB_FAILURE_THRESHOLD", 5)
    cb_recovery_timeout: float = _env_float("CB_RECOVERY_TIMEOUT", 60.0)

    # --- telegram admin ---
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_admin_ids: List[int] = field(
        default_factory=lambda: _env_list_int("TELEGRAM_ADMIN_IDS", [])
    )
    telegram_poll_timeout: int = _env_int("TELEGRAM_POLL_TIMEOUT", 30)
    telegram_rate_limit: int = _env_int("TELEGRAM_RATE_LIMIT", 20)
    tail_log_lines: int = _env_int("TAIL_LOG_LINES", 20)


settings = Settings()
