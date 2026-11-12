"""Read-only M4 API; outputs from actual CSVs; never fake API predictions."""
from __future__ import annotations
import os
from pathlib import Path
import pandas as pd
from fastapi import FastAPI, HTTPException, Query

app=FastAPI(title='Sillage M4 — Cross-market signals',version='0.1.0-experimental',
            description='Chronologie heuristique, pas de propagation causale prouvée.')


def folder():return Path(os.getenv('SILLAGE_M4_ARTIFACT_DIR','artifacts/m4_v01'))

def csv(name):
    p=folder()/name
    if not p.exists():raise HTTPException(503,f'M4 artifacts unavailable: {name}. Run python -m sillage_m4.run first.')
    return pd.read_csv(p).replace({float('nan'):None})


def records(df,limit):
    return df.head(limit).where(pd.notna(df),None).to_dict(orient='records')

@app.get('/m4/health')
def health():
    return {'status':'ok' if (folder()/'metrics_m4.json').exists() else 'missing_artifacts','artifact_dir':str(folder())}

@app.get('/m4/topics')
def topics():
    df=csv('ingredient_summary.csv');return {'count':len(df),'ingredients':df.ingredient.tolist()}

@app.get('/m4/timelines')
def get_timelines(ingredient:str|None=None,country:str|None=None,limit:int=Query(200,ge=1,le=500)):
    df=csv('market_timelines.csv')
    if ingredient:df=df[df.ingredient.str.lower()==ingredient.lower()]
    if country:df=df[df.country.str.upper()==country.upper()]
    return {'count':len(df),'items':records(df,limit)}

@app.get('/m4/lags')
def get_lags(ingredient:str|None=None,limit:int=Query(200,ge=1,le=500)):
    df=csv('cross_market_lags.csv')
    if ingredient:df=df[df.ingredient.str.lower()==ingredient.lower()]
    return {'count':len(df),'items':records(df,limit)}

@app.get('/m4/summary')
def get_summary(ingredient:str|None=None,limit:int=Query(100,ge=1,le=500)):
    df=csv('ingredient_summary.csv')
    if ingredient:df=df[df.ingredient.str.lower()==ingredient.lower()]
    return {'count':len(df),'items':records(df,limit)}

@app.get('/m4/methodology')
def methodology():
    from .core import PARAMS
    return {'method':'relative rise; within country 12-month baseline vs last 3 months; confirmation 2 of 3',
            'params':PARAMS,'warning':'Independent 0–100 normalization; retrospective source scaling; no cause/effect or market volume claim.',
            'threshold_sensitivity':'6, 8, 12 index points; flag unstable leaders','label':'experimental; human review required'}
