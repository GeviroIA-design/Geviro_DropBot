"""Point d'entrée du service always-on.

Lance : recovery -> workers (threads) -> console Telegram (thread) ->
boucle superviseur (scheduler + heartbeat + watchdog) jusqu'à arrêt.

Usage :
    python -m app.run_service                 # tourne en continu (VPS/systemd)
    python -m app.run_service --scan-now      # enfile un scan au démarrage
    python -m app.run_service --max-runtime 5 # s'arrête après 5s (smoke test)
"""
import argparse
import signal
import threading
import time

from app.supervisor import Supervisor
from app.telegram_admin import TelegramAdmin
from config.settings import settings
from runtime.service_state import Store
from utils.logger import get_logger

log = get_logger("run_service")


def _worker_loop(worker, stop: threading.Event, metrics, idle_sleep: float) -> None:
    while not stop.is_set():
        did = False
        # Tout le corps est protégé : un worker ne doit JAMAIS mourir
        # silencieusement (sinon son heartbeat se fige -> fausses alertes).
        try:
            did = worker.run_once()
            metrics.set_heartbeat(worker.name)
        except Exception as exc:  # noqa: BLE001
            log.warning(f"{worker.name} error: {exc}")
        if not did:
            stop.wait(idle_sleep)


def _install_signals(stop: threading.Event) -> None:
    def _handler(signum, _frame):
        log.info(f"signal {signum} recu -> arret propre")
        stop.set()

    for name in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, name, None)
        if sig is not None:
            try:
                signal.signal(sig, _handler)
            except (ValueError, OSError):
                pass


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="GEVIRO Dropbot service 24/7")
    parser.add_argument("--max-runtime", type=float, default=None,
                        help="arret automatique apres N secondes (tests)")
    parser.add_argument("--scan-now", action="store_true",
                        help="enfile un scan au demarrage")
    args = parser.parse_args(argv)

    store = Store(settings.state_db_path)
    supervisor = Supervisor(store, settings)

    summary = supervisor.recover()
    log.info(f"recovery: {summary}")
    if args.scan_now:
        supervisor.run_scan_now()
        log.info("scan initial enfile (--scan-now)")

    stop = threading.Event()
    _install_signals(stop)

    threads = []
    for worker in supervisor.workers:
        t = threading.Thread(
            target=_worker_loop,
            args=(worker, stop, supervisor.metrics, settings.tick_interval),
            name=worker.name,
            daemon=True,
        )
        t.start()
        threads.append(t)

    admin = TelegramAdmin(supervisor, settings)
    t_admin = threading.Thread(
        target=admin.run, args=(stop,), name="telegram", daemon=True
    )
    t_admin.start()
    threads.append(t_admin)

    log.info(
        f"service up: workers={len(supervisor.workers)} "
        f"telegram={'on' if admin.enabled else 'off'}"
    )

    start = time.time()
    try:
        while not stop.is_set():
            supervisor.tick()
            if args.max_runtime is not None and \
                    (time.time() - start) >= args.max_runtime:
                log.info("max-runtime atteint -> arret")
                break
            stop.wait(settings.tick_interval)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        for t in threads:
            t.join(timeout=2.0)
        store.close()
        log.info("service arrete proprement")


if __name__ == "__main__":
    main()
