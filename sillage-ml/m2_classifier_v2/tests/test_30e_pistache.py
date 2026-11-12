"""Contrôles de provenance pour 30e cas PROVISOIRE (sans validation du label)."""
import csv
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def rows(path):
    with path.open(encoding='utf-8-sig',newline='') as fh:return list(csv.DictReader(fh))
def test_pistache_30_topics_sans_oud():
    rs=rows(ROOT/'data/raw/reference_30_aliments_pistache_PROVISOIRE.csv')
    topics=set(r['topic_id'] for r in rs)
    assert len(topics)==30 and 'oud' not in topics and 'pistachio' in topics
    assert len(rs)==15604
    assert len({r['topic_id'] for r in rs if r['label']=='buzz'})==15
    assert len({r['topic_id'] for r in rs if r['label']=='tendance'})==15

def test_pistache_complete_et_pays_reels():
    rs=rows(ROOT/'data/raw/reference_30_aliments_pistache_PROVISOIRE.csv')
    pt=[r for r in rs if r['topic_id']=='pistachio']
    assert len(pt)==564
    assert Counter(r['zone'] for r in pt)=={z:94 for z in ['FR','US','JP','KR','AE','WORLD']}
    assert sorted({r['mois'] for r in pt})[0]=='2019-01'
    assert sorted({r['mois'] for r in pt})[-1]=='2026-10'
    assert all(r['label']=='tendance' and 'PROVISOIRE' in r['note'] for r in pt)

def test_pistache_exactement_le_source_P0():
    source=rows(ROOT/'data/source/google_trends_lot_P0_2019_2026.csv')
    target=rows(ROOT/'data/raw/reference_30_aliments_pistache_PROVISOIRE.csv')
    a={(r['country_iso2'] or 'WORLD',r['period_start'][:7]):r for r in source if r['topic_id']=='pistachio'}
    b={(r['zone'],r['mois']):r for r in target if r['topic_id']=='pistachio'}
    assert a.keys()==b.keys()
    for k in a:
        assert a[k]['value']==b[k]['indice_0_100']
        assert a[k]['query_original']==b[k]['query_original']
        assert a[k]['source_url']==b[k]['source_url']
        assert a[k]['raw_file']==b[k]['raw_file']

def test_ancien_referentiel_intact():
    original=rows(ROOT/'data/raw/reference_30_cas_google_trends_2019_2026.csv')
    provisional=rows(ROOT/'data/raw/reference_30_aliments_pistache_PROVISOIRE.csv')
    a=[r for r in original if r['topic_id']!='oud']
    b=[r for r in provisional if r['topic_id']!='pistachio']
    assert a==b
