"""Évaluation indépendante sur cas datés validés par l'équipe métier/Data.

Une étiquette positive signifie : émergence dans les N dernières observations
à la date de décision. Les alertes sont calculées sans voir le futur.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import pandas as pd

from sillage.pipeline import DetectionConfig, SERIES_KEY, detect, load_and_clean

REF_COLS = ["case_id", *SERIES_KEY, "as_of_date", "reference_label", "rationale", "source_url"]


def evaluate(cleaned: pd.DataFrame, references: pd.DataFrame, cfg: DetectionConfig, lookback: int = 4) -> dict:
    missing = set(REF_COLS) - set(references.columns)
    if missing:
        raise ValueError(f"Colonnes manquantes dans références : {sorted(missing)}")
    if references["case_id"].duplicated().any():
        raise ValueError("case_id dupliqué")
    if not references["reference_label"].astype(str).isin({"0", "1"}).all():
        raise ValueError("Les labels de référence doivent être 0 ou 1")
    if not references["as_of_date"].astype(str).str.fullmatch(r"\d{4}-\d{2}-\d{2}").all():
        raise ValueError("as_of_date doit être au format YYYY-MM-DD")
    output = []
    for _, r in references.iterrows():
        mask = pd.Series(True, index=cleaned.index)
        for col in SERIES_KEY:
            mask &= cleaned[col].astype(str).eq(str(r[col]))
        mask &= cleaned["date"].le(str(r["as_of_date"]))
        subset = cleaned.loc[mask].copy().sort_values("date")
        if subset.empty:
            raise ValueError(f"Cas sans données correspondantes : {r['case_id']}")
        # Diagnostic calculé uniquement sur l'historique disponible à as_of_date.
        _, signals, summary = detect(subset, cfg)
        if summary.iloc[0]["status"] != "ok":
            raise ValueError(f"Cas non évaluable (série insuffisante/irrégulière) : {r['case_id']}")
        recent_dates = set(subset["date"].tail(lookback).tolist())
        predicted = int(not signals.empty and signals["date"].isin(recent_dates).any())
        output.append({"case_id": r["case_id"], "label": int(r["reference_label"]),
                       "predicted": predicted, "as_of_date": r["as_of_date"]})
    tp = sum(x["predicted"] == x["label"] == 1 for x in output)
    tn = sum(x["predicted"] == x["label"] == 0 for x in output)
    fp = sum(x["predicted"] == 1 and x["label"] == 0 for x in output)
    fn = sum(x["predicted"] == 0 and x["label"] == 1 for x in output)
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2*precision*recall/(precision+recall) if precision is not None and recall is not None and precision+recall else None
    return {"n_cases": len(output), "reference_label_definition": f"emergence in last {lookback} observations as_of_date",
            "confusion": {"TP": tp, "TN": tn, "FP": fp, "FN": fn},
            "precision": precision, "recall": recall, "f1": f1,
            "accuracy": (tp+tn)/len(output) if output else None,
            "warnings": (["Moins de 30 cas : protocole demandé non complet"] if len(output) < 30 else []) +
                        (["Une seule classe présente : métriques peu informatives"] if len(set(x["label"] for x in output)) < 2 else []),
            "per_case": output}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--references", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--frequency", choices=["weekly", "monthly"], default="weekly")
    ap.add_argument("--window", type=int, default=12)
    ap.add_argument("--lag", type=int, default=4)
    args = ap.parse_args()
    data, _ = load_and_clean(args.input)
    cases = pd.read_csv(args.references, dtype=str).fillna("")
    metrics = evaluate(data, cases, DetectionConfig(frequency=args.frequency,
        history_window=args.window, growth_lag=args.lag))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in metrics.items() if k != "per_case"}, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
