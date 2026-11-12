from pathlib import Path
import json
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sillage_m3.prepare_reference import prepare
from sillage_m3.core import load_series, predict, backtest, metrics
from sillage_m3.api import app

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT/'data/input/reference_30_cas_google_trends_2019_2026.csv'
P0 = ROOT/'data/input/google_trends_lot_P0_2019_2026.csv'
PREP = ROOT/'data/processed/m3_30_foods_geo_2019_2026.csv'
ART = ROOT/'artifacts/m3_30_aliments_v02'

def test_30_foods_geographic_series():
    df=pd.read_csv(PREP)
    assert df.topic_id.nunique() == 30
    assert len(df) == 12784
    assert df.groupby(['topic_id','country_iso2']).ngroups == 136
    assert set(df.country_iso2)=={'FR','US','JP','KR','AE'}
    assert 'oud' not in set(df.topic_id)
    assert 'label' not in df.columns
    assert df.frequency.eq('monthly').all()
    assert df.is_synthetic.astype(str).eq('False').all()
    assert set(df.normalization_window)=={'2014-01_to_2026-10','2019-01_to_2026-10'}

def test_original_values_unchanged_and_zero_preserved():
    df=pd.read_csv(PREP)
    ref=pd.read_csv(REF)
    p0=pd.read_csv(P0)
    a=ref[(ref.topic_id!='oud') & ref.zone.isin(['FR','US','JP','KR','AE'])]
    a2=df[df.dataset_partition=='historical_reference_29']
    assert len(a)==len(a2)==131*94
    src=a.set_index(['topic_id','zone','mois']).indice_0_100.sort_index()
    res=a2.assign(mois=a2.period_start.str.slice(0,7)).set_index(['topic_id','country_iso2','mois']).value.sort_index()
    np.testing.assert_array_equal(src.to_numpy(),res.to_numpy())
    pist=p0[(p0.topic_id=='pistachio') & p0.country_iso2.notna()]
    ps=df[df.topic_id=='pistachio']
    assert len(pist)==len(ps)==470
    np.testing.assert_array_equal(
        pist.set_index(['country_iso2','period_start']).value.sort_index().to_numpy(),
        ps.set_index(['country_iso2','period_start']).value.sort_index().to_numpy())
    assert int((df.value==0).sum())==4818
    assert not df.value.isna().any()

def test_prepare_independent_and_audited(tmp_path):
    info=prepare(REF,P0,tmp_path/'prepared.csv')
    assert info['n_ingredients']==30
    assert info['n_country_series']==136
    assert info['n_monthly_observations']==12784
    assert info['reference_world_rows_excluded']==2820
    assert info['reference_non_food_oud_country_rows_excluded']==470
    assert json.loads((tmp_path/'audit_preparation_30_aliments.json').read_text())['prepared_sha256']==info['prepared_sha256']

def test_no_future_leakage_in_prediction():
    s=load_series(PREP)[0]
    idx=65
    hist=s['values'][:idx+1]
    changed=s['values'].copy()
    changed[idx+1:]=100-changed[idx+1:]
    for model in ('last_value','holt_damped','ridge_direct','seasonal_naive_12'):
        np.testing.assert_allclose(predict(hist,s['dates'][idx],model),predict(changed[:idx+1],s['dates'][idx],model))

def test_pregenerated_forecasts_and_comparison():
    m=json.loads((ART/'metrics_m3.json').read_text(encoding='utf-8'))
    assert m['n_series']==136 and m['n_ingredients']==30
    assert m['model_selected_on_selection_folds']=='last_value'
    assert m['ablation_no_pistachio_selected_model']=='last_value'
    predictions=pd.read_csv(ART/'forecast_selected.csv')
    assert len(predictions)==408
    assert set(predictions.target_month)=={'2026-11','2026-12','2027-01'}
    assert predictions.is_selected.all()
    assert predictions.forecast_is_estimate.all()
    bt=pd.read_csv(ART/'backtest_predictions.csv')
    assert len(bt[(bt.split=='selection') & (bt.model=='last_value')])==4080
    assert len(bt[(bt.split=='final_holdout') & (bt.model=='last_value')])==408
    assert (bt.target_month>bt.origin_month).all()
    assert not set(bt[bt.split=='selection'].origin_month) & set(bt[bt.split=='final_holdout'].origin_month)


def test_api_real_extended_outputs(monkeypatch):
    monkeypatch.setenv('SILLAGE_M3_ARTIFACT_DIR',str(ART))
    client=TestClient(app)
    assert client.get('/m3/health').json()['status']=='ok'
    assert client.get('/m3/metrics').json()['n_ingredients']==30
    r=client.get('/m3/forecasts',params={'ingredient':'pistachio','country':'FR'})
    assert r.status_code==200
    assert r.json()['count']==3
    assert r.json()['items'][0]['model']=='last_value'
    assert client.get('/m3/forecasts',params={'ingredient':'oud'}).status_code==404
