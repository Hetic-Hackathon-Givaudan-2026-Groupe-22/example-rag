"""M3 v0.3: rolling attention phases + unchanged Last Value 3-month forecasts.

CLI: python -m sillage_m3.run_rolling --input ... --out ...
No M2 RandomForest prefix inference: training on full trajectories would leak.
"""
from __future__ import annotations
import argparse, json, platform
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import numpy as np
from .core import load_series, predict, sha256, HORIZON, CUTOFFS
from .rolling import (history_states, STATES, INTERVAL_MONTHS,
                      CHANGE_THRESHOLD_POINTS, CHANGE_THRESHOLD_RATE,
                      LOW_ATTENTION_THRESHOLD, HIGH_ATTENTION_THRESHOLD)


def run(input_path: str | Path, out: str | Path) -> dict:
    input_path, out = Path(input_path), Path(out)
    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    out.mkdir(parents=True, exist_ok=True)
    series = load_series(input_path)
    states = pd.DataFrame(history_states(series))
    states.to_csv(out / 'rolling_states_monthly.csv', index=False)
    latest = (states.sort_values('origin_month').groupby(
        ['ingredient', 'country', 'normalization_scope'], as_index=False).tail(1)
        .sort_values(['ingredient','country']).reset_index(drop=True))
    latest.to_csv(out / 'rolling_states_latest.csv', index=False)
    # This keeps last_value entirely unchanged, with state only as metadata.
    projections = []
    for s in series:
        origin = s['dates'][-1]
        forecast = predict(s['values'], origin, 'last_value', HORIZON)
        for h, value in enumerate(forecast, 1):
            projections.append({
                'ingredient': s['ingredient'], 'country': s['country'],
                'normalization_scope': s['normalization_scope'],
                'origin_month': origin.strftime('%Y-%m'),
                'target_month': (origin+pd.DateOffset(months=h)).strftime('%Y-%m'),
                'horizon_months': h, 'model': 'last_value',
                'predicted_index_0_100': float(value),
                'is_synthetic': False, 'forecast_is_estimate': True,
            })
    latest_forecasts = pd.DataFrame(projections).merge(
        latest[['ingredient','country','normalization_scope','origin_month','phase',
                'mean_recent_3_months','delta_recent_vs_previous_points',
                'growth_confirmed_two_intervals','decline_confirmed_two_intervals']],
        on=['ingredient','country','normalization_scope','origin_month'],
        how='left', validate='many_to_one')
    if latest_forecasts.phase.isna().any():
        raise AssertionError('Des prévisions sans état temporel')
    latest_forecasts.to_csv(out/'forecast_last_value_with_state.csv',index=False)

    # Score the ORIGINAL last_value forecasts using the state known at EACH forecast origin.
    lv_rows = []
    for s in series:
        dates, values = s['dates'], s['values']
        for origin in CUTOFFS:
            ix = np.flatnonzero(dates == origin)
            if len(ix) != 1 or ix[0] < 59 or ix[0] + HORIZON >= len(dates):
                continue
            j = int(ix[0])
            forecast = predict(values[:j+1], origin, 'last_value', HORIZON)
            for h, estimated in enumerate(forecast, 1):
                actual = float(values[j+h])
                lv_rows.append({
                    'ingredient':s['ingredient'], 'country':s['country'],
                    'normalization_scope':s['normalization_scope'],
                    'dataset_partition':s['dataset_partition'],
                    'model':'last_value',
                    'origin_month':origin.strftime('%Y-%m'),
                    'target_month':dates[j+h].strftime('%Y-%m'),
                    'horizon_months':h,'actual':actual,
                    'prediction':float(estimated),
                    'abs_error':abs(float(estimated)-actual),
                    'error':float(estimated)-actual,
                    'split':'final_holdout' if origin == CUTOFFS[-1] else 'selection',
                })
    lv = pd.DataFrame(lv_rows)
    lv = lv.merge(states[['ingredient','country','normalization_scope','origin_month','phase',
                            'delta_recent_vs_previous_points','growth_confirmed_two_intervals']],
                  on=['ingredient','country','normalization_scope','origin_month'],
                  how='left', validate='many_to_one')
    if lv.phase.isna().any():
        raise AssertionError('Des dates de backtest sans état historique')
    lv.to_csv(out/'backtest_last_value_by_state.csv',index=False)
    grp = ['split','phase','horizon_months']
    grouped = (lv.groupby(grp,sort=True).agg(
        n_predictions=('abs_error','size'),
        mae=('abs_error','mean'), bias=('error','mean'))
        .reset_index())
    rmse = lv.groupby(grp,sort=True)['error'].apply(lambda x: float(np.sqrt(np.mean(np.square(x))))).reset_index(name='rmse')
    grouped = grouped.merge(rmse,on=grp,validate='one_to_one')
    grouped.to_csv(out/'metrics_last_value_by_state.csv',index=False)
    by_split = lv.groupby('split',sort=True).agg(
        mae=('abs_error','mean'), n_predictions=('abs_error','size')).reset_index()
    by_split.to_csv(out/'metrics_last_value_by_split.csv',index=False)

    phase_counts = latest.phase.value_counts().reindex(STATES,fill_value=0)
    summary = {
        'status':'experimental', 'version':'m3_v0.3_rolling',
        'n_ingredients':int(latest.ingredient.nunique()),
        'n_country_series':int(len(latest)),
        'n_rolling_state_rows':int(len(states)),
        'n_current_forecast_rows':int(len(latest_forecasts)),
        'forecast_horizon_months':HORIZON,
        'forecast_model':'last_value_UNCHANGED',
        'n_selection_origins':len(CUTOFFS)-1,
        'last_month':str(latest.origin_month.max()),
        'latest_phase_counts':{str(k):int(v) for k,v in phase_counts.items()},
        'last_value_mae_by_split':{str(r.split):round(float(r.mae),4) for r in by_split.itertuples()},
        'state_rule':{
            'window_months': INTERVAL_MONTHS,
            'nonoverlapping_comparison_blocks':3,
            'update_cadence':'monthly',
            'minimum_history_months':12,
            'delta_points_threshold':CHANGE_THRESHOLD_POINTS,
            'relative_change_threshold':CHANGE_THRESHOLD_RATE,
            'low_attention_threshold':LOW_ATTENTION_THRESHOLD,
            'stable_high_threshold':HIGH_ATTENTION_THRESHOLD,
            'thresholds_are_exploratory_not_calibrated':True,
        },
        'classification_warning':('Les phases décrivent une dynamique observée. '
              'Ce ne sont PAS des prédictions buzz vs tendance durable (M2). '
              'Le Random Forest M2 a été entraîné sur les courbes complètes : '
              'l’utiliser sur des préfixes sans réentraînement et validation serait trompeur.'),
        'normalization_warning':('Échelles Google Trends calculées a posteriori jusqu’en 2026 ; '
              'backtest strictement chronologique dans le code mais fuite de normalisation possible.'),
        'improvement_warning':('Les prévisions Last Value restent numériquement IDENTIQUES à v0.2. '
              'Le suivi temporel apporte une interprétation et un diagnostic, '
              'pas un gain démontré en MAE.'),
    }
    (out/'metrics_rolling_v03.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    names = ['rolling_states_monthly.csv','rolling_states_latest.csv',
             'forecast_last_value_with_state.csv','backtest_last_value_by_state.csv',
             'metrics_last_value_by_state.csv','metrics_last_value_by_split.csv',
             'metrics_rolling_v03.json']
    manifest = {
        'input':str(input_path), 'input_sha256':sha256(input_path),
        'timestamp_utc':datetime.now(timezone.utc).isoformat(),
        'code_version':'m3_v0.3_rolling', 'python':platform.python_version(),
        'cutoffs':[x.strftime('%Y-%m') for x in CUTOFFS],
        'selection_model_from_v02':'last_value',
        'future_observations_accessed_by_states':False,
        'dynamic_m2_retrained':False,
        'outputs_sha256':{n:sha256(out/n) for n in names},
    }
    (out/'manifest_rolling_v03.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
    return summary


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Sillage M3 v0.3: rolling phases + LastValue')
    p.add_argument('--input',default='data/processed/m3_30_foods_geo_2019_2026.csv')
    p.add_argument('--out',default='artifacts/m3_fenetres_v03')
    args = p.parse_args()
    print(json.dumps(run(args.input,args.out),indent=2,ensure_ascii=False))
