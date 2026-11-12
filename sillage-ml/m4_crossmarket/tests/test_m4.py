import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sillage_m4.core import load_series, detect_first_signal, timelines, cross_market, sensitivity, PARAMS
from sillage_m4.run import run
from sillage_m4.api import app

DATA=Path(__file__).resolve().parents[1]/'data/processed/m3_30_foods_geo_2019_2026.csv'
ROOT=Path(__file__).resolve().parents[1]


def series(topic='test',country='FR',jump=20,amount=40):
    dates=pd.date_range('2019-01-01',periods=36,freq='MS')
    arr=np.full(36,5.,float)
    arr[jump:]=amount
    return {'ingredient':topic,'country':country,'dates':dates,'values':arr,
            'normalization_scope':f'{topic}_{country}','query_original':topic,
            'source_url':f'https://trends.google.com/xyz/{country}','source':'gt',
            'dataset_partition':'ref','normalization_window':'2014-2026'}


def test_dataset_real_non_synthetic():
    s=load_series(DATA)
    assert len(s)==136
    assert len({x['ingredient'] for x in s})==30
    assert sum(len(x['values']) for x in s)==12784
    assert {x['country'] for x in s}=={'FR','US','JP','KR','AE'}


def test_relative_emergence_and_no_past():
    s=series(jump=20)
    d=detect_first_signal(s)
    assert d['first_signal_month']=='2020-10'
    assert d['months_above_threshold']>=2


def test_no_future_leak_in_detection():
    base=series(jump=20)
    d=detect_first_signal(base)['first_signal_month']
    modified=series(jump=20)
    modified['values'][30:]=100
    assert detect_first_signal(modified)['first_signal_month']==d


def test_flat_series_no_event():
    s=series()
    s['values'][:]=2
    assert detect_first_signal(s)['first_signal_month'] is None


def test_single_spike_not_confirmed():
    s=series()
    s['values'][:]=0
    s['values'][25]=100
    assert detect_first_signal(s)['first_signal_month'] is None


def test_two_countries_lags():
    s1=series(country='FR',jump=20)
    s2=series(country='US',jump=22)
    tl=timelines([s1,s2]);lags,sm=cross_market(tl)
    assert sm.iloc[0].first_markets_tied=='FR'
    assert sm.iloc[0].cross_market_comparison_available
    assert dict(zip(lags.country,lags.lag_months_after_first_observed))=={'FR':0,'US':2}


def test_tied_markets():
    tl=timelines([series(country='FR'),series(country='US')])
    lags,sm=cross_market(tl)
    assert sm.iloc[0].first_markets_tied=='FR;US'
    assert lags.lag_months_after_first_observed.eq(0).all()


def test_single_country_cannot_prove_crossmarket():
    tl=timelines([series(country='FR')]);_,sm=cross_market(tl)
    assert not sm.iloc[0].cross_market_comparison_available


def test_two_different_queries_flagged():
    a=series(country='FR');a['query_original']='pistache'
    b=series(country='US');b['query_original']='pistachio'
    tl=timelines([a,b]);assert tl.queries_differ_between_countries.all()


def test_missing_month_rejected(tmp_path):
    df=pd.read_csv(DATA).head(30)
    df=df.drop(df.index[5]);p=tmp_path/'missing.csv';df.to_csv(p,index=False)
    with pytest.raises(ValueError,match='Mois manquants'):load_series(p)


def test_world_rejected(tmp_path):
    df=pd.read_csv(DATA).head(30);df['country_iso2']='WORLD';p=tmp_path/'world.csv';df.to_csv(p,index=False)
    with pytest.raises(ValueError,match='WORLD'):load_series(p)


def test_synthetic_rejected(tmp_path):
    df=pd.read_csv(DATA).head(30);df.loc[df.index[0],'is_synthetic']=True
    p=tmp_path/'synthetic.csv';df.to_csv(p,index=False)
    with pytest.raises(ValueError,match='synthétiques'):load_series(p)


def test_sensitivity_flags_switch():
    s=[series(country='FR',jump=20),series(country='US',jump=22)]
    _,summary=cross_market(timelines(s));r=sensitivity(s,summary)
    assert r.iloc[0].same_leader_all_thresholds


def test_run_reproducible_and_manifest(tmp_path):
    output=run(DATA,tmp_path)
    assert output['n_ingredients']==30
    assert output['n_country_series']==136
    files=list(tmp_path.iterdir())
    assert len(files)==7
    manifest=json.loads((tmp_path/'manifest_m4.json').read_text())
    assert manifest['input_sha256']
    assert len(pd.read_csv(tmp_path/'market_timelines.csv'))==136


def test_api_real_results(monkeypatch):
    monkeypatch.setenv('SILLAGE_M4_ARTIFACT_DIR',str(ROOT/'artifacts/m4_v01'))
    with TestClient(app) as client:
        assert client.get('/m4/health').json()['status']=='ok'
        info=client.get('/m4/summary?ingredient=dubai_chocolate')
        assert info.status_code==200
        assert info.json()['count']==1
        lags=client.get('/m4/lags?ingredient=dubai_chocolate')
        assert lags.status_code==200
        assert lags.json()['count']==5
        assert client.get('/m4/topics').json()['count']==30
        assert client.get('/m4/methodology').status_code==200
