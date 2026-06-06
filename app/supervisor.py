"""Superviseur : coeur du service. Possède file, scheduler, workers,
circuit breakers, watchdog, et expose l'API utilisée par Telegram.

Conçu sans threads internes : `tick()` et les workers sont pilotés par
run_service (prod) ou directement par les tests (synchrone).
"""
import time
from collections import Counter
from typing import Callable, Dict, List, Optional

from config.constants import (
    HEARTBEAT_SUPERVISOR,
    JOB_TYPE_EXPORT,
    JOB_TYPE_SCAN,
)
from config.settings import Settings, settings as default_settings
from models.enums import IncidentSeverity
from monitoring.alerts import AlertManager
from monitoring.audit_log import AuditLog
from monitoring.healthcheck import compute_health
from monitoring.incident_store import IncidentStore
from monitoring.metrics_store import MetricsStore
from runtime.circuit_breaker import CircuitBreaker
from runtime.executor import OrderExecutor
from runtime.job_queue import JobQueue
from runtime.proposal_store import ProposalStore
from runtime.recovery import recover_on_start
from runtime.retry_policy import RetryPolicy
from runtime.scheduler import Scheduler
from runtime.service_state import ServiceState, Store
from runtime.watchdog import Watchdog
from runtime.worker import Worker
from utils.logger import get_logger, tail_log

log = get_logger("supervisor")


class Supervisor:
    def __init__(
        self,
        store: Store,
        settings: Settings = default_settings,
        clock: Callable[[], float] = time.time,
    ):
        self.store = store
        self.settings = settings
        self.clock = clock

        # Détection de gel du process (veille machine / saut d'horloge).
        self._last_tick = None
        self._suppress_watchdog_until = 0.0

        # Persistance
        self.service_state = ServiceState(store)
        self.queue = JobQueue(store, clock=clock)
        self.metrics = MetricsStore(store, clock=clock)
        self.incidents = IncidentStore(store, clock=clock)
        self.audit = AuditLog(store, clock=clock)
        self.proposals = ProposalStore(store, clock=clock)

        # Politique d'échec
        self.retry_policy = RetryPolicy(
            max_attempts=settings.max_retries,
            base_delay=settings.retry_base_delay,
            factor=settings.retry_factor,
            max_delay=settings.retry_max_delay,
        )
        self.breakers: Dict[str, CircuitBreaker] = {}

        # Alertes (notifier branché plus tard par telegram_admin)
        self.alerts = AlertManager(self.incidents, notify=None, clock=clock)

        # Référence optionnelle vers l'auth Telegram (pour /reload_config)
        self.auth = None

        # Exécution des commandes approuvées, sous garde-fous.
        # place_order=None => ordre SIMULÉ (aucune dépense réelle) tant
        # qu'aucune API marketplace n'est branchée.
        self.executor = OrderExecutor(
            self.proposals, self.metrics, self.incidents, self.service_state,
            max_eur_per_order=settings.max_eur_per_order,
            max_orders_per_day=settings.max_orders_per_day,
            place_order=None,
            clock=clock,
        )
        # Hook de notification des propositions (branché par telegram_admin).
        self.notify = None

        # Scheduler récurrent
        self.scheduler = Scheduler(clock=clock)
        self.scheduler.add(
            "scan", settings.scan_interval, JOB_TYPE_SCAN,
            max_attempts=settings.max_retries, first_delay=5.0,
        )
        self.scheduler.add(
            "export", settings.export_interval, JOB_TYPE_EXPORT,
            max_attempts=settings.max_retries, first_delay=15.0,
        )

        # Watchdog
        self.watchdog = Watchdog(
            self.queue, self.metrics,
            job_timeout=settings.job_timeout,
            heartbeat_max_age=settings.heartbeat_max_age,
            clock=clock,
        )

        # Registre des handlers de jobs
        self.registry: Dict[str, Callable[[dict], object]] = {
            JOB_TYPE_SCAN: self._handle_scan,
            JOB_TYPE_EXPORT: self._handle_export,
        }

        # Workers
        self.worker_count = max(1, settings.worker_count)
        self.workers: List[Worker] = [
            Worker(
                name=f"worker-{i}",
                queue=self.queue,
                registry=self.registry,
                retry_policy=self.retry_policy,
                metrics=self.metrics,
                incidents=self.incidents,
                alerts=self.alerts,
                breaker_for=self.breaker_for,
                is_blocked=self.service_state.is_blocked,
                clock=clock,
            )
            for i in range(self.worker_count)
        ]

    # ------------------------------------------------------------------ #
    # Cycle de vie
    # ------------------------------------------------------------------ #
    def recover(self) -> dict:
        return recover_on_start(
            self.queue, self.service_state, self.incidents,
            self.metrics, self.clock,
        )

    def breaker_for(self, job_type: str) -> CircuitBreaker:
        cb = self.breakers.get(job_type)
        if cb is None:
            cb = CircuitBreaker(
                name=job_type,
                failure_threshold=self.settings.cb_failure_threshold,
                recovery_timeout=self.settings.cb_recovery_timeout,
                clock=self.clock,
            )
            self.breakers[job_type] = cb
        return cb

    def tick(self, now: Optional[float] = None) -> List[dict]:
        """Un battement de superviseur : scheduler + heartbeat + watchdog."""
        now = now if now is not None else self.clock()

        # Si l'écart depuis le dernier tick dépasse largement l'intervalle,
        # c'est que le process a été gelé (veille machine, suspension VM,
        # ou saut d'horloge). On accorde alors une période de grâce au
        # watchdog pour laisser workers et jobs se rafraîchir -> évite les
        # fausses alertes 'stale heartbeat' / 'stuck job' au réveil.
        gap_threshold = max(
            self.settings.heartbeat_max_age, 5 * self.settings.tick_interval
        )
        if self._last_tick is not None and (now - self._last_tick) > gap_threshold:
            gap = now - self._last_tick
            self._suppress_watchdog_until = now + self.settings.heartbeat_max_age
            log.warning(
                f"gel detecte ({gap:.0f}s sans tick: veille ou saut d'horloge) "
                f"-> watchdog en grace {self.settings.heartbeat_max_age:.0f}s"
            )
        self._last_tick = now

        if not self.service_state.is_blocked():
            enqueued = self.scheduler.tick(self.queue)
            if enqueued:
                log.info(f"scheduled enqueued: {enqueued}")
        self.metrics.set_heartbeat(HEARTBEAT_SUPERVISOR, now)

        anomalies = self.watchdog.check(now)
        if now < self._suppress_watchdog_until:
            # Période de grâce post-gel : on n'agit pas et on n'alerte pas.
            return []
        for a in anomalies:
            if a["type"] == "stuck_job":
                self.queue.requeue_job(a["job_id"], now)
            self.alerts.raise_alert(
                IncidentSeverity.WARNING.value, "watchdog", self._alert_message(a)
            )
        return anomalies

    @staticmethod
    def _alert_message(anomaly: dict) -> str:
        """Message d'alerte STABLE (sans le nombre de secondes qui change à
        chaque tick) -> permet l'anti-spam de l'AlertManager si un worker
        meurt réellement."""
        if anomaly["type"] == "stale_heartbeat":
            return f"heartbeat '{anomaly['component']}' perime"
        if anomaly["type"] == "stuck_job":
            return f"job #{anomaly['job_id']} ({anomaly['name']}) bloque"
        return anomaly.get("detail", "anomalie watchdog")

    # ------------------------------------------------------------------ #
    # Handlers de jobs (appellent le coeur scoring existant)
    # ------------------------------------------------------------------ #
    def _handle_scan(self, payload: dict) -> None:
        from app.pipeline import run_pipeline

        n = int(payload.get("n", self.settings.n_products))
        seed = int(payload.get("seed", self.settings.seed))
        products, scorecards, _ = run_pipeline(n=n, seed=seed)

        summary = dict(Counter(s.decision for s in scorecards))
        name_by_id = {p.product_id: p.name for p in products}
        ranked = sorted(scorecards, key=lambda s: s.final_score, reverse=True)
        tops = [
            {
                "product_id": s.product_id,
                "name": name_by_id.get(s.product_id, ""),
                "final_score": s.final_score,
                "decision": s.decision,
            }
            for s in ranked[:5]
        ]
        self.service_state.set_last_scan(
            {
                "ts": self.clock(),
                "n_products": len(products),
                "summary": summary,
                "tops": tops,
            }
        )
        self.metrics.incr("scans")
        self._generate_proposals(products, scorecards)

    def _generate_proposals(self, products, scorecards) -> None:
        """Crée une proposition à gain positif pour chaque produit 'BUY',
        dans la limite du budget par commande, et la pousse sur Telegram."""
        prod_by_id = {p.product_id: p for p in products}
        decision_by_id = {s.product_id: s for s in scorecards}
        qty_default = max(1, self.settings.proposal_quantity)
        budget = self.settings.max_eur_per_order

        for pid, sc in decision_by_id.items():
            if sc.decision != "BUY":
                continue
            p = prod_by_id.get(pid)
            if p is None or p.net_profit <= 0:
                continue
            unit_cost = round(p.purchase_cost + p.shipping_cost, 2)
            if unit_cost <= 0 or unit_cost > budget:
                continue  # même une unité dépasse le plafond
            qty = min(qty_default, int(budget // unit_cost))
            if qty < 1:
                continue
            expected_gain = round(qty * p.net_profit, 2)
            if expected_gain <= 0:
                continue
            if self.proposals.has_pending_for(pid):
                continue  # déjà proposé, pas de doublon

            order_cost = round(qty * unit_cost, 2)
            prop_id = self.proposals.create(
                product_id=pid,
                name=p.name,
                quantity=qty,
                unit_cost=unit_cost,
                unit_sell_price=p.estimated_selling_price,
                expected_unit_net=round(p.net_profit, 2),
                expected_gain=expected_gain,
                order_cost=order_cost,
                score=sc.final_score,
            )
            self._push_proposal(prop_id, p.name, qty, order_cost,
                                expected_gain, p.net_margin)

    def _push_proposal(self, prop_id, name, qty, order_cost, gain, net_margin):
        if not self.notify:
            return
        msg = (
            f"PROPOSITION #{prop_id}\n"
            f"{name}\n"
            f"Qte {qty} | cout {order_cost:.2f} EUR | marge nette "
            f"{net_margin * 100:.0f}%\n"
            f"GAIN ESTIME : +{gain:.2f} EUR\n"
            f"-> /approve {prop_id}   ou   /reject {prop_id}"
        )
        try:
            self.notify(msg)
        except Exception as exc:  # noqa: BLE001
            log.warning(f"push proposition #{prop_id} echoue: {exc}")

    def _handle_export(self, payload: dict) -> None:
        from app.orchestrator import execute

        n = int(payload.get("n", self.settings.n_products))
        seed = int(payload.get("seed", self.settings.seed))
        out_dir = payload.get("out_dir", self.settings.output_dir)
        products, _, _, summary = execute(n=n, seed=seed, out_dir=out_dir)
        self.service_state.set_last_export(
            {
                "ts": self.clock(),
                "n_products": len(products),
                "summary": summary,
                "out_dir": out_dir,
            }
        )
        self.metrics.incr("exports")

    # ------------------------------------------------------------------ #
    # API consommée par les commandes Telegram
    # ------------------------------------------------------------------ #
    def status(self) -> dict:
        started = self.service_state.started_at()
        uptime = (self.clock() - started) if started else None
        last_scan = self.service_state.get_last_scan() or {}
        last_export = self.service_state.get_last_export() or {}
        return {
            "mode": self.service_state.mode(),
            "uptime_s": uptime,
            "workers": self.worker_count,
            "queue_counts": self.queue.counts(),
            "last_scan_ts": last_scan.get("ts"),
            "last_export_ts": last_export.get("ts"),
            "open_incidents": self.incidents.open_count(),
            "pending_proposals": self.proposals.pending_count(),
        }

    def health(self) -> dict:
        hb_age = self.metrics.heartbeat_age(HEARTBEAT_SUPERVISOR, self.clock())
        breaker_states = {n: cb.state.value for n, cb in self.breakers.items()}
        counts = self.queue.counts()
        last_scan = self.service_state.get_last_scan()
        last_scan_age = None
        if last_scan and last_scan.get("ts"):
            last_scan_age = self.clock() - last_scan["ts"]
        return compute_health(
            heartbeat_age=hb_age,
            heartbeat_max_age=self.settings.heartbeat_max_age,
            breaker_states=breaker_states,
            dead_letter_count=counts.get("dead_letter", 0),
            open_incidents=self.incidents.open_count(),
            paused=self.service_state.is_paused(),
            safe_mode=self.service_state.is_safe_mode(),
            last_scan_age=last_scan_age,
            scan_interval=self.settings.scan_interval,
        )

    def metrics_snapshot(self) -> Dict[str, float]:
        return self.metrics.all()

    def list_jobs(self, limit: int = 15) -> List[dict]:
        return self.queue.list(limit=limit)

    def queue_counts(self) -> Dict[str, int]:
        return self.queue.counts()

    def list_incidents(self, limit: int = 15) -> List[dict]:
        return self.incidents.list(limit=limit)

    def last_scan(self) -> Optional[dict]:
        return self.service_state.get_last_scan()

    def watchdog_check(self) -> List[dict]:
        return self.watchdog.check(self.clock())

    def pause(self) -> None:
        self.service_state.set_paused(True)
        log.info("service paused")

    def resume(self) -> None:
        self.service_state.set_paused(False)
        log.info("service resumed")

    def safe_mode_on(self) -> None:
        self.service_state.set_safe_mode(True)
        self.incidents.record(
            IncidentSeverity.WARNING.value, "admin", "safe mode activé"
        )
        log.warning("safe mode ON")

    def safe_mode_off(self) -> None:
        self.service_state.set_safe_mode(False)
        log.info("safe mode OFF")

    def restart_failed_jobs(self) -> int:
        n = self.queue.restart_failed(self.clock())
        log.info(f"restart_failed_jobs -> {n}")
        return n

    def run_scan_now(self) -> int:
        return self.queue.enqueue(
            "manual-scan", JOB_TYPE_SCAN, max_attempts=self.settings.max_retries
        )

    def run_export_now(self) -> int:
        return self.queue.enqueue(
            "manual-export", JOB_TYPE_EXPORT,
            max_attempts=self.settings.max_retries,
        )

    def reload_config(self) -> Dict[str, object]:
        fresh = Settings()
        changed: Dict[str, object] = {}

        if fresh.scan_interval != self.settings.scan_interval:
            self.scheduler.set_interval("scan", fresh.scan_interval)
            changed["scan_interval"] = fresh.scan_interval
        if fresh.export_interval != self.settings.export_interval:
            self.scheduler.set_interval("export", fresh.export_interval)
            changed["export_interval"] = fresh.export_interval
        if fresh.max_retries != self.settings.max_retries:
            self.retry_policy.max_attempts = fresh.max_retries
            changed["max_retries"] = fresh.max_retries
        if fresh.cb_failure_threshold != self.settings.cb_failure_threshold:
            for cb in self.breakers.values():
                cb.failure_threshold = fresh.cb_failure_threshold
            changed["cb_failure_threshold"] = fresh.cb_failure_threshold
        if self.auth is not None and set(fresh.telegram_admin_ids) != set(
            self.settings.telegram_admin_ids
        ):
            self.auth.set_admins(fresh.telegram_admin_ids)
            changed["telegram_admin_ids"] = len(fresh.telegram_admin_ids)

        self.settings = fresh
        return changed

    def tail_logs(self, n: int = 20) -> List[str]:
        return tail_log(n)

    def ack_incident(self, incident_id: int, admin_id) -> bool:
        return self.incidents.ack(incident_id, admin_id)

    # --- propositions d'achat ---
    def list_proposals(self, limit: int = 15) -> List[dict]:
        from runtime.proposal_store import PENDING
        return self.proposals.list(status=PENDING, limit=limit)

    def approve_proposal(self, proposal_id: int, admin_id):
        return self.executor.approve(proposal_id, admin_id)

    def reject_proposal(self, proposal_id: int, admin_id):
        return self.executor.reject(proposal_id, admin_id)
