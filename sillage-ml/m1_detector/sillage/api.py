"""API des RÉSULTATS CALCULÉS, jamais des données inventées dans les endpoints."""
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from sillage import __version__

app = FastAPI(title="Sillage M1 API", version=__version__, description="Baseline de détection, pas classification de durabilité")


def _dir() -> Path:
    return Path(os.environ.get("SILLAGE_ARTIFACT_DIR", "artifacts/real"))


def _load(filename: str):
    p = _dir() / filename
    if not p.is_file():
        raise HTTPException(status_code=503, detail=f"Artefact absent : {p}; exécuter le pipeline avant l'API")
    return json.loads(p.read_text(encoding="utf-8"))


@app.get("/health")
def health():
    return {"status": "ready" if (_dir() / "manifest.json").exists() else "no_artifacts",
            "artifact_directory": str(_dir()), "version": __version__}


@app.get("/model")
def model():
    return _load("manifest.json")


@app.get("/quality")
def quality():
    return _load("quality.json")


@app.get("/signals")
def signals(ingredient: Optional[str] = None, country: Optional[str] = None,
            source: Optional[str] = None, limit: int = Query(default=100, ge=1, le=500)):
    rows = _load("signals.json")
    if ingredient:
        rows = [r for r in rows if r["ingredient"] == ingredient.lower().strip()]
    if country:
        rows = [r for r in rows if r["country"] == country.upper().strip()]
    if source:
        rows = [r for r in rows if r["source"] == source.strip()]
    return {"n_matching": len(rows), "results": rows[:limit], "warning": "Une émergence n'est pas une preuve de tendance durable."}


@app.get("/series")
def series(ingredient: Optional[str] = None, country: Optional[str] = None):
    rows = _load("series.json")
    if ingredient:
        rows = [r for r in rows if r["ingredient"] == ingredient.lower().strip()]
    if country:
        rows = [r for r in rows if r["country"] == country.upper().strip()]
    return {"n_matching": len(rows), "results": rows}
