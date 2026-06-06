"""Mise en forme compacte des réponses Telegram + masquage de secrets."""
import time
from typing import Any, Dict, List, Optional


def mask_secret(value: str) -> str:
    if not value:
        return "(non configuré)"
    if len(value) <= 6:
        return "***"
    return "***" + value[-4:]


def _ago(ts: Optional[float], now: Optional[float] = None) -> str:
    if ts is None:
        return "jamais"
    now = now if now is not None else time.time()
    delta = max(0, int(now - ts))
    if delta < 60:
        return f"{delta}s"
    if delta < 3600:
        return f"{delta // 60}min"
    if delta < 86400:
        return f"{delta // 3600}h"
    return f"{delta // 86400}j"


def fmt_status(s: Dict[str, Any]) -> str:
    uptime = s.get("uptime_s")
    uptime_str = _fmt_duration(uptime) if uptime is not None else "n/a"
    counts = s.get("queue_counts", {})
    counts_str = ", ".join(f"{k}={v}" for k, v in counts.items()) or "vide"
    return (
        f"STATUS\n"
        f"- mode: {s.get('mode')}\n"
        f"- uptime: {uptime_str}\n"
        f"- workers: {s.get('workers')}\n"
        f"- file: {counts_str}\n"
        f"- dernier scan: il y a {_ago(s.get('last_scan_ts'))}\n"
        f"- dernier export: il y a {_ago(s.get('last_export_ts'))}\n"
        f"- incidents ouverts: {s.get('open_incidents')}\n"
        f"- propositions en attente: {s.get('pending_proposals', 0)}"
    )


def fmt_proposals(props: List[Dict[str, Any]]) -> str:
    if not props:
        return "PROPOSITIONS\n(aucune en attente)"
    lines = ["PROPOSITIONS DE REVENTE EN ATTENTE"]
    for p in props:
        lines.append(
            f"- #{p['id']} {p['name']} | prix {p['sell_price']:.2f} EUR | "
            f"marge +{p['margin_per_sale']:.2f} EUR/vente"
            f"\n    /approve {p['id']}   |   /reject {p['id']}"
        )
    return "\n".join(lines)


def fmt_listings(listings: List[Dict[str, Any]]) -> str:
    if not listings:
        return "MISES EN VENTE\n(aucune)"
    lines = ["MISES EN VENTE"]
    for p in listings:
        lines.append(
            f"- #{p['id']} {p['name']} [{p.get('channel')}] | "
            f"prix {p['sell_price']:.2f} EUR | marge +{p['margin_per_sale']:.2f}"
            f"/vente | ref {p.get('listing_ref')}"
        )
    return "\n".join(lines)


def fmt_health(h: Dict[str, Any]) -> str:
    lines = [f"HEALTH: {h.get('status', '?').upper()}"]
    for c in h.get("checks", []):
        mark = "OK " if c.get("ok") else "KO "
        lines.append(f"- [{mark}] {c.get('name')}: {c.get('detail')}")
    return "\n".join(lines)


def fmt_metrics(m: Dict[str, float]) -> str:
    if not m:
        return "METRICS\n(aucune métrique)"
    lines = ["METRICS"]
    for k in sorted(m):
        lines.append(f"- {k}: {_num(m[k])}")
    return "\n".join(lines)


def fmt_jobs(jobs: List[Dict[str, Any]]) -> str:
    if not jobs:
        return "JOBS\n(aucun job)"
    lines = ["JOBS (récents)"]
    for j in jobs:
        err = f" err={_short(j.get('last_error'))}" if j.get("last_error") else ""
        lines.append(
            f"- #{j['id']} {j['name']} [{j['state']}] "
            f"att={j.get('attempts', 0)}{err}"
        )
    return "\n".join(lines)


def fmt_queue(counts: Dict[str, int]) -> str:
    if not counts:
        return "QUEUE\n(vide)"
    lines = ["QUEUE"]
    for state in sorted(counts):
        lines.append(f"- {state}: {counts[state]}")
    return "\n".join(lines)


def fmt_incidents(incidents: List[Dict[str, Any]]) -> str:
    if not incidents:
        return "INCIDENTS\n(aucun)"
    lines = ["INCIDENTS (récents)"]
    for i in incidents:
        ack = "ack" if i.get("acknowledged") else "OPEN"
        lines.append(
            f"- #{i['id']} [{i['severity']}/{ack}] {i['source']}: "
            f"{_short(i['message'])} (il y a {_ago(i['created_at'])})"
        )
    return "\n".join(lines)


def fmt_lastscan(scan: Optional[Dict[str, Any]]) -> str:
    if not scan:
        return "LAST SCAN\n(aucun scan effectué)"
    summary = scan.get("summary", {})
    summary_str = ", ".join(f"{k}={v}" for k, v in summary.items()) or "n/a"
    return (
        f"LAST SCAN (il y a {_ago(scan.get('ts'))})\n"
        f"- produits: {scan.get('n_products')}\n"
        f"- décisions: {summary_str}"
    )


def fmt_tops(scan: Optional[Dict[str, Any]], limit: int = 5) -> str:
    if not scan or not scan.get("tops"):
        return "TOPS\n(aucun scan disponible)"
    lines = ["TOPS"]
    for t in scan["tops"][:limit]:
        lines.append(
            f"- {t.get('product_id')} {t.get('name')} "
            f"score={t.get('final_score')} -> {t.get('decision')}"
        )
    return "\n".join(lines)


def fmt_watchdog(anomalies: List[Dict[str, Any]]) -> str:
    if not anomalies:
        return "WATCHDOG\n- aucune anomalie"
    lines = ["WATCHDOG"]
    for a in anomalies:
        lines.append(f"- [{a.get('type')}] {a.get('detail')}")
    return "\n".join(lines)


def _fmt_duration(seconds: float) -> str:
    seconds = int(seconds)
    d, rem = divmod(seconds, 86400)
    h, rem = divmod(rem, 3600)
    m, _ = divmod(rem, 60)
    parts = []
    if d:
        parts.append(f"{d}j")
    if h:
        parts.append(f"{h}h")
    parts.append(f"{m}min")
    return " ".join(parts)


def _num(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else f"{v:.2f}"


def _short(text: Any, n: int = 60) -> str:
    text = str(text or "")
    return text if len(text) <= n else text[: n - 1] + "…"
