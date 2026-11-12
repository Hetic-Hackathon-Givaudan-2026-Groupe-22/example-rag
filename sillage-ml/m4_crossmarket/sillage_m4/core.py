"""Cross-market timing based on within-country Google Trends changes.

IMPORTANT: Per-country search indices are independently normalized. Timings are
candidate *observed signals*, never absolute audience volumes or causal diffusion.
Detection at month T uses data only through T. The source normalization window,
however, includes future years, so these data do NOT prove prospective detection.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

COUNTRIES = ('FR', 'US', 'JP', 'KR', 'AE')
PARAMS = {'baseline_months': 12, 'recent_months': 3,
          'min_confirming_months': 2, 'min_increase_points': 8.0,
          'relative_threshold': 0.35, 'mad_multiplier': 2.0}
SENSITIVITY_POINTS = (6.0, 8.0, 12.0)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_series(path: str | Path) -> list[dict]:
    df = pd.read_csv(path, dtype={'country_iso2': 'string', 'topic_id': 'string'})
    required = {'topic_id','country_iso2','period_start','value','normalization_scope_id',
                'query_original','source_url','source','frequency','is_synthetic'}
    missing = required - set(df.columns)
    if missing: raise ValueError(f'Colonnes absentes: {sorted(missing)}')
    if df['is_synthetic'].astype(str).str.lower().isin(('true','1','yes')).any():
        raise ValueError('Refus de données synthétiques dans le rendu M4')
    if (~df.country_iso2.isin(COUNTRIES)).any():
        raise ValueError('M4 exige des pays ISO2, WORLD/langue Wikipédia sont exclus')
    if (df.frequency != 'monthly').any(): raise ValueError('Fréquence mensuelle requise')
    dates = pd.to_datetime(df.period_start, errors='raise')
    if (dates.dt.day != 1).any(): raise ValueError('Dates premier jour du mois uniquement')
    values = pd.to_numeric(df.value, errors='coerce')
    if values.isna().any() or (~values.between(0,100)).any():
        raise ValueError('Indices Google Trends manquants/hors [0,100]')
    df = df.assign(date=dates, value=values)
    out=[]
    for (topic,country), g in df.groupby(['topic_id','country_iso2'], sort=True):
        g=g.sort_values('date').reset_index(drop=True)
        if len(g)<24: raise ValueError(f'Série trop courte: {topic} {country}')
        if g.date.duplicated().any(): raise ValueError(f'Doublons: {topic} {country}')
        expected=pd.date_range(g.date.iloc[0],g.date.iloc[-1],freq='MS')
        if len(expected)!=len(g) or not np.array_equal(expected.values,g.date.to_numpy()):
            raise ValueError(f'Mois manquants: {topic} {country}, ne pas combler par zéro')
        for key in ['normalization_scope_id','query_original','source_url','source']:
            if g[key].isna().any() or g[key].nunique()!=1:
                raise ValueError(f'Provenance incohérente: {topic} {country} {key}')
        out.append({'ingredient':str(topic),'country':str(country),
                    'dates':pd.DatetimeIndex(g.date),'values':g.value.to_numpy(float),
                    'normalization_scope':str(g.normalization_scope_id.iloc[0]),
                    'query_original':str(g.query_original.iloc[0]),
                    'source_url':str(g.source_url.iloc[0]),
                    'source':str(g.source.iloc[0]),
                    'dataset_partition':str(g.dataset_partition.iloc[0]) if 'dataset_partition' in g else '',
                    'normalization_window':str(g.normalization_window.iloc[0]) if 'normalization_window' in g else ''})
    if not out: raise ValueError('Aucune série')
    return out


def threshold_history(baseline: np.ndarray, points: float=8.0):
    """Robust threshold depending only on baseline months."""
    med=float(np.median(baseline))
    mad=float(np.median(np.abs(baseline-med)))
    diff=max(points, PARAMS['relative_threshold']*max(med,5.), PARAMS['mad_multiplier']*mad)
    return med, mad, diff


def detect_first_signal(s: dict, points: float=8.0) -> dict:
    """First confirmed *relative increase* in observed period; month T as confirmation.

    12 baseline months immediately preceding the 3-month recent window; 2 out
    of 3 months must clear the threshold. Historical data available through T only.
    This does NOT find the first-ever emergence of a food in the country.
    """
    vals=np.asarray(s['values'],float); months=s['dates']
    first_ix=PARAMS['baseline_months']+PARAMS['recent_months']-1
    for i in range(first_ix, len(vals)):
        baseline=vals[i-14:i-2]
        recent=vals[i-2:i+1]
        med,mad,diff=threshold_history(baseline,points)
        exceeds=int(np.count_nonzero(recent>=med+diff))
        if exceeds>=2 and float(recent.mean())>=med+diff:
            return {'first_signal_month':months[i].strftime('%Y-%m'),
                    'last_window_mean':round(float(recent.mean()),3),
                    'baseline_median':round(med,3),'baseline_mad':round(mad,3),
                    'threshold_increase':round(diff,3),
                    'months_above_threshold':exceeds,
                    'early_boundary_flag':bool(i<first_ix+6)}
    return {'first_signal_month':None,'last_window_mean':None,'baseline_median':None,
            'baseline_mad':None,'threshold_increase':None,
            'months_above_threshold':0,'early_boundary_flag':False}


def timelines(series: list[dict], points: float=8.0) -> pd.DataFrame:
    queries_by_topic={}
    normalizations_by_topic={}
    for s in series:
        queries_by_topic.setdefault(s['ingredient'],set()).add(s['query_original'])
        normalizations_by_topic.setdefault(s['ingredient'],set()).add(s['normalization_window'])
    rows=[]
    for s in series:
        d=detect_first_signal(s,points)
        rows.append({'ingredient':s['ingredient'],'country':s['country'],
                     'first_signal_month':d['first_signal_month'],
                     'signal_detected':bool(d['first_signal_month']),
                     **{k:v for k,v in d.items() if k!='first_signal_month'},
                     'n_monthly_observations':len(s['values']),
                     'series_start':s['dates'][0].strftime('%Y-%m'),
                     'series_end':s['dates'][-1].strftime('%Y-%m'),
                     'query_original':s['query_original'],'source':s['source'],
                     'source_url':s['source_url'],
                     'normalization_scope':s['normalization_scope'],
                     'normalization_window':s['normalization_window'],
                     'dataset_partition':s['dataset_partition'],
                     'queries_differ_between_countries':len(queries_by_topic[s['ingredient']])>1,
                     'normalization_windows_differ':len(normalizations_by_topic[s['ingredient']])>1,
                     'cross_country_query_semantics_unverified':True,
                     'comparison_unit':'mois_de_signal_confirme_NON_volume'})
    return pd.DataFrame(rows).sort_values(['ingredient','country']).reset_index(drop=True)


def month_index(s: str) -> int:
    dt=pd.Timestamp(s)
    return dt.year*12+dt.month


def cross_market(tl: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame]:
    """Chronology with ties: no causal inference or volumes implied."""
    leads=[]; summaries=[]
    for topic,g in tl.groupby('ingredient',sort=True):
        detected=g[g.signal_detected].copy()
        n_country=len(g); n_detected=len(detected)
        earliest=min(detected.first_signal_month) if n_detected else None
        leaders=sorted(detected.loc[detected.first_signal_month==earliest,'country']) if earliest else []
        if earliest:
            detected['lag_months']=detected.first_signal_month.map(month_index)-month_index(earliest)
            for _,r in detected.sort_values(['first_signal_month','country']).iterrows():
                leads.append({'ingredient':topic,'country':r.country,
                              'first_signal_month':r.first_signal_month,
                              'lag_months_after_first_observed':int(r.lag_months),
                              'is_tied_first':bool(r.lag_months==0),
                              'first_markets_tied':';'.join(leaders),
                              'n_countries_available':n_country,
                              'n_countries_with_signal':n_detected,
                              'source_url':r.source_url,'query_original':r.query_original,
                              'normalization_scope':r.normalization_scope,
                              'queries_differ_between_countries':bool(r.queries_differ_between_countries),
                              'early_boundary_flag':bool(r.early_boundary_flag)})
        summaries.append({'ingredient':topic,'n_countries_available':n_country,
                          'n_countries_with_signal':n_detected,
                          'first_observed_signal_month':earliest,
                          'first_markets_tied':';'.join(leaders),
                          'cross_market_comparison_available':bool(n_country>=2 and n_detected>=2),
                          'month_span_first_to_last':max((month_index(x)-month_index(earliest) for x in detected.first_signal_month),default=0) if earliest else None,
                          'queries_differ_between_countries':bool(g.queries_differ_between_countries.any()),
                          'early_boundary_flag_any':bool(g.early_boundary_flag.any()),
                          'caution':'heuristic signal timing; no causal diffusion and no absolute market-size inference'})
    return pd.DataFrame(leads), pd.DataFrame(summaries)


def sensitivity(series: list[dict], base_summary: pd.DataFrame) -> pd.DataFrame:
    results={}
    for points in SENSITIVITY_POINTS:
        _, s=cross_market(timelines(series,points=points))
        results[points]=s.set_index('ingredient')
    records=[]
    for topic in sorted(base_summary.ingredient):
        leader=[str(results[p].loc[topic,'first_markets_tied']) for p in SENSITIVITY_POINTS]
        active=[bool(results[p].loc[topic,'cross_market_comparison_available']) for p in SENSITIVITY_POINTS]
        dates=[str(results[p].loc[topic,'first_observed_signal_month']) for p in SENSITIVITY_POINTS]
        valid=all(active)
        records.append({'ingredient':topic,'leader_threshold_6':leader[0],
                        'leader_threshold_8':leader[1], 'leader_threshold_12':leader[2],
                        'first_month_threshold_6':dates[0],
                        'first_month_threshold_8':dates[1],
                        'first_month_threshold_12':dates[2],
                        'comparable_all_thresholds':valid,
                        'same_leader_all_thresholds':bool(valid and len(set(leader))==1),
                        'threshold_sensitive_or_incomplete':not (valid and len(set(leader))==1)})
    return pd.DataFrame(records)
