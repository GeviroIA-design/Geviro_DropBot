"""Mise en forme compacte des réponses Telegram (en français) + masquage.

Les valeurs internes (états de job, décisions, mode...) restent en anglais
dans le code/la base ; elles sont TRADUITES ici, uniquement à l'affichage.
"""
import time
from typing import Any, Dict, List, Optional

# --- Traductions d'affichage ---
JOB_STATE_FR = {
    "pending": "en attente",
    "running": "en cours",
    "success": "réussie",
    "failed": "échouée",
    "retrying": "nouvel essai",
    "dead_letter": "abandonnée",
    "cancelled": "annulée",
}
DECISION_FR = {
    "BUY": "ACHETER",
    "TEST": "TESTER",
    "WATCHLIST": "À SURVEILLER",
    "REJECT": "REJETER",
}
HEALTH_FR = {"ok": "OK", "degraded": "DÉGRADÉ", "down": "HORS SERVICE"}
MODE_FR = {"running": "actif", "paused": "en pause", "safe_mode": "mode sécurité"}
SEVERITY_FR = {"info": "info", "warning": "avertissement", "critical": "critique"}
CHECK_FR = {
    "heartbeat": "battement de cœur",
    "circuit_breakers": "coupe-circuits",
    "dead_letter": "tâches abandonnées",
    "mode": "mode",
    "last_scan": "dernier scan",
    "open_incidents": "incidents ouverts",
}


def _t(mapping: dict, key: str) -> str:
    return mapping.get(key, key)


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
    uptime_str = _fmt_duration(uptime) if uptime is not None else "n/d"
    counts = s.get("queue_counts", {})
    counts_str = ", ".join(
        f"{_t(JOB_STATE_FR, k)}={v}" for k, v in counts.items()
    ) or "vide"
    return (
        f"ÉTAT DU SERVICE\n"
        f"- mode : {_t(MODE_FR, s.get('mode'))}\n"
        f"- en service depuis : {uptime_str}\n"
        f"- processus de travail : {s.get('workers')}\n"
        f"- file d'attente : {counts_str}\n"
        f"- dernier scan : il y a {_ago(s.get('last_scan_ts'))}\n"
        f"- dernier export : il y a {_ago(s.get('last_export_ts'))}\n"
        f"- incidents ouverts : {s.get('open_incidents')}\n"
        f"- propositions en attente : {s.get('pending_proposals', 0)}"
    )


def fmt_health(h: Dict[str, Any]) -> str:
    lines = [f"SANTÉ : {_t(HEALTH_FR, h.get('status', '?'))}"]
    for c in h.get("checks", []):
        mark = "OK" if c.get("ok") else "KO"
        lines.append(
            f"- [{mark}] {_t(CHECK_FR, c.get('name'))} : {c.get('detail')}"
        )
    return "\n".join(lines)


def fmt_metrics(m: Dict[str, float]) -> str:
    if not m:
        return "COMPTEURS\n(aucun)"
    lines = ["COMPTEURS"]
    for k in sorted(m):
        lines.append(f"- {k} : {_num(m[k])}")
    return "\n".join(lines)


def fmt_jobs(jobs: List[Dict[str, Any]]) -> str:
    if not jobs:
        return "TÂCHES\n(aucune)"
    lines = ["TÂCHES (récentes)"]
    for j in jobs:
        err = f" err={_short(j.get('last_error'))}" if j.get("last_error") else ""
        lines.append(
            f"- #{j['id']} {j['name']} [{_t(JOB_STATE_FR, j['state'])}] "
            f"essais={j.get('attempts', 0)}{err}"
        )
    return "\n".join(lines)


def fmt_queue(counts: Dict[str, int]) -> str:
    if not counts:
        return "FILE D'ATTENTE\n(vide)"
    lines = ["FILE D'ATTENTE"]
    for state in sorted(counts):
        lines.append(f"- {_t(JOB_STATE_FR, state)} : {counts[state]}")
    return "\n".join(lines)


def fmt_incidents(incidents: List[Dict[str, Any]]) -> str:
    if not incidents:
        return "INCIDENTS\n(aucun)"
    lines = ["INCIDENTS (récents)"]
    for i in incidents:
        ack = "acquitté" if i.get("acknowledged") else "OUVERT"
        lines.append(
            f"- #{i['id']} [{_t(SEVERITY_FR, i['severity'])}/{ack}] "
            f"{i['source']} : {_short(i['message'])} "
            f"(il y a {_ago(i['created_at'])})"
        )
    return "\n".join(lines)


def fmt_lastscan(scan: Optional[Dict[str, Any]]) -> str:
    if not scan:
        return "DERNIER SCAN\n(aucun scan effectué)"
    summary = scan.get("summary", {})
    summary_str = ", ".join(
        f"{_t(DECISION_FR, k)}={v}" for k, v in summary.items()
    ) or "n/d"
    return (
        f"DERNIER SCAN (il y a {_ago(scan.get('ts'))})\n"
        f"- produits analysés : {scan.get('n_products')}\n"
        f"- décisions : {summary_str}"
    )


def fmt_tops(scan: Optional[Dict[str, Any]], limit: int = 5) -> str:
    if not scan or not scan.get("tops"):
        return "MEILLEURS PRODUITS\n(aucun scan disponible)"
    lines = ["MEILLEURS PRODUITS"]
    for t in scan["tops"][:limit]:
        lines.append(
            f"- {t.get('product_id')} {t.get('name')} "
            f"score : {t.get('final_score')} -> {_t(DECISION_FR, t.get('decision'))}"
        )
    return "\n".join(lines)


def fmt_watchdog(anomalies: List[Dict[str, Any]]) -> str:
    if not anomalies:
        return "SURVEILLANCE\n- aucune anomalie"
    lines = ["SURVEILLANCE"]
    for a in anomalies:
        lines.append(f"- {a.get('detail')}")
    return "\n".join(lines)


def fmt_proposals(props: List[Dict[str, Any]]) -> str:
    if not props:
        return "PROPOSITIONS\n(aucune en attente)"
    lines = ["PROPOSITIONS DE REVENTE EN ATTENTE"]
    for p in props:
        block = (
            f"- #{p['id']} {p['name']} | prix {p['sell_price']:.2f} EUR | "
            f"marge +{p['margin_per_sale']:.2f} EUR/vente"
        )
        if p.get("product_url"):
            block += f"\n    voir : {p['product_url']}"
        block += f"\n    /approve {p['id']}   |   /reject {p['id']}"
        lines.append(block)
    return "\n".join(lines)


def fmt_results(data: Dict[str, Any]) -> str:
    rows = data.get("rows", [])
    suffix = " (simulés)" if data.get("simulated") else ""
    if not rows:
        return f"RÉSULTATS{suffix}\n(aucun produit mis en vente pour l'instant)"
    lines = [f"RÉSULTATS{suffix}"]
    for r in rows:
        days = r["hours"] / 24.0
        age = f"{days:.1f}j" if days >= 1 else f"{int(r['hours'])}h"
        lines.append(
            f"- {r['name']} [{r.get('channel')}] | {age} | "
            f"{r['views']} vues | {r['sales']} ventes | +{r['profit']:.2f} EUR"
        )
    lines.append(
        f"\nTOTAL : {data.get('total_sales', 0)} ventes | "
        f"+{data.get('total_profit', 0):.2f} EUR{suffix}"
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
            f"/vente | réf {p.get('listing_ref')}"
        )
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
