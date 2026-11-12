# Sillage — Intégration réelle Lot 01 Wikipédia → M1 (v0.3)

**G22 – Auralis | Établi le 12 novembre 2026**

## Objectif et état réel des livrables

Le pipeline M1 v0.3 reçoit les **12 690 observations réelles admissibles** issues du lot 01 Wikimedia, vérifie leur format, segmente les séries aux mois manquants, calcule les features de M1 et archive les alertes calculées. Le code et les résultats sont **reproductibles** avec l'environnement Python 3.12 déjà utilisé dans `sillage_pipeline_m1_v02`.

- **Fait :** nettoyage préalable Wikipédia audité (lot V1 distinct), 12 tests M1/API, premier run réel et artefacts conservés, API renvoyant les résultats du run.
- **À faire :** évaluation indépendante sur 30 cas, calibration des seuils et comparaison de modèles; M2 buzz/durable, M3 prévision et M4 cross-market pays ne sont pas réalisés.
- **Scientifiquement :** les 450 alertes sont des **signaux statistiques candidats**, pas 450 tendances validées et **pas 450 vrais positifs**. Elles sont nombreuses et les seuils doivent être évalués contre les cas de référence.

## Ne pas confondre Wikipédia et pays

`fr.wikipedia` décrit une édition **linguistique** consultée dans le monde entier; ce n'est pas la France. Les résultats restent identifiés par `segment_type=wiki_project` et `segment_id=fr.wikipedia`, avec `country_iso2=null`. Ne pas les utiliser pour conclure à une propagation cross-market nationale.

Les mois absents sont conservés comme absents : pas de remplissage par zéro, pas d'interpolation. Les observations sont découpées en **sous-séries mensuelles continues**, les sous-séries de 12 mois ou moins ne produisent pas d'alerte.

## Démarrage simple sur Windows + Git Bash

1. Décompresser `Sillage_M1_Wikipedia_V03.zip` dans `C:\Users\VOTRE_UTILISATEUR\Projects\Givaudan\`, à côté du dossier `sillage_pipeline_m1_v02`. **Ne pas fusionner les dossiers** : cela préserve le travail initial.
2. Depuis VS Code / Git Bash :

```bash
cd ~/Projects/Givaudan/Sillage_M1_Wikipedia_V03
source ../sillage_pipeline_m1_v02/.venv/Scripts/activate
python --version
python -m pytest -q
```

3. **Le premier traitement réel est déjà présent dans** `artifacts/wikipedia/20261112_wikipedia_lot01_m1_v03/`. Pour créer **une nouvelle exécution versionnée** sans écraser la précédente :

```bash
python -m sillage.wikipedia_m1 --input data/raw/wikipedia_lot01_eligible.csv --out artifacts/wikipedia
```

Le nom du run est horodaté et un pointeur `LATEST_WIKIPEDIA_RUN.txt` sélectionne le dernier run de l'API. Il n'est pas nécessaire de relancer le pipeline pour consulter le premier résultat.

4. Pour exposer les sorties **effectivement calculées** dans Swagger :

```bash
uvicorn sillage.wikipedia_api:app --port 8002
```

Ouvrir `http://127.0.0.1:8002/docs`. Tester `GET /health`, `GET /model`, `GET /quality`, `GET /signals?ingredient=matcha`, `GET /series?edition=fr.wikipedia`. L'API lit les fichiers générés et ne contient **aucun résultat inventé**. Les filtres portent sur les éditions Wikipédia et les ingrédients, pas sur les pays.

## Résultats du premier run réel

| Mesure | Valeur constatée |
|---|---:|
| Observations admissibles et traitées | 12 690 |
| Ingrédients / sujets alimentaires | 16 |
| Séries sujet × édition Wikipédia | 115 |
| Éditions Wikipédia | 10 |
| Sous-séries mensuelles continues | 120 |
| Séries avec des mois manquants | 3 |
| Mois absents dans ces séries | 11 |
| Sous-séries analysables (historique > 12 mois) | 117 |
| Sous-séries trop courtes | 3 |
| Lignes de features produites | 11 277 |
| Alertes candidates M1, non validées | 450 |
| Séries comportant au moins une alerte | 107 |
| Pays inférés, labels entraînés ou résultats simulés | 0 |

**Important :** le nombre élevé d'alertes suggère que les paramètres exploratoires (`z≥3`, croissance sur 4 mois `≥25%`, historique de 12 mois) doivent être calibrés. Ils ne constituent pas un résultat de précision ou de rappel.

## Fichiers à conserver pour les livrables

- `data/raw/wikipedia_lot01_eligible.csv` : **copie d'entrée non altérée** du lot admissible (autres observations mises en quarantaine restent dans le dossier de nettoyage V1).
- `artifacts/wikipedia/<run>/input_snapshot.csv` : instantané exact de l'entrée, pour audit.
- `artifacts/wikipedia/<run>/cleaned.csv` : observations contrôlées, séparées par sous-séries continues.
- `artifacts/wikipedia/<run>/features.csv` : features sans information future.
- `artifacts/wikipedia/<run>/signals.csv` et `signals.json` : alertes et provenance par observation.
- `artifacts/wikipedia/<run>/series.json` et `runs_quality.csv` : état des séries.
- `artifacts/wikipedia/<run>/quality.json` : statistiques de contrôle.
- `artifacts/wikipedia/<run>/manifest.json` : version de la méthode, paramètres, SHA-256 d'entrée et de sorties, date d'exécution.
- `tests/test_wikipedia_m1.py` : tests de non-fabrication de pays, non-fuite du futur, gaps, API, archivage.

## Changements de code par rapport à v0.2

- `sillage/pipeline.py` : le détecteur `detect` accepte dorénavant des `series_key` personnalisées. Par défaut, l'ancienne interface pays est inchangée et ses six tests continuent de réussir.
- `sillage/wikipedia_m1.py` : validation stricte du contrat Wikipédia, découpe des séries mensuelles continues, application du **même détecteur M1** aux éditions linguistiques, publication versionnée.
- `sillage/wikipedia_api.py` : API FastAPI indépendante (port 8002) qui retourne les vrais artefacts du run publié.
- `tests/test_wikipedia_m1.py` : six tests supplémentaires, pour un total de douze.

## Prochain travail Data

1. Faire vérifier manuellement une première sélection d'alertes sur des preuves externes et la courbe historique ; constituer **30 cas de référence indépendants**, incluant de vrais négatifs.
2. Définir la date de décision et les critères exacts de « signal émergent » et mesurer précision, rappel, F1, délai d'alerte sur ces cas, avec éventuelle validation temporelle.
3. Collecter des données **géolocalisées par pays** et comparables pour le vrai moteur cross-market ; ne pas utiliser le projet linguistique comme pays.
4. Une fois le modèle suffisamment évalué, l'intégrer à l'API métier de Sillage ; cette API Wikipédia est un premier endpoint technique, pas encore le radar complet.
