from dataclasses import asdict, dataclass


@dataclass
class Weights:
    demande: float = 0.10
    croissance: float = 0.10
    momentum: float = 0.10
    marge: float = 0.12
    roi: float = 0.10
    concurrence: float = 0.07
    saturation: float = 0.06
    fournisseur: float = 0.08
    logistique: float = 0.06
    qualite: float = 0.07
    stabilite: float = 0.05
    risque: float = 0.05
    durabilite: float = 0.04

    def total(self) -> float:
        return sum(asdict(self).values())


DEFAULT_WEIGHTS = Weights()
