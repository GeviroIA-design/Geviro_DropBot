from dataclasses import asdict, dataclass, field
from typing import List


@dataclass
class Forecast:
    product_id: str
    horizon: int
    historical: List[float] = field(default_factory=list)
    forecast: List[float] = field(default_factory=list)
    mae: float = 0.0
    mape: float = 0.0
    wmape: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)
