"""Sillage M1 on real Wikimedia pageview series, segmented by Wikipedia edition.

Never infer a country from wiki_project. Never impute missing months as zero.
Scores are uncalibrated statistical alerts, not trend-durability probabilities.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from sillage import __version__
from sillage.pipeline import DetectionConfig, detect, _json_safe

SERIES = ["ingredient", "segment_type", "segment_id", "source", "metric", "normalization_scope"]
REQUIRED = SERIES + ["observation_id", "date", "value", "country_iso2", "is_synthetic", "quality_status", "source_url", "unit"]


def read_wikipedia_csv(path: Path) -> tuple[pd.DataFrame, dict]:
    raw = pd.read_csv(path, encoding="utf-8-sig", dtype={"country_iso2": "string"})
    missing = sorted(set(REQUIRED) - set(raw.columns))
    if missing:
        raise ValueError(f"Contrat de données Wikipédia incomplet : {missing}")
    if raw.empty:
        raise ValueError("CSV Wikipédia vide")
    if raw["country_iso2"].fillna("").astype(str).str.strip().ne("").any():
        raise ValueError("Wikipédia par langue ne fournit aucun pays : country_iso2 doit rester vide")
    if raw["segment_type"].ne("wiki_project").any() or raw["segment_id"].str.fullmatch(r"[a-z-]+\.wikipedia").fillna(False).eq(False).any():
        raise ValueError("Les segments doivent être des éditions Wikipédia (ex. fr.wikipedia)")
    if raw["quality_status"].ne("usable").any():
        raise ValueError("Le fichier doit contenir uniquement les séries déjà qualifiées usable")
    if raw["source"].ne("wikimedia_pageviews").any() or raw["metric"].ne("article_pageviews_user").any():
        raise ValueError("Métriques/source incompatibles avec ce connecteur")
    if raw["unit"].ne("views_count").any() or raw["is_synthetic"].astype(str).str.lower().ne("false").any():
        raise ValueError("Seules les vues Wikimedia réelles sont acceptées")
    if raw["source_url"].fillna("").eq("").any():
        raise ValueError("URL de provenance absente")
    for key in SERIES:
        if raw[key].isna().any() or raw[key].astype(str).str.strip().eq("").any():
            raise ValueError(f"Clé de série manquante : {key}")
    dates = pd.to_datetime(raw["date"], format="%Y-%m-%d", errors="coerce")
    if dates.isna().any() or dates.dt.day.ne(1).any():
        raise ValueError("Dates invalides : seules les dates YYYY-MM-01 sont attendues")
    values = pd.to_numeric(raw["value"], errors="coerce")
    if values.isna().any() or not np.isfinite(values.to_numpy()).all() or values.lt(0).any():
        raise ValueError("Vues Wikimedia manquantes, non finies ou négatives")
    if raw["observation_id"].duplicated().any() or raw.duplicated(SERIES + ["date"]).any():
        raise ValueError("Observation / mois dupliqué : arrêter et auditer")
    clean = raw.copy()
    clean["value"] = values.astype(float)
    clean["date"] = dates.dt.strftime("%Y-%m-%d")
    clean["country_iso2"] = None
    clean["is_synthetic"] = False
    clean = clean.sort_values(SERIES + ["date"], kind="stable").reset_index(drop=True)
    # Separate contiguous monthly runs. Missing months remain missing; do not interpolate.
    month_index = clean["date"].str.slice(0, 4).astype(int) * 12 + clean["date"].str.slice(5, 7).astype(int)
    contiguous = month_index.groupby([clean[c] for c in SERIES]).diff().eq(1)
    starts = ~contiguous
    clean["continuity_run"] = starts.groupby([clean[c] for c in SERIES]).cumsum().astype(int)
    sizes = clean.groupby(SERIES, sort=True).size()
    runs = clean.groupby(SERIES + ["continuity_run"], sort=True).size()
    report = {
        "input_rows": int(len(raw)),
        "validated_rows": int(len(clean)),
        "n_series": int(len(sizes)),
        "n_ingredients": int(clean["ingredient"].nunique()),
        "n_wikipedia_editions": int(clean["segment_id"].nunique()),
        "n_monthly_contiguous_runs": int(len(runs)),
        "n_series_with_gaps": int((runs.groupby(level=list(range(len(SERIES)))).size() > 1).sum()),
        "n_missing_month_positions_within_series": int(sum((pd.Period(g.date.max(),freq="M") - pd.Period(g.date.min(),freq="M")).n+1-len(g) for _,g in clean.groupby(SERIES))),
        "zero_values_preserved": int(clean["value"].eq(0).sum()),
        "country_attributed": False,
        "is_synthetic": False,
        "notes": [
            "Wikimedia pageviews = intérêt documentaire par édition linguistique; pas ventes/demande ni pays.",
            "Séries segmentées aux mois manquants; aucun zéro ou interpolation inventé.",
            "Les 12 mois antérieurs sont requis pour produire la première caractéristique M1.",
        ],
    }
    return clean, report


def run_wikipedia(input_path: Path, output_root: Path, cfg: DetectionConfig | None = None, run_name: str | None = None) -> tuple[Path, dict]:
    cfg = cfg or DetectionConfig(frequency="monthly")
    cfg.check()
    if cfg.frequency != "monthly":
        raise ValueError("Le fichier Wikipédia est mensuel; frequency=monthly obligatoire")
    source = Path(input_path)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    clean, quality = read_wikipedia_csv(source)
    key = SERIES + ["continuity_run"]
    features, signals, run_summaries = detect(clean, cfg, series_key=key)
    # Attach original URLs, without labels, from the exact source records.
    join_cols = SERIES + ["continuity_run", "date"]
    provenance_cols = join_cols + ["source_url", "page_url", "observation_id", "country_iso2"]
    present_provenance_cols = [x for x in provenance_cols if x in clean.columns]
    if not features.empty:
        features = features.merge(clean[present_provenance_cols], on=join_cols, how="left", validate="one_to_one")
    if not signals.empty:
        signals = signals.merge(clean[present_provenance_cols], on=join_cols, how="left", validate="one_to_one")
    # Aggregate run summaries to one row per source series; keep run-specific detail separately.
    series_rows = []
    grouped = clean.groupby(SERIES, sort=True)
    for name, group in grouped:
        props = dict(zip(SERIES, name))
        run_summary = run_summaries
        for col, val in props.items():
            run_summary = run_summary.loc[run_summary[col].eq(val)]
        valid_run = run_summary["status"].eq("ok")
        series_signals = signals
        for col, val in props.items():
            if not series_signals.empty:
                series_signals = series_signals.loc[series_signals[col].eq(val)]
        series_rows.append({
            **props,
            "country_iso2": None,
            "n_observations": int(len(group)),
            "first_date": group["date"].min(),
            "last_date": group["date"].max(),
            "n_contiguous_runs": int(group["continuity_run"].nunique()),
            "n_analyzed_runs": int(valid_run.sum()),
            "status": "ok" if valid_run.all() else ("partially_analyzed" if valid_run.any() else "insufficient_contiguous_history"),
            "emergence_events": int(len(series_signals)),
            "first_detected_at": None if series_signals.empty else series_signals["date"].min(),
            "is_synthetic": False,
        })
    series = pd.DataFrame(series_rows)
    quality.update({
        "n_analyzed_runs": int(run_summaries["status"].eq("ok").sum()),
        "n_unanalyzed_short_runs": int(run_summaries["status"].eq("insufficient_history").sum()),
        "n_feature_rows": int(len(features)),
        "n_alerts": int(len(signals)),
        "n_series_with_at_least_one_alert": int(series["emergence_events"].gt(0).sum()),
    })
    if run_name is None:
        run_name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + digest[:8]
    if not run_name or not all(x.isalnum() or x in "-_" for x in run_name):
        raise ValueError("Nom de run invalide")
    output = Path(output_root) / run_name
    if output.exists():
        raise FileExistsError(f"Le run existe déjà, aucun écrasement : {output}")
    output.mkdir(parents=True, exist_ok=False)
    # Archive exact input; full audit trail.
    shutil.copyfile(source, output / "input_snapshot.csv")
    clean.to_csv(output / "cleaned.csv", index=False, encoding="utf-8-sig")
    features.to_csv(output / "features.csv", index=False, encoding="utf-8-sig")
    signals.to_csv(output / "signals.csv", index=False, encoding="utf-8-sig")
    (output / "signals.json").write_text(json.dumps(_json_safe(signals.to_dict("records")), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    (output / "series.json").write_text(json.dumps(_json_safe(series.to_dict("records")), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    (output / "quality.json").write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")
    run_summaries.to_csv(output / "runs_quality.csv", index=False, encoding="utf-8-sig")
    manifest = {
        "run_id": run_name,
        "model_version": f"M1-wikipedia-statistical-baseline-{__version__}",
        "model_type": "detector_untrained_heuristic",
        "method": "robust_z_past_median_plus_lag_growth",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_source": str(source),
        "input_sha256": digest,
        "parameters": asdict(cfg),
        "data_scope": "article_pageviews_by_wikipedia_edition",
        "n_observations": int(len(clean)),
        "n_series": len(series),
        "n_alerts": int(len(signals)),
        "contains_real": True,
        "contains_synthetic": False,
        "model_validation": "NON EVALUÉ SUR 30 CAS INDÉPENDANTS",
        "country_warning": "wiki_project != country; aucune inférence de pays / pas de résultat cross-market",
        "statistical_warning": "Alertes heuristiques non calibrées; pas de classification buzz/durable ni de prévision.",
    }
    files_to_hash = ["input_snapshot.csv", "cleaned.csv", "features.csv", "signals.csv", "signals.json", "series.json", "quality.json", "runs_quality.csv"]
    manifest["output_sha256"] = {f: hashlib.sha256((output / f).read_bytes()).hexdigest() for f in files_to_hash}
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (Path(output_root) / "LATEST_WIKIPEDIA_RUN.txt").write_text(run_name + "\n", encoding="utf-8")
    return output, manifest


def main() -> None:
    ap = argparse.ArgumentParser(description="Sillage M1 pour observations Wikimedia : pas de pays inventés")
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("artifacts/wikipedia"), help="Racine des runs versionnés")
    ap.add_argument("--window", type=int, default=12)
    ap.add_argument("--lag", type=int, default=4)
    ap.add_argument("--z", type=float, default=3.)
    ap.add_argument("--growth", type=float, default=0.25)
    ap.add_argument("--name", type=str, default=None)
    args = ap.parse_args()
    out, manifest = run_wikipedia(args.input, args.out, DetectionConfig(frequency="monthly", history_window=args.window, growth_lag=args.lag, z_threshold=args.z, growth_threshold=args.growth), args.name)
    print(json.dumps({"output_dir": str(out), "run_id": manifest["run_id"], "n_observations": manifest["n_observations"], "n_series": manifest["n_series"], "n_alerts": manifest["n_alerts"]}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
