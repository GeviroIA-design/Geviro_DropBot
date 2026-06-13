"""Définition et routage des commandes admin Telegram.

Chaque handler a la signature (supervisor, args: list[str], user_id) -> str.
Aucune commande n'exécute de shell ni de code arbitraire : elles ne font
qu'appeler des méthodes typées du superviseur.
"""
from typing import Callable, Dict, List

from config.constants import CONFIRM_TOKEN
from config.settings import settings
from integrations.telegram import formatter as fmt


# Menu premium : SOURCE UNIQUE pour /help, /menu, setMyCommands et BotFather.
MENU_GROUPS = [
    ("Suivi", [
        ("status", "État du service"),
        ("health", "Diagnostic santé"),
        ("tops", "Meilleurs produits du dernier scan"),
        ("listings", "Produits mis en vente"),
        ("results", "Résultats des produits mis en vente"),
    ]),
    ("Revente", [
        ("scan", "Lancer une analyse maintenant"),
        ("proposals", "Propositions de revente en attente"),
        ("approve", "Valider et mettre en vente (id)"),
        ("reject", "Refuser une proposition (id)"),
    ]),
    ("Contrôle", [
        ("pause", "Mettre les analyses en pause"),
        ("resume", "Reprendre les analyses"),
        ("config", "Recharger la configuration"),
        ("logs", "Derniers journaux"),
    ]),
]
# Commandes avancées : fonctionnelles, mais hors menu principal.
ADVANCED = [
    "metrics", "jobs", "queue", "incidents", "watchdog",
    "safe_mode_on", "safe_mode_off", "restart_failed_jobs", "ack_incident",
]


def telegram_command_menu():
    """Liste pour setMyCommands : [{command, description}, ...] (+ /help)."""
    items = [{"command": "help", "description": "Aide et menu des commandes"}]
    for _group, cmds in MENU_GROUPS:
        for name, desc in cmds:
            items.append({"command": name, "description": desc})
    return items


def botfather_commands_text() -> str:
    """Bloc à coller dans BotFather /setcommands (format 'cmd - desc')."""
    lines = ["help - Aide et menu des commandes"]
    for _group, cmds in MENU_GROUPS:
        for name, desc in cmds:
            lines.append(f"{name} - {desc}")
    return "\n".join(lines)


def cmd_start(sup, args, user_id) -> str:
    return (
        "👋 GEVIRO DropBot — console d'administration.\n"
        "Vous êtes authentifié comme administrateur.\n\n"
        "Tapez /help pour le menu, ou /status pour voir l'état du bot."
    )


def cmd_help(sup, args, user_id) -> str:
    lines = ["GEVIRO DropBot — commandes"]
    for group, cmds in MENU_GROUPS:
        lines.append(f"\n— {group} —")
        for name, desc in cmds:
            lines.append(f"/{name} : {desc}")
    lines.append("\nAvancé : " + " ".join(f"/{c}" for c in ADVANCED))
    return "\n".join(lines)


def cmd_menu(sup, args, user_id) -> str:
    return cmd_help(sup, args, user_id)


def cmd_ping(sup, args, user_id) -> str:
    return "pong (le bot est en ligne)"


def cmd_status(sup, args, user_id) -> str:
    return fmt.fmt_status(sup.status())


def cmd_health(sup, args, user_id) -> str:
    return fmt.fmt_health(sup.health())


def cmd_metrics(sup, args, user_id) -> str:
    return fmt.fmt_metrics(sup.metrics_snapshot())


def cmd_jobs(sup, args, user_id) -> str:
    limit = _int_arg(args, 0, 15)
    return fmt.fmt_jobs(sup.list_jobs(limit))


def cmd_queue(sup, args, user_id) -> str:
    return fmt.fmt_queue(sup.queue_counts())


def cmd_incidents(sup, args, user_id) -> str:
    limit = _int_arg(args, 0, 15)
    return fmt.fmt_incidents(sup.list_incidents(limit))


def cmd_lastscan(sup, args, user_id) -> str:
    return fmt.fmt_lastscan(sup.last_scan())


def cmd_tops(sup, args, user_id) -> str:
    return fmt.fmt_tops(sup.last_scan())


def cmd_watchdog(sup, args, user_id) -> str:
    return fmt.fmt_watchdog(sup.watchdog_check())


def cmd_pause(sup, args, user_id) -> str:
    sup.pause()
    return "Service EN PAUSE. Les processus ne prennent plus de tâches."


def cmd_resume(sup, args, user_id) -> str:
    sup.resume()
    return "Service REPRIS. Mode actif."


def cmd_safe_mode_on(sup, args, user_id) -> str:
    sup.safe_mode_on()
    return "MODE SÉCURITÉ activé. Exécution suspendue, le service reste vivant."


def cmd_safe_mode_off(sup, args, user_id) -> str:
    sup.safe_mode_off()
    return "MODE SÉCURITÉ désactivé. Reprise normale."


def cmd_restart_failed_jobs(sup, args, user_id) -> str:
    n = sup.restart_failed_jobs()
    return f"{n} tâche(s) échouée(s)/abandonnée(s) remise(s) en file."


def cmd_run_scan_now(sup, args, user_id) -> str:
    job_id = sup.run_scan_now()
    return f"Analyse lancée (tâche #{job_id})."


def cmd_run_export_now(sup, args, user_id) -> str:
    job_id = sup.run_export_now()
    return f"Export lancé (tâche #{job_id})."


def cmd_reload_config(sup, args, user_id) -> str:
    changed = sup.reload_config()
    body = ", ".join(f"{k}={v}" for k, v in changed.items()) or "aucun changement"
    return f"Configuration rechargée. {body}"


def cmd_tail_logs(sup, args, user_id) -> str:
    n = _int_arg(args, 0, settings.tail_log_lines)
    lines = sup.tail_logs(n)
    if not lines:
        return "JOURNAUX\n(vide)"
    return "JOURNAUX (dernières lignes)\n" + "\n".join(lines)


def cmd_ack_incident(sup, args, user_id) -> str:
    if not args:
        return "Utilisation : /ack_incident <id>"
    try:
        incident_id = int(args[0])
    except ValueError:
        return "id invalide. Utilisation : /ack_incident <id>"
    ok = sup.ack_incident(incident_id, user_id)
    return f"Incident #{incident_id} acquitté." if ok else \
        f"Incident #{incident_id} introuvable ou déjà acquitté."


def cmd_proposals(sup, args, user_id) -> str:
    return fmt.fmt_proposals(sup.list_proposals(_int_arg(args, 0, 15)))


def cmd_listings(sup, args, user_id) -> str:
    return fmt.fmt_listings(sup.list_listings(_int_arg(args, 0, 15)))


def cmd_results(sup, args, user_id) -> str:
    return fmt.fmt_results(sup.results_summary(_int_arg(args, 0, 20)))


def cmd_approve(sup, args, user_id) -> str:
    if not args:
        return "Utilisation : /approve <id>"
    try:
        pid = int(args[0])
    except ValueError:
        return "id invalide. Utilisation : /approve <id>"
    _ok, msg = sup.approve_proposal(pid, user_id)
    return msg


def cmd_reject(sup, args, user_id) -> str:
    if not args:
        return "Utilisation : /reject <id>"
    try:
        pid = int(args[0])
    except ValueError:
        return "id invalide. Utilisation : /reject <id>"
    _ok, msg = sup.reject_proposal(pid, user_id)
    return msg


def _int_arg(args: List[str], idx: int, default: int) -> int:
    if len(args) > idx:
        try:
            return max(1, int(args[idx]))
        except ValueError:
            return default
    return default


# name -> {func, help, confirm}
COMMANDS: Dict[str, Dict] = {
    "start": {"func": cmd_start, "help": "message d'accueil", "confirm": False},
    "help": {"func": cmd_help, "help": "liste des commandes", "confirm": False},
    "ping": {"func": cmd_ping, "help": "test de vie (pong)", "confirm": False},
    "status": {"func": cmd_status, "help": "état du service", "confirm": False},
    "health": {"func": cmd_health, "help": "diagnostic santé", "confirm": False},
    "metrics": {"func": cmd_metrics, "help": "compteurs", "confirm": False},
    "jobs": {"func": cmd_jobs, "help": "dernières tâches [n]", "confirm": False},
    "queue": {"func": cmd_queue, "help": "états de la file d'attente", "confirm": False},
    "incidents": {"func": cmd_incidents, "help": "incidents récents [n]", "confirm": False},
    "lastscan": {"func": cmd_lastscan, "help": "résumé du dernier scan", "confirm": False},
    "tops": {"func": cmd_tops, "help": "meilleurs produits du dernier scan", "confirm": False},
    "proposals": {"func": cmd_proposals, "help": "propositions de revente en attente [n]", "confirm": False},
    "approve": {"func": cmd_approve, "help": "valide et met en vente une proposition <id>", "confirm": False},
    "reject": {"func": cmd_reject, "help": "refuse une proposition <id>", "confirm": False},
    "listings": {"func": cmd_listings, "help": "produits actuellement mis en vente [n]", "confirm": False},
    "results": {"func": cmd_results, "help": "résultats (vues/ventes/profit) des produits en vente", "confirm": False},
    "watchdog": {"func": cmd_watchdog, "help": "anomalies de surveillance détectées", "confirm": False},
    "pause": {"func": cmd_pause, "help": "met les processus de travail en pause", "confirm": False},
    "resume": {"func": cmd_resume, "help": "reprend l'exécution", "confirm": False},
    "safe_mode_on": {"func": cmd_safe_mode_on, "help": "active le mode sécurité", "confirm": True},
    "safe_mode_off": {"func": cmd_safe_mode_off, "help": "désactive le mode sécurité", "confirm": False},
    "restart_failed_jobs": {"func": cmd_restart_failed_jobs, "help": "relance les tâches échouées", "confirm": True},
    "run_scan_now": {"func": cmd_run_scan_now, "help": "lance une analyse immédiate", "confirm": False},
    "run_export_now": {"func": cmd_run_export_now, "help": "lance un export immédiat", "confirm": False},
    "reload_config": {"func": cmd_reload_config, "help": "recharge la configuration (.env)", "confirm": False},
    "tail_logs": {"func": cmd_tail_logs, "help": "dernières lignes de journal [n]", "confirm": False},
    "ack_incident": {"func": cmd_ack_incident, "help": "acquitte un incident <id>", "confirm": False},
    # Alias conviviaux (noms du menu) + menu.
    "scan": {"func": cmd_run_scan_now, "help": "lance une analyse immédiate", "confirm": False},
    "logs": {"func": cmd_tail_logs, "help": "derniers journaux [n]", "confirm": False},
    "config": {"func": cmd_reload_config, "help": "recharge la configuration", "confirm": False},
    "menu": {"func": cmd_menu, "help": "menu des commandes", "confirm": False},
}


class CommandRouter:
    def __init__(self, supervisor):
        self.supervisor = supervisor

    def dispatch(self, command: str, args: List[str], user_id) -> str:
        spec = COMMANDS.get(command)
        if spec is None:
            return f"Commande inconnue: /{command}. Tapez /help."
        if spec["confirm"] and CONFIRM_TOKEN not in args:
            return (
                f"Action sensible. Confirmez avec : /{command} {CONFIRM_TOKEN}"
            )
        func: Callable = spec["func"]
        try:
            return func(self.supervisor, args, user_id)
        except Exception as exc:  # noqa: BLE001
            return f"erreur lors de /{command}: {type(exc).__name__}: {exc}"
