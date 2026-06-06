from enum import Enum


class Decision(str, Enum):
    BUY = "BUY"
    TEST = "TEST"
    WATCHLIST = "WATCHLIST"
    REJECT = "REJECT"


class Category(str, Enum):
    HOME = "home"
    BEAUTY = "beauty"
    TECH = "tech"
    FITNESS = "fitness"
    PETS = "pets"
    KIDS = "kids"
    OUTDOOR = "outdoor"
    KITCHEN = "kitchen"
    OTHER = "other"


class JobState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"
    CANCELLED = "cancelled"


# États non terminaux (le worker peut encore les reprendre).
ACTIVE_JOB_STATES = (JobState.PENDING.value, JobState.RETRYING.value)
# États terminaux.
TERMINAL_JOB_STATES = (
    JobState.SUCCESS.value,
    JobState.DEAD_LETTER.value,
    JobState.CANCELLED.value,
)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class IncidentSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class HealthStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    DOWN = "down"


class ServiceMode(str, Enum):
    RUNNING = "running"
    PAUSED = "paused"
    SAFE_MODE = "safe_mode"
