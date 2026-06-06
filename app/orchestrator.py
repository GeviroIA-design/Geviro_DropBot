import os
from collections import Counter
from typing import List

from app.pipeline import run_pipeline
from config.settings import settings
from models.scorecard import Scorecard
from utils.exporters import export_excel_fr, export_json, export_report
from utils.logger import get_logger

log = get_logger("orchestrator")


def _summary(scorecards: List[Scorecard]) -> dict:
    return dict(Counter(s.decision for s in scorecards))


def execute(n: int = None, seed: int = None, out_dir: str = None):
    out_dir = out_dir or settings.output_dir
    products, scorecards, forecasts = run_pipeline(n=n, seed=seed)

    export_report(products, scorecards, out_dir)
    export_excel_fr(
        products, scorecards, os.path.join(out_dir, "rapport_lisible.csv")
    )
    export_json(
        [f.to_dict() for f in forecasts],
        os.path.join(out_dir, "forecasts.json"),
    )

    summary = _summary(scorecards)
    log.info(f"run complete: {summary} -> {out_dir}")
    return products, scorecards, forecasts, summary
