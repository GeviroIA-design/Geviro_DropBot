from dataclasses import asdict, dataclass


@dataclass
class Product:
    # Identification
    product_id: str
    name: str
    category: str
    niche: str

    # Économie
    purchase_cost: float
    estimated_selling_price: float
    shipping_cost: float
    ad_cost_estimate: float

    # Signaux de demande / momentum
    demand_volume: int
    demand_growth: float
    short_term_momentum: float
    mid_term_momentum: float

    # Marché
    competition_level: float
    market_saturation: float

    # Qualité perçue
    average_rating: float
    review_count: int

    # Opérations
    shipping_delay_days: int
    supplier_reliability: float
    estimated_return_rate: float

    # Caractéristiques produit
    seasonality_score: float
    demand_stability: float
    virality_score: float
    durability_score: float

    # Calculés par les analyzers
    gross_profit: float = 0.0
    net_profit: float = 0.0
    gross_margin: float = 0.0
    net_margin: float = 0.0
    roi: float = 0.0
    risk_score: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)
