from models.product import Product


def analyze(p: Product) -> Product:
    """Calcule marges, ROI, en intégrant le coût attendu des retours.

    gross_profit = price - (purchase + shipping)
    net_profit   = price - (purchase + shipping + ad) - expected_return_loss
    roi          = net_profit / (purchase + ad)
    """
    revenue = p.estimated_selling_price
    cogs = p.purchase_cost + p.shipping_cost

    p.gross_profit = round(revenue - cogs, 2)
    p.gross_margin = round(p.gross_profit / revenue, 4) if revenue > 0 else 0.0

    total_cost = cogs + p.ad_cost_estimate
    raw_net = revenue - total_cost
    expected_return_loss = p.estimated_return_rate * cogs
    p.net_profit = round(raw_net - expected_return_loss, 2)
    p.net_margin = round(p.net_profit / revenue, 4) if revenue > 0 else 0.0

    invested = p.purchase_cost + p.ad_cost_estimate
    p.roi = round(p.net_profit / invested, 4) if invested > 0 else 0.0

    return p
