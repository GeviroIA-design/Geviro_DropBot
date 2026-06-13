"""Persistance centrale du service (SQLite, stdlib).

Un seul fichier SQLite partagé par tous les composants (scheduler, workers,
telegram). Accès sérialisé par un RLock -> sûr entre threads pour la charge
faible d'un service d'administration.
"""
import json
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS state (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS jobs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    type         TEXT NOT NULL,
    state        TEXT NOT NULL,
    payload      TEXT,
    attempts     INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 1,
    last_error   TEXT,
    created_at   REAL NOT NULL,
    updated_at   REAL NOT NULL,
    scheduled_at REAL NOT NULL DEFAULT 0,
    started_at   REAL,
    finished_at  REAL
);
CREATE INDEX IF NOT EXISTS idx_jobs_state ON jobs(state, scheduled_at);
CREATE TABLE IF NOT EXISTS incidents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    severity        TEXT NOT NULL,
    source          TEXT NOT NULL,
    message         TEXT NOT NULL,
    created_at      REAL NOT NULL,
    acknowledged    INTEGER NOT NULL DEFAULT 0,
    acknowledged_by TEXT,
    acknowledged_at REAL
);
CREATE TABLE IF NOT EXISTS audit (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ts        REAL NOT NULL,
    admin_id  TEXT NOT NULL,
    command   TEXT NOT NULL,
    args      TEXT,
    allowed   INTEGER NOT NULL,
    result    TEXT
);
CREATE TABLE IF NOT EXISTS metrics (
    key   TEXT PRIMARY KEY,
    value REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS heartbeats (
    name TEXT PRIMARY KEY,
    ts   REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS circuit_breakers (
    name       TEXT PRIMARY KEY,
    state      TEXT NOT NULL,
    failures   INTEGER NOT NULL DEFAULT 0,
    opened_at  REAL,
    updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS proposals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id      TEXT NOT NULL,
    name            TEXT NOT NULL,
    supplier_cost   REAL NOT NULL,
    sell_price      REAL NOT NULL,
    platform_fee    REAL NOT NULL,
    margin_per_sale REAL NOT NULL,
    score           REAL NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    channel         TEXT,
    listing_ref     TEXT,
    product_url     TEXT,
    created_at      REAL NOT NULL,
    decided_at      REAL,
    decided_by      TEXT,
    note            TEXT
);
CREATE INDEX IF NOT EXISTS idx_proposals_status ON proposals(status, id);
"""


class Store:
    """Connexion SQLite thread-safe (un connecteur, un verrou)."""

    def __init__(self, path: str):
        self.path = path
        if path != ":memory:":
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._migrate()
            self._conn.commit()

    def _migrate(self) -> None:
        """Migrations légères : ajoute les colonnes manquantes sur une base
        existante (idempotent). Indispensable pour mettre à jour le VPS sans
        recréer la base."""
        self._add_column("proposals", "product_url", "TEXT")

    def _add_column(self, table: str, col: str, decl: str) -> None:
        cols = [
            r["name"] for r in self._conn.execute(f"PRAGMA table_info({table})")
        ]
        if col not in cols:
            self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")

    @contextmanager
    def connection(self):
        """Transaction atomique : tient le verrou et commit en sortie."""
        with self._lock:
            try:
                yield self._conn
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

    def execute(self, sql: str, params: tuple = ()) -> int:
        with self._lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur.lastrowid

    def query(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        with self._lock:
            cur = self._conn.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]

    def query_one(self, sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    # --- clé/valeur JSON ---
    def set_state(self, key: str, value: Any) -> None:
        self.execute(
            "INSERT INTO state(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, json.dumps(value)),
        )

    def get_state(self, key: str, default: Any = None) -> Any:
        row = self.query_one("SELECT value FROM state WHERE key=?", (key,))
        if not row:
            return default
        try:
            return json.loads(row["value"])
        except (ValueError, TypeError):
            return default

    def close(self) -> None:
        with self._lock:
            self._conn.close()


class ServiceState:
    """Drapeaux et jalons de haut niveau du service."""

    PAUSED = "paused"
    SAFE_MODE = "safe_mode"
    STARTED_AT = "started_at"
    LAST_SCAN = "last_scan"
    LAST_EXPORT = "last_export"

    def __init__(self, store: Store):
        self.store = store

    def mark_started(self, ts: Optional[float] = None) -> None:
        self.store.set_state(self.STARTED_AT, ts if ts is not None else time.time())

    def started_at(self) -> Optional[float]:
        return self.store.get_state(self.STARTED_AT)

    def is_paused(self) -> bool:
        return bool(self.store.get_state(self.PAUSED, False))

    def set_paused(self, value: bool) -> None:
        self.store.set_state(self.PAUSED, bool(value))

    def is_safe_mode(self) -> bool:
        return bool(self.store.get_state(self.SAFE_MODE, False))

    def set_safe_mode(self, value: bool) -> None:
        self.store.set_state(self.SAFE_MODE, bool(value))

    def mode(self) -> str:
        if self.is_safe_mode():
            return "safe_mode"
        if self.is_paused():
            return "paused"
        return "running"

    def is_blocked(self) -> bool:
        """True si les workers ne doivent PAS traiter de jobs."""
        return self.is_paused() or self.is_safe_mode()

    def set_last_scan(self, payload: dict) -> None:
        self.store.set_state(self.LAST_SCAN, payload)

    def get_last_scan(self) -> Optional[dict]:
        return self.store.get_state(self.LAST_SCAN)

    def set_last_export(self, payload: dict) -> None:
        self.store.set_state(self.LAST_EXPORT, payload)

    def get_last_export(self) -> Optional[dict]:
        return self.store.get_state(self.LAST_EXPORT)
