"""Agrégation de séries Google Trends au niveau TOPIC pour classifier buzz/durable.

Référentiel historique : caractères RETROSPECTIFS sur 2019-2026.
Ce module n'est pas un système de prévision à une date historique passée.
Aucune conversion fallacieuse de métriques Google Trends en volumes de vente.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    'med_peak_concentration',
    'med_recent_to_peak',
    'med_active_fraction',
    'med_longest_active_run',
    'med_end_vs_start',
    'med_stability',
    'med_recent_vs_history',
]
EXCLUDED_TOPIC_IDS = {'oud'}

@dataclass(frozen=True)
class FeaturePolicy:
    min_months: int = 24
    min_zones: int = 2
    activity_threshold: float = 10.0


def validate_reference(frame: pd.DataFrame) -> pd.DataFrame:
    required = {'topic_id','terme','label','zone','mois','indice_0_100','query_original','source_url'}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f'Colonnes manquantes : {missing}')
    df = frame.copy()
    df['topic_id'] = df['topic_id'].astype(str).str.strip()
    df['zone'] = df['zone'].astype(str).str.upper().str.strip()
    df['label'] = df['label'].astype(str).str.strip().str.lower()
    df['mois'] = df['mois'].astype(str).str.strip()
    df['value'] = pd.to_numeric(df['indice_0_100'],errors='coerce')
    parsed = pd.to_datetime(df['mois'],format='%Y-%m',errors='coerce')
    bad = parsed.isna()|df['value'].isna()|~np.isfinite(df['value'])|(df['value']<0)|(df['value']>100)
    if bool(bad.any()):
        raise ValueError(f'{int(bad.sum())} observation(s) invalides (date, indice Google Trends 0..100)')
    if df[['topic_id','zone','mois']].duplicated().any():
        raise ValueError('Même topic, zone, mois présent plusieurs fois ; dédupliquer chez le Tech')
    if not df['label'].isin(['buzz','tendance']).all():
        raise ValueError('Labels autres que buzz / tendance')
    if df.groupby('topic_id')['label'].nunique().gt(1).any():
        raise ValueError('Labels incohérents pour un même topic')
    # WORLD est une agrégation et ne doit pas compter comme pays supplémentaire.
    df = df.loc[df['zone']!='WORLD'].copy()
    df['mois_dt'] = parsed.loc[df.index]
    df.sort_values(['topic_id','zone','mois_dt'],inplace=True)
    return df.reset_index(drop=True)


def _longest_run(mask: np.ndarray) -> int:
    best=cur=0
    for b in mask:
        cur = cur+1 if bool(b) else 0
        best=max(best,cur)
    return best


def _zone_features(zone_data: pd.DataFrame, policy: FeaturePolicy) -> dict[str,float]|None:
    g=zone_data.sort_values('mois_dt')
    idx=g['mois_dt'].dt.to_period('M').array.asi8
    if len(g)<policy.min_months or len(np.unique(idx))!=len(idx) or np.any(np.diff(idx)!=1):
        return None
    x=g['value'].to_numpy(float)
    total=float(x.sum()); peak=max(float(x.max()),1.0)
    early=float(np.mean(x[:min(12,len(x))]))
    recent=float(np.mean(x[-min(12,len(x)):])); overall=float(np.mean(x))
    q75=float(np.percentile(x,75)); sigma=float(np.std(x))
    active=x>=policy.activity_threshold
    return {
      'peak_concentration':float(np.sort(x)[-min(6,len(x)):].sum()/max(total,1.0)),
      'recent_to_peak':float(recent/peak),
      'active_fraction':float(active.mean()),
      'longest_active_run':float(_longest_run(active)/len(x)),
      'end_vs_start':float(np.clip((recent-early)/max(early,5),-2,5)),
      'stability':float(1.0/(1.0+sigma/max(overall,5))),
      'recent_vs_history':float(np.clip((recent-q75)/max(q75,5),-2,5)),
    }


def extract_features(data:pd.DataFrame,policy:FeaturePolicy|None=None)->tuple[pd.DataFrame,pd.DataFrame]:
    policy=policy or FeaturePolicy()
    df=validate_reference(data)
    features=[]; audit=[]
    for topic, topic_rows in df.groupby('topic_id',sort=True):
        topic_zones=[]
        for zone,g in topic_rows.groupby('zone',sort=True):
            vals=_zone_features(g,policy)
            if vals is not None: topic_zones.append((zone,vals))
        labels=topic_rows['label'].unique()
        reason='ok'
        if topic in EXCLUDED_TOPIC_IDS: reason='hors_perimetre_alimentaire'
        elif len(topic_zones)<policy.min_zones:reason='series_insuffisantes'
        audit.append({
            'topic_id':topic,'terme':str(topic_rows['terme'].iloc[0]),'label_reference':labels[0],
            'n_zones':len(topic_zones),'n_observations':len(topic_rows),
            'status':reason,
            'reference_verified':False,
        })
        if reason!='ok':continue
        item={'topic_id':topic,'label':int(labels[0]=='tendance')}
        for col in ('peak_concentration','recent_to_peak','active_fraction','longest_active_run','end_vs_start','stability','recent_vs_history'):
            item['med_'+col]=float(np.median([v[col] for _,v in topic_zones]))
        features.append(item)
    features_df = pd.DataFrame(features)
    if features_df.empty:
        features_df = pd.DataFrame(columns=['topic_id', 'label'] + FEATURE_COLUMNS)
    return features_df.sort_values('topic_id').reset_index(drop=True), pd.DataFrame(audit).sort_values('topic_id').reset_index(drop=True)


def features_for_new_topic(frame:pd.DataFrame, policy:FeaturePolicy|None=None)->dict[str,float]:
    policy=policy or FeaturePolicy()
    df=frame.copy()
    required={'zone','mois','indice_0_100'}
    if not required.issubset(df.columns):raise ValueError('zone, mois et indice_0_100 obligatoires')
    df['topic_id']='NEW_TOPIC';df['terme']='new';df['label']='buzz'
    df['query_original']='user_defined';df['source_url']='not_provided'
    feats,audit=extract_features(df,policy)
    if feats.empty:raise ValueError(f'Insuffisance de séries : {audit.to_dict("records")}')
    return {c:float(feats.loc[0,c]) for c in FEATURE_COLUMNS}
