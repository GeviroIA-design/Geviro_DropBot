import logging
import os
import sys
from typing import List

from config.settings import settings


def _ensure_log_dir(path: str) -> None:
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logger.setLevel(level)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(fmt)
    logger.addHandler(stream)

    # Fichier de log (utile pour /tail_logs et le post-mortem VPS).
    if settings.log_file:
        try:
            _ensure_log_dir(settings.log_file)
            file_handler = logging.FileHandler(
                settings.log_file, encoding="utf-8"
            )
            file_handler.setFormatter(fmt)
            logger.addHandler(file_handler)
        except OSError:
            # Pas de fichier => on reste sur stdout uniquement.
            pass

    logger.propagate = False
    return logger


def tail_log(n: int = 20) -> List[str]:
    """Retourne les n dernières lignes du fichier de log (best-effort)."""
    path = settings.log_file
    if not path or not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError:
        return []
    return [ln.rstrip("\n") for ln in lines[-max(1, n):]]
