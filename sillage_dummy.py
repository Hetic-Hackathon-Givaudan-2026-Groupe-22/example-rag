"""Sillage — routes Data « dummy » (Gate 1, G22 Auralis).

Contrat d'interface entre Data et Tech pour le radar buzz / tendance. Les valeurs renvoyées sont
FACTICES (mode="dummy") : elles servent à brancher le front et l'API NestJS en attendant le vrai
score calculé à date figée (tickets #11, #14, #17). Le format, lui, est celui qui sera conservé.
"""

from __future__ import annotations

import hashlib
from datetime import date
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/sillage", tags=["sillage (dummy)"])

Verdict = Literal["suivre", "surveiller", "ignorer"]


class ScoreRequest(BaseModel):
    tendance: str = Field(..., min_length=1, examples=["pistache"])
    zone: str = Field("Europe", examples=["Europe"])
    periode_mois: int = Field(24, ge=3, le=120, description="Fenêtre d'observation en mois")
    categorie: str | None = Field(None, examples=["sucré"])
    date_figee: date | None = Field(
        None, description="Mode rejoué : seules les données antérieures à cette date sont utilisées"
    )
    masquer_nom: bool = Field(False, description="Mode preuve : le nom de la tendance est caché aux agents")


class Composantes(BaseModel):
    duree: float = Field(..., ge=0, le=100, description="La hausse dure-t-elle ?")
    geographie: float = Field(..., ge=0, le=100, description="Combien de pays touchés ?")
    categories: float = Field(..., ge=0, le=100, description="Combien de catégories de produits ?")
    lancements: float = Field(..., ge=0, le=100, description="Produits arrivés en rayon")
    matiere: float = Field(..., ge=0, le=100, description="Tension sur les matières premières")


class Argument(BaseModel):
    texte: str
    source: str


class Matiere(BaseModel):
    nom: str
    origine: str
    risque_prix: Literal["faible", "moyen", "élevé", "inconnu"]
    variation_prix_12m_pct: float | None = None
    source: str | None = None


class ScoreResponse(BaseModel):
    tendance: str
    zone: str
    date_donnees: date
    score: float = Field(..., ge=0, le=100, description="Score buzz (0) / durable (100), calculé par le code")
    composantes: Composantes
    verdict_propose: Verdict
    confiance: float = Field(..., ge=0, le=1)
    arguments: list[Argument]
    matieres: list[Matiere]
    mode: Literal["dummy", "reel"] = "dummy"


# Exemples des maquettes, pour une démo cohérente avant le vrai modèle.
EXEMPLES = {
    "pistache": dict(score=78, comp=(80, 75, 70, 72, 92), verdict="suivre", conf=0.74,
                     matieres=[Matiere(nom="Pistache", origine="États-Unis", risque_prix="élevé",
                                       variation_prix_12m_pct=35.0, source="Financial Times, 19/04/2025"),
                               Matiere(nom="Amande", origine="Toutes", risque_prix="inconnu")]),
    "dalgona": dict(score=18, comp=(10, 35, 15, 8, 5), verdict="ignorer", conf=0.81, matieres=[]),
    "matcha": dict(score=55, comp=(70, 60, 50, 55, 40), verdict="surveiller", conf=0.58, matieres=[]),
}


def _factice(nom: str) -> dict:
    h = hashlib.sha256(nom.lower().encode()).digest()
    comp = tuple(round(20 + h[i] / 255 * 70, 1) for i in range(5))
    score = round(sum(comp) / 5, 1)
    verdict = "suivre" if score >= 65 else "surveiller" if score >= 40 else "ignorer"
    return dict(score=score, comp=comp, verdict=verdict, conf=round(0.5 + h[5] / 255 * 0.3, 2), matieres=[])


@router.post("/score", response_model=ScoreResponse)
def score(req: ScoreRequest) -> ScoreResponse:
    """Score buzz / durable, verdict proposé et matières liées. **Valeurs factices (Gate 1).**"""
    cle = next((k for k in EXEMPLES if k in req.tendance.lower()), None)
    d = EXEMPLES[cle] if cle else _factice(req.tendance)
    nom = "Tendance A" if req.masquer_nom else req.tendance
    return ScoreResponse(
        tendance=nom,
        zone=req.zone,
        date_donnees=req.date_figee or date.today(),
        score=d["score"],
        composantes=Composantes(**dict(zip(["duree", "geographie", "categories", "lancements", "matiere"], d["comp"]))),
        verdict_propose=d["verdict"],
        confiance=d["conf"],
        arguments=[
            Argument(texte="[dummy] La hausse des recherches dure et touche plusieurs pays.",
                     source="Google Trends / Wikipedia Pageviews"),
            Argument(texte="[dummy] Des produits arrivent en rayon.", source="Open Food Facts"),
            Argument(texte="[dummy] Tension sur le prix de la matière première.", source="Série de prix (#14)"),
        ],
        matieres=d["matieres"],
    )


@router.get("/health")
def health() -> dict:
    """Vérifie que le service Data Sillage répond."""
    return {"service": "sillage-data", "mode": "dummy", "version": "0.1.0"}
