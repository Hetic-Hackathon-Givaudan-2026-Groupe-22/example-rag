# Sillage — M2 V2 | Comparaison de trois modèles (12/11/2026)

**Statut : expérimentation rétrospective ; pas de validation prédictive avant le pic.**

Cette livraison est une **copie distincte** de `Sillage_Modele_V2_30aliments_PISTACHE_PROVISOIRE` avec une comparaison reproductible ajoutée. Les anciens résultats ne sont pas écrasés. Voir `README_30E_CAS_PISTACHE.md` pour la construction du référentiel.

## Notre protocole

- **30 aliments** : 15 buzz / 15 tendances (pistache = label de travail PROVISOIRE).
- **7 features numériques identiques** pour tous les modèles, calculées par pays puis agrégées au niveau du sujet ; édition WORLD exclue.
- Chaque modèle utilise des hyperparamètres fixés dans `sillage_v2/compare_models.py`.
- Validation **Leave-One-Topic-Out** : le sujet du test est totalement absent de son entraînement ; le scaler de la régression logistique est ajusté dans chaque fold.
- Sensibilité : comparaison répétée en retirant la pistache provisoire (29 cas).
- Aucun split aléatoire par mois ou par pays : ces lignes ne sont pas des exemples ML indépendants.

## Résultats

| Modèle | Corrects / 30 | F1 macro |
|---|---:|---:|
| Logistic Regression | 28 | 0,933 |
| Random Forest | **29** | **0,967** |
| XGBoost | 27 | 0,900 |

**Random Forest est candidat technique retenu** pour cette première expérimentation ; son unique erreur sur le lot : `dubai_chocolate`. Sans pistache : Random Forest 28/29 (F1 macro ≈ 0,965). Tous ces chiffres sont à confirmer dans un protocole de prévision à date T.

## Vérifications effectuées sur cette livraison

- **22 tests automatisés passés** sur le projet complet (16 précédents + 6 de comparaison).
- API contrôlée sur `GET /v2/model`, `GET /v2/metrics`, `GET /v2/cases` et `POST /v2/predict` avec réponses HTTP 200 depuis les artefacts Random Forest.
- L'API n'est pas déployée dans l'application de l'équipe ; ces contrôles sont locaux.

## Installation et tests : Windows / Git Bash

Décompresser le ZIP dans `C:\Users\VOTRE_UTILISATEUR\Projects\Givaudan` **en évitant les doubles dossiers de même nom**.

```bash
cd ~/Projects/Givaudan/Sillage_M2_Comparaison_3_modeles_V2
source ../sillage_pipeline_m1_v02/.venv/Scripts/activate
python -m pip install -r requirements-comparison.txt
python -m pytest -q
```

Reproduire toute la comparaison :

```bash
python -m sillage_v2.compare_models --input data/raw/reference_30_aliments_pistache_PROVISOIRE.csv --out artifacts/comparison_v2
```

Pour interroger le **modèle Random Forest enregistré** (pas une prédiction statique) :

```bash
export SILLAGE_V2_ARTIFACT_DIR="artifacts/comparison_v2"
uvicorn sillage_v2.api:app --port 8004
```

Swagger : http://127.0.0.1:8004/docs ; `GET /v2/metrics`, `GET /v2/model`, `GET /v2/cases` et `POST /v2/predict`.

## Preuves de comparaison

Les sorties sont dans `artifacts/comparison_v2/` : `RAPPORT_COMPARAISON_V2.md`, `metrics_v2.json`, `comparaison_par_sujet.csv`, `predictions_*.csv`, `manifest_comparison_v2.json`, `model_v2.joblib` et `predictions_30_oof.csv`.

**Note sur le classement** : sélection après comparaison de trois candidats sur ces 30 mêmes cas -> optimisme possible ; ni un test externe ni un benchmark prospectif indépendant. Les sources originales et les labels n'ont pas été audités indépendamment. La pistache est une hypothèse et ses données Google Trends ne sont pas normalisées comme le référentiel de base. Les données du futur sont utilisées dans les features rétrospectives ; pas d'affirmation de capacité de prédiction avant le pic.

## Publication GitHub

Publier d'abord les scripts, tests, métriques, README et manifestes sur une branche de travail de `hackathon-app`, puis ouvrir une PR. Les sources dans `data/raw/` et `data/source/` sont **ignorées** par `.gitignore` en attendant validation de leurs droits. Conserver les résultats à 29 cas et la comparaison comme expérimentations distinctes ; ne pas écraser un résultat historique.
