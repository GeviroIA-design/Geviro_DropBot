"""Calcul de l'état de santé global, indépendant et testable."""
from typing import Any, Dict, List, Optional

from models.enums import CircuitState, HealthStatus


def compute_health(
    heartbeat_age: Optional[float],
    heartbeat_max_age: float,
    breaker_states: Dict[str, str],
    dead_letter_count: int,
    open_incidents: int,
    paused: bool,
    safe_mode: bool,
    last_scan_age: Optional[float],
    scan_interval: float,
) -> Dict[str, Any]:
    """Agrège des signaux bruts en un statut OK / DEGRADED / DOWN.

    DOWN : le coeur ne bat plus (heartbeat absent ou trop vieux).
    DEGRADED : un breaker ouvert, des dead-letters, safe_mode/pause,
               ou un scan trop ancien.
    """
    checks: List[Dict[str, Any]] = []
    status = HealthStatus.OK

    # Heartbeat -> vital
    if heartbeat_age is None or heartbeat_age > heartbeat_max_age:
        checks.append(
            {
                "name": "heartbeat",
                "ok": False,
                "detail": "absent" if heartbeat_age is None
                else f"{heartbeat_age:.0f}s > {heartbeat_max_age:.0f}s",
            }
        )
        status = HealthStatus.DOWN
    else:
        checks.append(
            {"name": "heartbeat", "ok": True, "detail": f"{heartbeat_age:.0f}s"}
        )

    # Circuit breakers
    open_breakers = [
        n for n, s in breaker_states.items() if s == CircuitState.OPEN.value
    ]
    if open_breakers:
        checks.append(
            {"name": "circuit_breakers", "ok": False,
             "detail": "open: " + ", ".join(open_breakers)}
        )
        status = _worst(status, HealthStatus.DEGRADED)
    else:
        checks.append({"name": "circuit_breakers", "ok": True, "detail": "all closed"})

    # Dead-letter
    if dead_letter_count > 0:
        checks.append(
            {"name": "dead_letter", "ok": False, "detail": f"{dead_letter_count} jobs"}
        )
        status = _worst(status, HealthStatus.DEGRADED)
    else:
        checks.append({"name": "dead_letter", "ok": True, "detail": "0"})

    # Mode dégradé volontaire
    if safe_mode or paused:
        checks.append(
            {"name": "mode", "ok": False,
             "detail": "safe_mode" if safe_mode else "paused"}
        )
        status = _worst(status, HealthStatus.DEGRADED)
    else:
        checks.append({"name": "mode", "ok": True, "detail": "running"})

    # Fraîcheur du dernier scan
    if last_scan_age is not None and last_scan_age > scan_interval * 3:
        checks.append(
            {"name": "last_scan", "ok": False,
             "detail": f"{last_scan_age:.0f}s old"}
        )
        status = _worst(status, HealthStatus.DEGRADED)
    else:
        checks.append(
            {"name": "last_scan", "ok": True,
             "detail": "n/a" if last_scan_age is None else f"{last_scan_age:.0f}s"}
        )

    # Incidents ouverts (informatif, ne dégrade pas seul)
    checks.append(
        {"name": "open_incidents", "ok": open_incidents == 0,
         "detail": str(open_incidents)}
    )

    return {"status": status.value, "checks": checks}


def _worst(current: HealthStatus, candidate: HealthStatus) -> HealthStatus:
    order = {HealthStatus.OK: 0, HealthStatus.DEGRADED: 1, HealthStatus.DOWN: 2}
    return current if order[current] >= order[candidate] else candidate
