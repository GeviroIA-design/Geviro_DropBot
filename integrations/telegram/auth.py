"""Contrôle d'accès admin Telegram + rate limiting simple."""
import time
from collections import deque
from typing import Callable, Deque, Dict, Iterable


class Auth:
    def __init__(
        self,
        admin_ids: Iterable[int],
        rate_limit: int = 20,
        window: float = 60.0,
        clock: Callable[[], float] = time.time,
    ):
        self.admin_ids = set(int(a) for a in admin_ids)
        self.rate_limit = rate_limit
        self.window = window
        self.clock = clock
        self._hits: Dict[int, Deque[float]] = {}

    def set_admins(self, admin_ids: Iterable[int]) -> None:
        self.admin_ids = set(int(a) for a in admin_ids)

    def is_admin(self, user_id) -> bool:
        try:
            return int(user_id) in self.admin_ids
        except (TypeError, ValueError):
            return False

    def allow_rate(self, user_id) -> bool:
        """Fenêtre glissante : max `rate_limit` actions / `window` secondes."""
        try:
            uid = int(user_id)
        except (TypeError, ValueError):
            return False
        now = self.clock()
        hits = self._hits.setdefault(uid, deque())
        while hits and (now - hits[0]) > self.window:
            hits.popleft()
        if len(hits) >= self.rate_limit:
            return False
        hits.append(now)
        return True
