from typing import List

from models.product import Product


def validate_product(p: Product) -> List[str]:
    errors: List[str] = []
    if not p.product_id:
        errors.append("missing product_id")
    if p.purchase_cost < 0:
        errors.append("negative purchase_cost")
    if p.estimated_selling_price <= 0:
        errors.append("non-positive selling price")
    if p.shipping_cost < 0:
        errors.append("negative shipping_cost")
    if p.ad_cost_estimate < 0:
        errors.append("negative ad_cost_estimate")
    if p.demand_volume < 0:
        errors.append("negative demand_volume")
    if not (0.0 <= p.supplier_reliability <= 1.0):
        errors.append("supplier_reliability out of [0,1]")
    if not (0.0 <= p.competition_level <= 1.0):
        errors.append("competition_level out of [0,1]")
    if not (0.0 <= p.market_saturation <= 1.0):
        errors.append("market_saturation out of [0,1]")
    if not (0.0 <= p.estimated_return_rate <= 1.0):
        errors.append("estimated_return_rate out of [0,1]")
    if not (0.0 <= p.demand_stability <= 1.0):
        errors.append("demand_stability out of [0,1]")
    if not (0.0 <= p.virality_score <= 1.0):
        errors.append("virality_score out of [0,1]")
    if not (0.0 <= p.durability_score <= 1.0):
        errors.append("durability_score out of [0,1]")
    if p.shipping_delay_days < 0:
        errors.append("negative shipping_delay_days")
    return errors
