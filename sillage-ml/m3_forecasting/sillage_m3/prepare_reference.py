"""Create an auditable M3 geographic forecasting dataset from the collected sources.

Historical reference: 29 food topics (excluding non-food 'oud'); pistachio: 5 P0
country series. No WORLD-as-country, no P0 duplicates, no label columns.
Never manufacture values, interpolate, or recalculate Google Trends indices.
"""
from __future__ import annotations

import argparse
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

FOOD_EXCLUSION = 'oud'
P0_ADDITION = 'pistachio'
COUNTRIES = ('FR', 'US', 'JP', 'KR', 'AE')
EXPECTED_MONTHS = pd.period_range('2019-01', '2026-10', freq='M')


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assert_complete(df: pd.DataFrame, keys: list[str]) -> None:
    if df.duplicated(keys + ['period_start']).any():
        raise ValueError('Doublon topic/pays/normalisation/mois')
    for group_key, g in df.groupby(keys, sort=False, dropna=False):
        months = pd.PeriodIndex(pd.to_datetime(g.period_start), freq='M')
        if len(months) != len(EXPECTED_MONTHS) or not months.sort_values().equals(EXPECTED_MONTHS):
            raise ValueError(f'Série non complète, sans remplissage: {group_key}')
        if not g.value.between(0, 100).all() or g.value.isna().any():
            raise ValueError(f'Indices invalides pour {group_key}')
        if g.source_url.isna().any() or g.source_url.eq('').any() or g.raw_file.isna().any():
            raise ValueError(f'Provenance manquante pour {group_key}')


def prepare(reference_csv: str | Path, p0_csv: str | Path, out: str | Path) -> dict:
    reference_csv, p0_csv, out = Path(reference_csv), Path(p0_csv), Path(out)
    reference = pd.read_csv(reference_csv, dtype={'zone': 'string', 'topic_id': 'string'})
    p0 = pd.read_csv(p0_csv, dtype={'country_iso2': 'string', 'topic_id': 'string'})
    required_ref = {'topic_id','zone','mois','indice_0_100','query_original','source_url','raw_file','note','quality_flags','label'}
    required_p0 = {'topic_id','country_iso2','period_start','value','query_original','normalization_scope_id','source_url','raw_file','quality_flags','source','is_synthetic'}
    if required_ref-set(reference):
        raise ValueError(f'Colonnes référence manquantes: {required_ref-set(reference)}')
    if required_p0-set(p0):
        raise ValueError(f'Colonnes P0 manquantes: {required_p0-set(p0)}')
    excluded_world = int(reference.zone.eq('WORLD').sum())
    excluded_nonfood = int(reference[(reference.topic_id == FOOD_EXCLUSION)&(reference.zone != 'WORLD')].shape[0])
    ref_food = reference[(reference.topic_id != FOOD_EXCLUSION) & reference.zone.isin(COUNTRIES)].copy()
    if ref_food.topic_id.nunique() != 29:
        raise ValueError(f'29 aliments historiques attendus, trouvé {ref_food.topic_id.nunique()}')
    if ref_food.topic_id.eq(P0_ADDITION).any():
        raise ValueError('Pistache déjà dans le référentiel, risque de doublons')
    if (ref_food.groupby('topic_id').label.nunique() != 1).any():
        raise ValueError('Labels historiques contradictoires; audit requis')
    p0_food = p0[(p0.topic_id == P0_ADDITION)&p0.country_iso2.isin(COUNTRIES)].copy()
    if p0_food.empty or p0_food.country_iso2.nunique()!=5:
        raise ValueError('Pistache P0 géographique absente/incomplète')
    if p0_food.is_synthetic.astype(str).str.lower().isin(('true', '1', 'yes')).any():
        raise ValueError('Observations synthétiques dans P0')

    # Preserve the original source URLs and raw file identifiers, no Google index transformations.
    ref_data = pd.DataFrame({
        'topic_id': ref_food.topic_id,
        'country_iso2': ref_food.zone,
        'period_start': pd.to_datetime(ref_food.mois, format='%Y-%m').dt.strftime('%Y-%m-%d'),
        'value': pd.to_numeric(ref_food.indice_0_100, errors='raise'),
        'normalization_scope_id': 'gt_reference_2014_2026_' + ref_food.topic_id + '_' + ref_food.zone,
        'frequency':'monthly',
        'source':'google_trends_reference_2014_2026',
        'source_url':ref_food.source_url,
        'query_original':ref_food.query_original,
        'raw_file':ref_food.raw_file,
        'quality_flags':ref_food.quality_flags,
        'is_synthetic':False,
        'dataset_partition':'historical_reference_29',
        'normalization_window':'2014-01_to_2026-10',
        'collection_note':ref_food.note,
    })
    p0_data = pd.DataFrame({
        'topic_id':p0_food.topic_id,
        'country_iso2':p0_food.country_iso2,
        'period_start':pd.to_datetime(p0_food.period_start).dt.strftime('%Y-%m-%d'),
        'value':pd.to_numeric(p0_food.value, errors='raise'),
        'normalization_scope_id':p0_food.normalization_scope_id,
        'frequency':p0_food.frequency,
        'source':p0_food.source,
        'source_url':p0_food.source_url,
        'query_original':p0_food.query_original,
        'raw_file':p0_food.raw_file,
        'quality_flags':p0_food.quality_flags,
        'is_synthetic':False,
        'dataset_partition':'pistachio_p0_provisional',
        'normalization_window':'2019-01_to_2026-10',
        'collection_note':'Ajout pistache P0, normalisation 2019-2026 différente du référentiel 2014-2026',
    })
    combined = pd.concat([ref_data,p0_data], ignore_index=True)
    combined = combined.sort_values(['topic_id','country_iso2','period_start']).reset_index(drop=True)
    group = ['topic_id','country_iso2','normalization_scope_id']
    _assert_complete(combined,group)
    if combined.topic_id.nunique()!=30 or len(combined)!=136*94:
        raise ValueError(f'Effectifs inattendus: {combined.topic_id.nunique()} ingrédients, {len(combined)} points')
    if not set(combined.country_iso2.unique()).issubset(COUNTRIES):
        raise ValueError('Pays invalides')
    # Confirm original numeric values are untouched.
    if not ref_data.value.reset_index(drop=True).equals(pd.to_numeric(ref_food.indice_0_100).reset_index(drop=True)):
        raise ValueError('Valeurs de référence modifiées')
    if not p0_data.value.reset_index(drop=True).equals(pd.to_numeric(p0_food.value).reset_index(drop=True)):
        raise ValueError('Valeurs P0 modifiées')

    out.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(out,index=False)
    audit = {
        'status':'experimental',
        'n_ingredients':int(combined.topic_id.nunique()),
        'n_country_series':int(combined.groupby(group).ngroups),
        'n_monthly_observations':int(len(combined)),
        'n_historical_topics':int(ref_food.topic_id.nunique()),
        'n_historical_country_series':int(ref_data.groupby(group).ngroups),
        'n_pistachio_country_series':int(p0_data.groupby(group).ngroups),
        'reference_world_rows_excluded':excluded_world,
        'reference_non_food_oud_country_rows_excluded':excluded_nonfood,
        'p0_other_ingredients_excluded':int(len(p0)-len(p0_food)),
        'n_original_zero_indices_preserved':int((combined.value==0).sum()),
        'n_quality_flag_inferieur_a_1':int(combined.quality_flags.astype(str).str.contains('inferieur_a_1').sum()),
        'labels_used_as_m3_features':False,
        'reference_original_sha256':_digest(reference_csv),
        'p0_original_sha256':_digest(p0_csv),
        'prepared_sha256':_digest(out),
        'prepared_file':str(out),
        'generated_at_utc':datetime.now(timezone.utc).isoformat(),
        'warnings':[
            'Les indices Google Trends 0-100 sont propres à chaque requête et fenêtre de normalisation',
            'Le référentiel historique est normalisé sur 2014-2026, la pistache P0 sur 2019-2026',
            'Normalisation avec une fenêtre se terminant en octobre 2026: le backtest n’est pas un rejeu prospectif sans information future dans l’échelle',
            'Les labels buzz/tendance ne sont pas intégrés aux features M3; pistache provisoire',
            'Aucun mois ou zéro n’a été fabriqué, les zéros originaux sont préservés',
            'WORLD exclu des séries géographiques',
        ],
    }
    (out.parent / 'audit_preparation_30_aliments.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False),encoding='utf-8')
    return audit

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--reference', default='data/input/reference_30_cas_google_trends_2019_2026.csv')
    p.add_argument('--p0', default='data/input/google_trends_lot_P0_2019_2026.csv')
    p.add_argument('--out', default='data/processed/m3_30_foods_geo_2019_2026.csv')
    a=p.parse_args()
    print(json.dumps(prepare(a.reference,a.p0,a.out),indent=2,ensure_ascii=False))
