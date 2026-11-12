from pathlib import Path
import json
from datetime import date
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from sillage.wikipedia_m1 import read_wikipedia_csv, run_wikipedia, SERIES
from sillage.pipeline import DetectionConfig, detect
from sillage.wikipedia_api import app


def make_data(tmp_path, include_gap=False):
    rows=[]
    for ing in ['matcha', 'yuzu']:
        for i,dt in enumerate(pd.date_range('2021-01-01',periods=36,freq='MS')):
            if include_gap and i == 22:
                continue
            v=100. if i < 18 else 100+8*(i-17)
            rows.append(dict(observation_id=f'{ing}_{i}', ingredient=ing,
                segment_type='wiki_project', segment_id='fr.wikipedia', date=dt.strftime('%Y-%m-%d'),
                value=v, country_iso2=None, is_synthetic=False, quality_status='usable',
                source='wikimedia_pageviews', metric='article_pageviews_user', unit='views_count',
                source_url='https://wikimedia.org/api/', page_url='https://fr.wikipedia.org/wiki/Test',
                normalization_scope='absolute_pageviews_by_wikipedia_edition'))
    path=tmp_path/'wiki.csv'
    pd.DataFrame(rows).to_csv(path,index=False)
    return path


def test_country_is_never_attributed(tmp_path):
    cleaned,quality=read_wikipedia_csv(make_data(tmp_path))
    assert cleaned.country_iso2.isna().all()
    assert quality['country_attributed'] is False


def test_fake_country_rejected(tmp_path):
    path=make_data(tmp_path)
    df=pd.read_csv(path, dtype={'country_iso2': 'string'})
    df.loc[0,'country_iso2']='FR'
    df.to_csv(path,index=False)
    with pytest.raises(ValueError,match='country_iso2'):
        read_wikipedia_csv(path)


def test_month_gap_segments_without_zero_fill(tmp_path):
    cleaned,quality=read_wikipedia_csv(make_data(tmp_path,include_gap=True))
    assert len(cleaned)==70
    assert quality['n_series_with_gaps']==2
    assert quality['n_missing_month_positions_within_series']==2
    assert cleaned['value'].min()==100
    assert cleaned.groupby(SERIES)['continuity_run'].nunique().eq(2).all()


def test_signal_is_computed_from_observations(tmp_path):
    path=make_data(tmp_path)
    out,manifest=run_wikipedia(path,tmp_path/'artifacts',run_name='test_run')
    assert manifest['n_observations']==72
    assert manifest['n_series']==2
    assert manifest['n_alerts'] > 0
    alerts=json.loads((out/'signals.json').read_text(encoding='utf-8'))
    assert all(a['country_iso2'] is None and a['is_synthetic'] is False for a in alerts)
    assert all(a['source_url'].startswith('https://') for a in alerts)
    assert (out/'input_snapshot.csv').read_bytes() == path.read_bytes()
    assert manifest['input_sha256']


def test_no_future_leakage(tmp_path):
    clean,_=read_wikipedia_csv(make_data(tmp_path))
    k=SERIES+['continuity_run']; cfg=DetectionConfig(frequency='monthly')
    a,_,_=detect(clean.loc[clean.date<='2022-12-01'].copy(), cfg, series_key=k)
    b,_,_=detect(clean, cfg, series_key=k)
    b=b.loc[b.date<='2022-12-01'].reset_index(drop=True)
    pd.testing.assert_frame_equal(a.reset_index(drop=True), b)


def test_api_uses_actual_artifacts(tmp_path,monkeypatch):
    path=make_data(tmp_path)
    root=tmp_path/'published'
    run_wikipedia(path,root,run_name='run1')
    monkeypatch.setenv('SILLAGE_WIKI_ARTIFACT_DIR',str(root))
    client=TestClient(app)
    assert client.get('/health').json()['status']=='ready'
    info=client.get('/model').json()
    assert info['n_alerts']>0
    signals=client.get('/signals',params={'ingredient':'matcha'}).json()
    assert signals['n_matching']>0
    assert all(r['ingredient']=='matcha' and r['country_iso2'] is None for r in signals['results'])
    assert client.get('/quality').json()['n_series']==2
    assert client.get('/series',params={'edition':'fr.wikipedia'}).json()['n_matching']==2
