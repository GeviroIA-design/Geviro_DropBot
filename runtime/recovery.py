"""Recovery au démarrage : remet le service dans un état cohérent."""
import time
from typing import Dict

from models.enums import IncidentSeverity
from monitoring.incident_store import IncidentStore
from runtime.job_queue import JobQueue
from runtime.service_state import ServiceState


def recover_on_start(
    queue: JobQueue,
    service_state: ServiceState,
    incidents: IncidentStore,
    metrics=None,
    clock=time.time,
) -> Dict[str, object]:
    """Réenfile les jobs laissés 'running' par un crash et journalise.

    Purge aussi les heartbeats hérités du run précédent : sinon, au premier
    tick du watchdog, des heartbeats périmés déclencheraient un faux incident
    'stale' avant que les composants n'aient eu le temps de re-battre.
    """
    requeued = queue.requeue_running(clock())
    if metrics is not None:
        metrics.clear_heartbeats()
    service_state.mark_started(clock())

    summary = {
        "requeued_running_jobs": requeued,
        "resumed_safe_mode": service_state.is_safe_mode(),
        "resumed_paused": service_state.is_paused(),
    }
    incidents.record(
        IncidentSeverity.INFO.value,
        "recovery",
        f"service start: requeued={requeued}, "
        f"safe_mode={service_state.is_safe_mode()}, "
        f"paused={service_state.is_paused()}",
    )
    return summary
