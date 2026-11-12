"""Read-only API serving M3 computed artifacts, no made-up forecasts."""
import os, json
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
import pandas as pd

app = FastAPI(title="Sillage — M3 Forecasting", version="0.2.0-experimental",
              description="3-month ahead Google Trends relative index forecasts, strictly per normalized series")

def artifact_dir():
    return Path(os.environ.get("SILLAGE_M3_ARTIFACT_DIR", "artifacts/m3_30_aliments_v02"))

def _json():
    p = artifact_dir() / "metrics_m3.json"
    if not p.is_file():
        raise HTTPException(503, "Exécuter python -m sillage_m3.run pour créer les artefacts M3")
    return json.loads(p.read_text(encoding="utf-8"))

@app.get("/m3/health")
def health():
    return {"status": "ok" if (artifact_dir() / "forecast_selected.csv").is_file() else "artifacts_missing"}

@app.get("/m3/metrics")
def get_metrics():
    return _json()

@app.get("/m3/forecasts")
def get_forecasts(ingredient: str | None = None, country: str | None = None,
                  limit: int = Query(default=100, ge=1, le=500)):
    p = artifact_dir() / "forecast_selected.csv"
    if not p.is_file():
        raise HTTPException(503, "Aucun forecast calculé ; lancer sillage_m3.run")
    df = pd.read_csv(p)
    if ingredient:
        df = df[df.ingredient == ingredient]
    if country:
        df = df[df.country == country.upper()]
    if df.empty:
        raise HTTPException(404, "Aucune prévision pour cet ingrédient/pays")
    return {"count": int(len(df)), "items": df.head(limit).to_dict("records"),
            "note": "Prévisions d'indice relatif par normalisation ; pas des volumes de vente"}

# M3 v0.3 additive endpoints: rolling diagnostic, without changing v0.2 endpoints.
def rolling_artifact_dir():
    return Path(os.environ.get('SILLAGE_M3_ROLLING_ARTIFACT_DIR', 'artifacts/m3_fenetres_v03'))


@app.get('/m3/dynamics/metrics')
def rolling_metrics():
    p = rolling_artifact_dir() / 'metrics_rolling_v03.json'
    if not p.is_file():
        raise HTTPException(503, 'Exécuter python -m sillage_m3.run_rolling pour créer les artefacts v0.3')
    return json.loads(p.read_text(encoding='utf-8'))


@app.get('/m3/dynamics/latest')
def rolling_latest(ingredient: str | None = None, country: str | None = None,
                   limit: int = Query(default=100, ge=1, le=500)):
    p = rolling_artifact_dir() / 'rolling_states_latest.csv'
    if not p.is_file():
        raise HTTPException(503, 'Aucun état de fenêtre enregistré ; lancer sillage_m3.run_rolling')
    df = pd.read_csv(p)
    if ingredient:
        df = df[df.ingredient == ingredient]
    if country:
        df = df[df.country == country.upper()]
    if df.empty:
        raise HTTPException(404, 'Aucune série pour cet aliment/pays')
    return {'count':int(len(df)), 'items':df.head(limit).to_dict('records'),
            'note':'Phases descriptives, PAS de labels buzz/trend ; prévision Last Value inchangée.'}


@app.get('/m3/dynamics/forecast')
def rolling_forecast(ingredient: str | None = None, country: str | None = None,
                     limit: int = Query(default=100, ge=1, le=500)):
    p = rolling_artifact_dir() / 'forecast_last_value_with_state.csv'
    if not p.is_file():
        raise HTTPException(503, 'Aucune prévision v0.3 ; lancer sillage_m3.run_rolling')
    df = pd.read_csv(p)
    if ingredient:
        df = df[df.ingredient == ingredient]
    if country:
        df = df[df.country == country.upper()]
    if df.empty:
        raise HTTPException(404, 'Aucune prévision pour cet aliment/pays')
    return {'count':int(len(df)), 'items':df.head(limit).to_dict('records'),
            'note':'Last Value v0.2 identique ; états de courbe mis à jour chaque mois.'}


@app.get('/m3/dynamics/history')
def rolling_history(ingredient: str, country: str,
                    limit: int = Query(default=100, ge=1, le=500)):
    p = rolling_artifact_dir() / 'rolling_states_monthly.csv'
    if not p.is_file():
        raise HTTPException(503, 'Aucun historique v0.3 ; lancer sillage_m3.run_rolling')
    df = pd.read_csv(p)
    df = df[(df.ingredient == ingredient) & (df.country == country.upper())]
    if df.empty:
        raise HTTPException(404, 'Aucune série pour cet aliment/pays')
    df = df.sort_values('origin_month',ascending=False)
    return {'count':int(len(df)), 'items':df.head(limit).to_dict('records'),
            'note':'Dynamique observée après chaque nouveau mois ; attention aux normalisations a posteriori.'}
