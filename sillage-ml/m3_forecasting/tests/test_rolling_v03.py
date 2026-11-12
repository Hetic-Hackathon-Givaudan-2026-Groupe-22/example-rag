"""Unit + integration tests on real historical collection and at-origin chronology."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sillage_m3.rolling import describe_history
from sillage_m3.core import load_series, predict
from sillage_m3.run_rolling import run
from sillage_m3.api import app

ROOT=Path(__file__).resolve().parents[1]
PREP=ROOT/'data/processed/m3_30_foods_geo_2019_2026.csv'
V02=ROOT/'artifacts/m3_30_aliments_v02'
V03=ROOT/'artifacts/m3_fenetres_v03'


def test_persistent_growth_requires_both_intervals():
    y=np.asarray([10]*6+[10]*3+[20]*3+[30]*3,float)
    a=describe_history(y)
    assert a['phase']=='hausse_persistante'
    assert a['growth_confirmed_two_intervals'] is True
    assert a['is_buzz_vs_trend_label'] is False


def test_growth_single_interval_unconfirmed():
    assert describe_history(np.asarray([10]*9+[10]*3+[20]*3,float))['phase']=='hausse_a_confirmer'


def test_stable_high_is_not_no_trend_or_buzz():
    r=describe_history(np.full(18,35.0))
    assert r['phase']=='stable_niveau_eleve'
    assert r['is_buzz_vs_trend_label'] is False


def test_persistent_decline_and_low_after_decline():
    y=np.asarray([50]*9+[50]*3+[30]*3+[10]*3,float)
    assert describe_history(y)['phase']=='repli_persistant'
    assert describe_history(np.full(15,2.0))['phase']=='faible_attention'


def test_no_lookahead_even_if_future_changes():
    s=load_series(PREP)[0]
    cut=50
    pref=s['values'][:cut+1].copy()
    tampered=s['values'].copy()
    tampered[cut+1:] = 100 - tampered[cut+1:]
    assert describe_history(pref)==describe_history(tampered[:cut+1])
    np.testing.assert_array_equal(predict(pref,s['dates'][cut],'last_value'),
                                  predict(tampered[:cut+1],s['dates'][cut],'last_value'))


def test_bad_data_fail_closed():
    with pytest.raises(ValueError): describe_history(np.ones(8))
    with pytest.raises(ValueError): describe_history(np.array([10]*11+[np.nan]))
    with pytest.raises(ValueError): describe_history(np.array([10]*11+[101]))


def test_rolling_artifacts_generated_and_reproducible(tmp_path):
    report=run(PREP,tmp_path/'results')
    assert report['n_country_series']==136
    assert report['n_ingredients']==30
    assert report['n_rolling_state_rows']==136*(94-11)
    assert report['n_current_forecast_rows']==136*3
    latest=pd.read_csv(tmp_path/'results/rolling_states_latest.csv')
    history=pd.read_csv(tmp_path/'results/rolling_states_monthly.csv')
    f=pd.read_csv(tmp_path/'results/forecast_last_value_with_state.csv')
    assert len(latest)==136 and len(history)==11288 and len(f)==408
    assert set(f.model)=={'last_value'}
    assert latest.origin_month.eq('2026-10').all()
    assert history.origin_month.min()=='2019-12'
    assert history.origin_month.max()=='2026-10'
    assert not history.phase.isna().any()
    assert history.is_buzz_vs_trend_label.eq(False).all()
    old=pd.read_csv(V02/'forecast_selected.csv')
    joined=f.merge(old,on=['ingredient','country','normalization_scope','origin_month','target_month','horizon_months'],
                   validate='one_to_one',suffixes=('_new','_old'))
    assert len(joined)==408
    np.testing.assert_allclose(joined.predicted_index_0_100_new,joined.predicted_index_0_100_old,rtol=0,atol=1e-8)
    bt=pd.read_csv(tmp_path/'results/backtest_last_value_by_state.csv')
    assert len(bt)==136*11*3
    assert bt.groupby('split').size().to_dict()=={'selection':136*10*3,'final_holdout':136*3}
    assert set(bt.model)=={'last_value'}
    old_bt=pd.read_csv(V02/'backtest_predictions.csv')
    old_lv=old_bt[old_bt.model.eq('last_value')]
    m=bt.merge(old_lv,on=['ingredient','country','normalization_scope','origin_month','target_month','horizon_months','split','model'],validate='one_to_one')
    assert len(m)==len(bt)
    np.testing.assert_allclose(m.prediction_x,m.prediction_y,rtol=0,atol=1e-8)
    assert (bt.target_month > bt.origin_month).all()
    assert (tmp_path/'results/manifest_rolling_v03.json').is_file()


def test_api_dynamic_files(monkeypatch):
    assert (V03/'rolling_states_latest.csv').is_file()
    monkeypatch.setenv('SILLAGE_M3_ROLLING_ARTIFACT_DIR',str(V03))
    client=TestClient(app)
    assert client.get('/m3/dynamics/metrics').status_code==200
    latest=client.get('/m3/dynamics/latest',params={'ingredient':'matcha','country':'FR'})
    assert latest.status_code==200 and latest.json()['count']==1
    fc=client.get('/m3/dynamics/forecast',params={'ingredient':'matcha','country':'FR'})
    assert fc.status_code==200 and fc.json()['count']==3
    assert all(x['model']=='last_value' for x in fc.json()['items'])
    hist=client.get('/m3/dynamics/history',params={'ingredient':'matcha','country':'FR','limit':3})
    assert hist.status_code==200 and hist.json()['count']==83
    assert client.get('/m3/dynamics/latest',params={'ingredient':'oud'}).status_code==404
