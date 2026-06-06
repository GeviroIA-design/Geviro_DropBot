import csv
import json
import os
from typing import List

from models.product import Product
from models.scorecard import Scorecard
from utils.logger import get_logger

log = get_logger("exporters")


def ensure_dir(path: str) -> None:
    if path:
        os.makedirs(path, exist_ok=True)


def export_csv(rows: List[dict], path: str) -> None:
    ensure_dir(os.path.dirname(path) or ".")
    try:
        if not rows:
            open(path, "w", encoding="utf-8").close()
            return
        keys: list = []
        seen = set()
        for r in rows:
            for k in r.keys():
                if k not in seen:
                    seen.add(k)
                    keys.append(k)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for r in rows:
                writer.writerow(r)
    except PermissionError:
        log.warning(
            f"{path} verrouille (ouvert dans Excel ?) -- ecriture ignoree. "
            f"Fermez le fichier puis relancez."
        )


def export_json(data, path: str) -> None:
    ensure_dir(os.path.dirname(path) or ".")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    except PermissionError:
        log.warning(
            f"{path} verrouille (ouvert ?) -- ecriture ignoree. "
            f"Fermez le fichier puis relancez."
        )


def export_report(
    products: List[Product], scorecards: List[Scorecard], out_dir: str
) -> None:
    ensure_dir(out_dir)
    sc_map = {s.product_id: s for s in scorecards}

    rows = []
    json_payload = []
    for p in products:
        s = sc_map.get(p.product_id)
        row = p.to_dict()
        if s is not None:
            row.update(
                {
                    "final_score": s.final_score,
                    "decision": s.decision,
                    "reasons": " | ".join(s.reasons),
                }
            )
        rows.append(row)
        json_payload.append(
            {
                "product": p.to_dict(),
                "scorecard": s.to_dict() if s is not None else None,
            }
        )

    export_csv(rows, os.path.join(out_dir, "report.csv"))
    export_json(json_payload, os.path.join(out_dir, "report.json"))


# Colonnes du rapport lisible (clé interne -> en-tête français).
# Ordonnées du plus utile au plus détaillé : décision et finances d'abord.
EXCEL_FR_COLUMNS = [
    ("product_id", "ID"),
    ("name", "Produit"),
    ("category", "Catégorie"),
    ("niche", "Niche"),
    ("final_score", "SCORE FINAL /100"),
    ("decision", "DÉCISION"),
    ("reasons", "Raisons de la décision"),
    ("net_margin", "Marge nette"),
    ("roi", "ROI"),
    ("net_profit", "Profit net (€)"),
    ("gross_margin", "Marge brute"),
    ("gross_profit", "Profit brut (€)"),
    ("estimated_selling_price", "Prix de vente (€)"),
    ("purchase_cost", "Coût d'achat (€)"),
    ("shipping_cost", "Coût livraison (€)"),
    ("ad_cost_estimate", "Coût pub estimé (€)"),
    ("demand_volume", "Volume de demande"),
    ("demand_growth", "Croissance demande"),
    ("short_term_momentum", "Momentum court terme"),
    ("mid_term_momentum", "Momentum moyen terme"),
    ("demand_stability", "Stabilité demande"),
    ("seasonality_score", "Saisonnalité"),
    ("virality_score", "Viralité"),
    ("durability_score", "Durabilité"),
    ("competition_level", "Niveau concurrence"),
    ("market_saturation", "Saturation marché"),
    ("average_rating", "Note moyenne avis"),
    ("review_count", "Nb avis"),
    ("shipping_delay_days", "Délai livraison (jours)"),
    ("supplier_reliability", "Fiabilité fournisseur"),
    ("estimated_return_rate", "Taux de retour estimé"),
    ("risk_score", "Score risque (0-1)"),
    ("score_demande", "Sous-score demande"),
    ("score_croissance", "Sous-score croissance"),
    ("score_momentum", "Sous-score momentum"),
    ("score_marge", "Sous-score marge"),
    ("score_roi", "Sous-score ROI"),
    ("score_concurrence", "Sous-score concurrence"),
    ("score_saturation", "Sous-score saturation"),
    ("score_fournisseur", "Sous-score fournisseur"),
    ("score_logistique", "Sous-score logistique"),
    ("score_qualite", "Sous-score qualité"),
    ("score_stabilite", "Sous-score stabilité"),
    ("score_risque", "Sous-score risque"),
    ("score_durabilite", "Sous-score durabilité"),
    ("bonus", "Bonus"),
    ("malus", "Malus"),
]


def _fr_value(v) -> str:
    """Formatte une valeur pour Excel français (décimale = virgule)."""
    if isinstance(v, bool):
        return "oui" if v else "non"
    if isinstance(v, float):
        return ("%g" % v).replace(".", ",")
    return str(v)


def export_excel_fr(
    products: List[Product], scorecards: List[Scorecard], path: str
) -> None:
    """Rapport lisible pour Excel français.

    - séparateur de colonnes ';' (et non ',')
    - décimales avec virgule
    - BOM UTF-8 pour afficher correctement les accents
    - lignes triées par score décroissant
    - toutes les colonnes (produit + sous-scores), en-têtes français
    """
    ensure_dir(os.path.dirname(path) or ".")
    sc_map = {s.product_id: s for s in scorecards}

    merged = []
    for p in products:
        s = sc_map.get(p.product_id)
        row = p.to_dict()
        if s is not None:
            sd = s.to_dict()
            sd["reasons"] = " | ".join(s.reasons)
            row.update(sd)
        merged.append(row)

    merged.sort(key=lambda r: r.get("final_score", 0.0), reverse=True)

    try:
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow([label for _, label in EXCEL_FR_COLUMNS])
            for r in merged:
                writer.writerow(
                    [_fr_value(r.get(key, "")) for key, _ in EXCEL_FR_COLUMNS]
                )
    except PermissionError:
        log.warning(
            f"{path} verrouille (ouvert dans Excel ?) -- ecriture ignoree. "
            f"Fermez le fichier puis relancez."
        )
