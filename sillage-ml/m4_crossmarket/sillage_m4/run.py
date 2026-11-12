"""Run: python -m sillage_m4.run --input ... --out ..."""
from __future__ import annotations
import argparse
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
from .core import load_series,timelines,cross_market,sensitivity,sha256,PARAMS,SENSITIVITY_POINTS


def run(input_path, out_dir):
    path=Path(input_path); out=Path(out_dir); out.mkdir(parents=True,exist_ok=True)
    series=load_series(path)
    tl=timelines(series)
    leads,summary=cross_market(tl)
    sens=sensitivity(series,summary)
    summary=summary.merge(sens[['ingredient','comparable_all_thresholds','same_leader_all_thresholds','threshold_sensitive_or_incomplete']],on='ingredient',validate='one_to_one')
    review=summary[(~summary.cross_market_comparison_available)|summary.queries_differ_between_countries|summary.early_boundary_flag_any|summary.threshold_sensitive_or_incomplete].copy()
    outputs={'market_timelines.csv':tl,'cross_market_lags.csv':leads,
             'ingredient_summary.csv':summary,'threshold_sensitivity.csv':sens,
             'review_needed.csv':review}
    for fn,df in outputs.items():df.to_csv(out/fn,index=False)
    n_comparable=int(summary.cross_market_comparison_available.sum())
    n_stable=int(summary.same_leader_all_thresholds.sum())
    metrics={'status':'experimental','version':'m4_v0.1',
             'n_ingredients':int(summary.shape[0]),'n_country_series':len(series),
             'n_observations':int(sum(len(s['values']) for s in series)),
             'n_countries_total':5,'n_country_series_signal_detected':int(tl.signal_detected.sum()),
             'n_topics_comparable_min_two_countries':n_comparable,
             'n_topics_leader_stable_across_thresholds':n_stable,
             'n_topics_need_review':int(review.shape[0]),
             'n_topics_multiple_tied_first':int(summary.first_markets_tied.fillna('').str.contains(';').sum()),
             'thresholds_exploratory':PARAMS,'sensitivity_min_points':list(SENSITIVITY_POINTS),
             'interpretation':'first confirmed relative-rise within observed data; no causal diffusion, no absolute market sizes',
             'critical_warning':'normalization uses 2014/2019–2026 including future after historical origin; retrospective chronology ONLY',
             'validation':'no independent onset ground truth; no precision/recall established'}
    (out/'metrics_m4.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8')
    manifest={'version':'m4_v0.1','input_path':str(path),'input_sha256':sha256(path),
              'generated_at_utc':datetime.now(timezone.utc).isoformat(),
              'python_version':platform.python_version(), 'params':PARAMS,
              'outputs_sha256':{f:sha256(out/f) for f in [*outputs,'metrics_m4.json']}}
    (out/'manifest_m4.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    return metrics


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();print(json.dumps(run(a.input,a.out),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
