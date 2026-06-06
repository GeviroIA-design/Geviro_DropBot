"""Compteurs, jauges et heartbeats persistés."""
import time
from typing import Dict, Optional

from runtime.service_state import Store


class MetricsStore:
    def __init__(self, store: Store, clock=time.time):
        self.store = store
        self.clock = clock

    def incr(self, key: str, amount: float = 1.0) -> None:
        self.store.execute(
            "INSERT INTO metrics(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = value + ?",
            (key, amount, amount),
        )

    def set_gauge(self, key: str, value: float) -> None:
        self.store.execute(
            "INSERT INTO metrics(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )

    def get(self, key: str, default: float = 0.0) -> float:
        row = self.store.query_one(
            "SELECT value FROM metrics WHERE key=?", (key,)
        )
        return float(row["value"]) if row else default

    def all(self) -> Dict[str, float]:
        rows = self.store.query("SELECT key, value FROM metrics ORDER BY key")
        return {r["key"]: r["value"] for r in rows}

    # --- heartbeats ---
    def set_heartbeat(self, name: str, ts: Optional[float] = None) -> None:
        self.store.execute(
            "INSERT INTO heartbeats(name, ts) VALUES(?, ?) "
            "ON CONFLICT(name) DO UPDATE SET ts = excluded.ts",
            (name, ts if ts is not None else self.clock()),
        )

    def get_heartbeat(self, name: str) -> Optional[float]:
        row = self.store.query_one(
            "SELECT ts FROM heartbeats WHERE name=?", (name,)
        )
        return float(row["ts"]) if row else None

    def all_heartbeats(self) -> Dict[str, float]:
        rows = self.store.query("SELECT name, ts FROM heartbeats")
        return {r["name"]: r["ts"] for r in rows}

    def clear_heartbeats(self) -> None:
        """Purge les heartbeats (appelé au démarrage : les composants
        re-battent immédiatement, donc pas de faux 'stale' au boot)."""
        self.store.execute("DELETE FROM heartbeats")

    def heartbeat_age(self, name: str, now: Optional[float] = None) -> Optional[float]:
        ts = self.get_heartbeat(name)
        if ts is None:
            return None
        now = now if now is not None else self.clock()
        return now - ts
