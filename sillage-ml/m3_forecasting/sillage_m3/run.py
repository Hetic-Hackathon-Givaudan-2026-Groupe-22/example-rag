"""M3 geographical monthly forecasting: out-of-time folds + holdout and traceable artifacts."""
from __future__ import annotations
import argparse, json, platform
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
import sklearn
from .core import load_series, backtest, metrics, forecast_latest, sha256, CUTOFFS, MODELS


def run(input_path: str | Path, out: str | Path) -> dict:
    input_path, out = Path(input_path), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    series = load_series(input_path)
    bt = backtest(series)
    metric_df, best = metrics(bt)
    future = forecast_latest(series, best)
    selected = future[future.is_selected].copy()
    bt.to_csv(out / 'backtest_predictions.csv', index=False)
    metric_df.to_csv(out / 'metrics_by_split.csv', index=False)
    future.to_csv(out / 'forecast_all_candidates.csv', index=False)
    selected.to_csv(out / 'forecast_selected.csv', index=False)
    # All model comparisons retain the same time folds; metrics also reported per series and ingredient.
    topic_metrics = (bt.groupby(['split','model','ingredient'],sort=True)
                   .agg(mae=('abs_error','mean'),n_predictions=('abs_error','size'),
                        n_countries=('country','nunique')).reset_index())
    topic_metrics.to_csv(out/'metrics_by_ingredient.csv',index=False)
    horizon_metrics = (bt.groupby(['split','model','horizon_months'],sort=True)
                    .agg(mae=('abs_error','mean'), n_predictions=('abs_error','size')).reset_index())
    horizon_metrics.to_csv(out/'metrics_by_horizon.csv',index=False)
    cohort_metrics = (bt.groupby(['split','model','dataset_partition'],sort=True)
                   .agg(mae=('abs_error','mean'),n_predictions=('abs_error','size'),
                        n_ingredients=('ingredient','nunique')).reset_index())
    cohort_metrics.to_csv(out/'metrics_by_cohort.csv',index=False)
    topic_macro = (topic_metrics.groupby(['split','model'],sort=True)
                   .agg(mae_macro_per_ingredient=('mae','mean'),n_ingredients=('ingredient','size'))
                   .reset_index())
    topic_macro.to_csv(out/'metrics_topic_macro.csv',index=False)

    holdout = metric_df[metric_df.split=='final_holdout']
    summary = {
        'status':'experimental', 'version':'m3_v0.2',
        'forecast_horizon_months':3,
        'model_selected_on_selection_folds':best,
        'model_selection_criterion':'MAE micro par prédiction sur les folds de sélection ; holdout exclu de la sélection',
        'n_series':len(series), 'n_ingredients':len(set(x['ingredient'] for x in series)),
        'n_monthly_observations':sum(len(s['values']) for s in series),
        'n_selection_origins':len(CUTOFFS)-1,
        'holdout_origin':CUTOFFS[-1].strftime('%Y-%m'),
        'last_data_month':max(x['dates'][-1] for x in series).strftime('%Y-%m'),
        'data_partitions':pd.Series([s['dataset_partition'] for s in series]).value_counts().to_dict(),
        'selection_metrics':metric_df[metric_df.split=='selection'].set_index('model')[['mae','rmse','bias','n_predictions']].round(4).to_dict('index'),
        'holdout_metrics':holdout.set_index('model')[['mae','rmse','bias','n_predictions']].round(4).to_dict('index'),
        'selection_topic_macro_mae':topic_macro[topic_macro.split=='selection'].set_index('model')['mae_macro_per_ingredient'].round(4).to_dict(),
        'holdout_topic_macro_mae':topic_macro[topic_macro.split=='final_holdout'].set_index('model')['mae_macro_per_ingredient'].round(4).to_dict(),
        'label_used_as_feature':False,
        'scope_warning':'Google Trends 0-100 relatifs par requête, géographie et fenêtre de normalisation. Aucune agrégation des pays en volumes de demande.',
        'normalization_warning':'Référentiel 2014-2026; pistache P0 2019-2026. Le dénominateur de normalisation inclut potentiellement des périodes postérieures aux origines de backtest. Ce test ne peut PAS prouver une anticipation sans fuite d’information de normalisation.',
        'scientific_warning':'Étude rétrospective sur données de collecte; 30 aliments avec pistache provisoire; backtest chronologique mais normalisations a posteriori. Pas de preuve prospective.',
    }
    if 'pistachio_p0_provisional' in set(bt.dataset_partition):
        bt_ref_only = bt[bt.dataset_partition=='historical_reference_29']
        agg_ref, ref_best = metrics(bt_ref_only)
        audit_ref = {
            'status':'ablation_excluding_provisional_pistachio',
            'n_ingredients':int(bt_ref_only.ingredient.nunique()),
            'n_country_series':int(bt_ref_only[['ingredient','country','normalization_scope']].drop_duplicates().shape[0]),
            'selected_on_selection_folds':ref_best,
            'selection':agg_ref[agg_ref.split=='selection'].set_index('model')[['mae','rmse','n_predictions']].round(4).to_dict('index'),
            'holdout':agg_ref[agg_ref.split=='final_holdout'].set_index('model')[['mae','rmse','n_predictions']].round(4).to_dict('index'),
            'same_normalization_window_for_all_reference_series': True,
            'not_a_prospective_test':True,
        }
        (out/'ablation_without_pistachio.json').write_text(json.dumps(audit_ref,indent=2,ensure_ascii=False),encoding='utf-8')
        summary['ablation_no_pistachio_selected_model'] = ref_best
    (out/'metrics_m3.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    outputs = ['backtest_predictions.csv','metrics_by_split.csv','forecast_selected.csv','forecast_all_candidates.csv',
               'metrics_by_ingredient.csv','metrics_by_horizon.csv','metrics_by_cohort.csv',
               'metrics_topic_macro.csv','metrics_m3.json']
    if (out/'ablation_without_pistachio.json').is_file():
        outputs.append('ablation_without_pistachio.json')
    manifest = {
        'input':str(input_path), 'input_sha256':sha256(input_path),
        'generated_at_utc':datetime.now(timezone.utc).isoformat(),
        'code_version':'m3_v0.2', 'python':platform.python_version(),
        'pandas':pd.__version__, 'scikit_learn':sklearn.__version__,
        'cutoff_dates':[x.strftime('%Y-%m') for x in CUTOFFS],
        'selection_rule':'minimum selection-fold MAE; final_holdout NOT in selection',
        'months_missing_filled_with_zero':False,
        'world_rows_excluded':True,
        'input_has_label_feature':False,
        'outputs_sha256':{name:sha256(out/name) for name in outputs},
    }
    (out/'manifest_m3.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--input',default='data/processed/m3_30_foods_geo_2019_2026.csv')
    p.add_argument('--out',default='artifacts/m3_30_aliments_v02')
    a=p.parse_args()
    print(json.dumps(run(a.input,a.out),indent=2,ensure_ascii=False))
