"""API for real, computed Wikipedia M1 artifacts. No fabricated countries."""
import json
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query

app = FastAPI(title="Sillage M1 — Wikipédia", description="Signaux d'attention documentaire par édition linguistique, pas demande par pays.")


def _latest_dir() -> Path:
    base = Path(os.environ.get("SILLAGE_WIKI_ARTIFACT_DIR", "artifacts/wikipedia"))
    if (base / "manifest.json").is_file():
        return base
    pointer = base / "LATEST_WIKIPEDIA_RUN.txt"
    if not pointer.is_file():
        raise HTTPException(503, "Aucun run Wikipédia publié : lancer python -m sillage.wikipedia_m1")
    name = pointer.read_text(encoding="utf-8").strip()
    if Path(name).name != name or not name:
        raise HTTPException(503, "Pointeur de run invalide")
    return base / name


def _read(name: str):
    path = _latest_dir() / name
    if not path.is_file():
        raise HTTPException(503, f"Artefact absent : {name}")
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/health")
def health():
    try:
        p = _latest_dir()
        return {"status": "ready", "run": p.name, "scope": "wikipedia_edition_not_country"}
    except HTTPException:
        return {"status": "no_artifacts"}


@app.get("/model")
def model():
    return _read("manifest.json")


@app.get("/quality")
def quality():
    return _read("quality.json")


@app.get("/signals")
def signals(ingredient: str | None = None, edition: str | None = None, limit: int = Query(100, ge=1, le=500)):
    records = _read("signals.json")
    if ingredient:
        records = [r for r in records if r["ingredient"] == ingredient.lower().strip()]
    if edition:
        records = [r for r in records if r["segment_id"] == edition.strip()]
    return {"n_matching": len(records), "results": records[:limit], "caution": "Édition Wikipédia ≠ pays; les alertes ne sont pas des prédictions validées."}


@app.get("/series")
def series(ingredient: str | None = None, edition: str | None = None):
    records = _read("series.json")
    if ingredient:
        records = [r for r in records if r["ingredient"] == ingredient.lower().strip()]
    if edition:
        records = [r for r in records if r["segment_id"] == edition.strip()]
    return {"n_matching": len(records), "results": records}
