from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sillage_m3.core import load_series, predict, backtest, metrics, forecast_latest, MODELS
from sillage_m3.run import run

RAW = Path(__file__).resolve().parents[1] / 'data/input/google_trends_lot_P0_2019_2026.csv'

@pytest.fixture(scope='module')
def series():
    return load_series(RAW)


def test_19_series_four_topics(series):
    assert len(series) == 19
    assert set(x['ingredient'] for x in series) == {'matcha','pistachio','dalgona_coffee','dubai_chocolate'}


def test_no_world_as_country(series):
    assert all(x['country'] in {'FR','US','JP','KR','AE'} for x in series)


def test_only_full_monthly_historical_series(series):
    assert all(len(x['values']) == 94 for x in series)
    assert all(str(x['dates'][-1])[:10] == '2026-10-01' for x in series)


def test_no_missing_or_fabricated_zero(series):
    assert all(np.isfinite(x['values']).all() for x in series)
    assert sum(np.count_nonzero(x['values']==0) for x in series) > 0


def test_models_bounded_horizon(series):
    s=series[0]
    for m in MODELS:
        pred=predict(s['values'], s['dates'][-1], m)
        assert len(pred)==3 and np.isfinite(pred).all()
        assert (pred>=0).all() and (pred<=100).all()


def test_naive_last(series):
    y=series[0]['values']
    assert np.all(predict(y, series[0]['dates'][-1], 'last_value')==y[-1])


def test_seasonal_naive(series):
    y=series[0]['values']
    np.testing.assert_allclose(predict(y,series[0]['dates'][-1],'seasonal_naive_12'),y[-12:-9])


def test_no_future_leakage_at_fixed_origin(series):
    s=series[0]; hist=s['values'][:70].copy(); origin=s['dates'][69]
    changed=s['values'].copy(); changed[70:]=100-changed[70:]
    for m in MODELS:
        np.testing.assert_allclose(predict(hist,origin,m),predict(changed[:70],origin,m))


def test_bad_horizon_or_model(series):
    s=series[0]
    with pytest.raises(ValueError):predict(s['values'],s['dates'][-1],'unknown')
    with pytest.raises(ValueError):predict(s['values'],s['dates'][-1],'last_value',horizon=13)


def test_reject_missing_month(tmp_path):
    df=pd.read_csv(RAW)
    r=df[(df.topic_id=='matcha') & (df.country_iso2=='FR')].index[5]
    df=df.drop(r)
    path=tmp_path/'corrupt.csv';df.to_csv(path,index=False)
    with pytest.raises(ValueError,match='Mois manquants'):load_series(path)


def test_backtest_split_and_holdout(series):
    df=backtest(series[:2]); summ, best=metrics(df)
    assert set(df.split)=={'selection','final_holdout'}
    assert best in MODELS
    assert len(df[df.split=='final_holdout'])==2*4*3
    assert (df.target_month > df.origin_month).all()
    assert (df.groupby(['normalization_scope','split','model','origin_month']).size()==3).all()


def test_future_forecast_origin_and_dates(series):
    f=forecast_latest(series[:1], 'last_value')
    chosen=f[f.is_selected]
    assert set(chosen.target_month)=={'2026-11','2026-12','2027-01'}
    assert chosen.forecast_is_estimate.all()
    assert chosen.is_synthetic.eq(False).all()


def test_pipeline_generates_all_artifacts(tmp_path):
    summary=run(RAW,tmp_path)
    assert summary['n_series']==19
    assert summary['n_ingredients']==4
    assert len(pd.read_csv(tmp_path/'forecast_selected.csv'))==57
    assert len(pd.read_csv(tmp_path/'forecast_all_candidates.csv'))==228
    assert (tmp_path/'metrics_m3.json').is_file()
    assert (tmp_path/'manifest_m3.json').is_file()


def test_api_reads_real_files(tmp_path,monkeypatch):
    run(RAW,tmp_path)
    monkeypatch.setenv('SILLAGE_M3_ARTIFACT_DIR',str(tmp_path))
    from sillage_m3.api import app
    client=TestClient(app)
    assert client.get('/m3/health').json()['status']=='ok'
    assert client.get('/m3/metrics').status_code==200
    r=client.get('/m3/forecasts',params={'ingredient':'matcha','country':'FR'})
    assert r.status_code==200
    assert r.json()['count']==3
    assert r.json()['items'][0]['model']==client.get('/m3/metrics').json()['model_selected_on_selection_folds']
    assert client.get('/m3/forecasts',params={'ingredient':'nothere'}).status_code==404
