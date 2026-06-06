from dataclasses import asdict, dataclass, field
from typing import List


@dataclass
class Scorecard:
    product_id: str
    score_demande: float = 0.0
    score_croissance: float = 0.0
    score_momentum: float = 0.0
    score_marge: float = 0.0
    score_roi: float = 0.0
    score_concurrence: float = 0.0
    score_saturation: float = 0.0
    score_fournisseur: float = 0.0
    score_logistique: float = 0.0
    score_qualite: float = 0.0
    score_stabilite: float = 0.0
    score_risque: float = 0.0
    score_durabilite: float = 0.0
    bonus: float = 0.0
    malus: float = 0.0
    final_score: float = 0.0
    decision: str = "WATCHLIST"
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
