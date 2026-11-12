"""API de démonstration V2 : calculs réels, aucun résultat statique inventé."""
from __future__ import annotations
import json,os
from pathlib import Path
from functools import lru_cache
from typing import Annotated
from fastapi import FastAPI,HTTPException,Query
from pydantic import BaseModel,Field
from joblib import load
import pandas as pd
from sillage_v2.features import FEATURE_COLUMNS,features_for_new_topic

ARTIFACT_DIR=Path(os.getenv('SILLAGE_V2_ARTIFACT_DIR','artifacts/comparison_v2'))
app=FastAPI(title='Sillage — M2 V2 expérimentale',version='2.0.0-experimental',description='Classification rétrospective de signaux Google Trends alimentaires ; score non calibré')

@lru_cache(maxsize=1)
def read_release():
    metrics_path=ARTIFACT_DIR/'metrics_v2.json'
    if not metrics_path.exists():
        raise FileNotFoundError('Artefacts V2 manquants : '+str(metrics_path))
    metadata=json.loads(metrics_path.read_text(encoding='utf-8'))
    prediction_file=f"predictions_{metadata['food_cases_evaluated']}_oof.csv"
    needed=['model_v2.joblib', prediction_file, 'audit_30_references.csv']
    missing=[str(ARTIFACT_DIR/p) for p in needed if not (ARTIFACT_DIR/p).exists()]
    if missing:raise FileNotFoundError('Artefacts V2 manquants : '+', '.join(missing))
    # Sécurité : charger uniquement le joblib généré localement par notre code, jamais un joblib inconnu.
    return {
        'model':load(ARTIFACT_DIR/'model_v2.joblib'),
        'metrics':metadata,
        'cases':pd.read_csv(ARTIFACT_DIR/prediction_file),
        'audit':pd.read_csv(ARTIFACT_DIR/'audit_30_references.csv'),
    }

def release_or_503():
    try:return read_release()
    except (FileNotFoundError,ValueError) as exc:raise HTTPException(503,str(exc)) from exc

class Observation(BaseModel):
    zone:str=Field(...,description='Code pays, ex. FR, JP, US, non WORLD')
    mois:str=Field(...,description='YYYY-MM')
    indice_0_100:float=Field(...,ge=0,le=100)

class PredictRequest(BaseModel):
    topic_id:str=Field(...,min_length=1,max_length=120)
    observations:list[Observation]=Field(...,min_length=1)

@app.get('/v2/health')
def health():
    try:
        r=read_release();return {'status':'ok','version':r['metrics']['version'],'cases':len(r['cases']),'mode':'retrospective_experimental'}
    except (FileNotFoundError,ValueError):return {'status':'missing_artifacts','version':'2.0.0-experimental'}

@app.get('/v2/model')
def model_info():
    r=release_or_503()
    return {'model':r['model'].get('model_type','LogisticRegression + StandardScaler'),'features':FEATURE_COLUMNS,
      'label_quality':'non_verifies_independamment','purpose':'retrospective buzz versus tendance',
      'evaluation':'Leave-One-Topic-Out','scope':'alimentaire',
      'warning':'Ce modèle ne prédit PAS encore la durabilité future d’une tendance émergente.'}

@app.get('/v2/metrics')
def metrics():return release_or_503()['metrics']

@app.get('/v2/references')
def references():
    d=release_or_503()['audit']
    return {'count':len(d),'data':d.where(pd.notna(d),None).to_dict('records')}

@app.get('/v2/cases')
def cases(topic_id:str|None=None,limit:Annotated[int,Query(ge=1,le=100)]=100):
    d=release_or_503()['cases']
    if topic_id:d=d.loc[d.topic_id==topic_id]
    d=d.head(limit)
    return {'count':len(d),'type':'out_of_fold_by_topic','cases':d.to_dict('records'),
      'note':'Scores validés seulement contre les labels provisoires du fichier fourni.'}

@app.post('/v2/predict')
def predict(req:PredictRequest):
    r=release_or_503()
    if req.topic_id.lower()=='oud':raise HTTPException(400,'Sujet hors périmètre alimentaire')
    df=pd.DataFrame([o.model_dump() for o in req.observations])
    if not df.empty and df['zone'].str.upper().eq('WORLD').any():raise HTTPException(400,'WORLD doit être exclu : pas un pays')
    try:feats=features_for_new_topic(df)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc
    model=r['model']['model'];columns=r['model']['feature_columns']
    import numpy as np
    x=np.asarray([[feats[c] for c in columns]], dtype=float)
    p=float(model.predict_proba(x)[0,1]);lab='tendance' if p>=0.5 else 'buzz'
    return {'topic_id':req.topic_id,'classification_exploratoire':lab,
      'score_tendance_non_calibre':round(p,6),'features':feats,
      'n_observations':len(df),'n_zones':df['zone'].nunique(),'version':r['metrics']['version'],
      'scientific_status':'retrospective_unverified_labels',
      'warning':'Ne pas interpréter ce score comme une probabilité validée de durabilité future.'}
