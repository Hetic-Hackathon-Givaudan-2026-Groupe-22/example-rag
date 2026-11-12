# Sillage M2 — 30e aliment ajouté à titre PROVISOIRE

**Date : 12 novembre 2026 — sous-ensemble exploratoire, NON une validation indépendante.**

## Changement réalisé

- L'ancien référentiel de 30 sujets est **préservé** sous `data/raw/reference_30_cas_google_trends_2019_2026.csv` (29 sujets alimentaires + `oud`, parfumerie).
- Nouveau fichier **distinct** : `data/raw/reference_30_aliments_pistache_PROVISOIRE.csv`. Les 564 lignes d'`oud` ont été remplacées par les **564 observations réelles de pistache**, issues du fichier P0 (FR, US, JP, KR, AE et WORLD ; 94 mois, janvier 2019–octobre 2026).
- Les indices, termes, URLs et dates de collecte sont **copiés sans modification** de l'export d'origine. Aucune valeur synthétique.
- `WORLD` est explicite et exclu des features pays, comme dans le modèle original.
- L'étiquette **`tendance` pour pistache est une hypothèse de travail NON VALIDÉE**, non une vérité terrain. Elle est indiquée dans le champ `note` de chaque ligne ajoutée.

### Limite supplémentaire majeure : normalisation Google Trends

Le lot P0 de la pistache est **normalisé sur 2019–2026** ; le référentiel historique contient des séries **exportées sur 2014–2026, puis tronquées à 2019–2026**. L'échelle 0–100 ne répond donc pas à la même référence. Ceci peut modifier les 7 features, notamment la fraction de mois avec indice >=10. Il est incorrect de traiter le classement et les métriques obtenues comme un benchmark comparatif validé. La collecte harmonisée devra être réalisée par Joseph/Tech.

## Exécuter sur Windows / Git Bash

```bash
cd ~/Projects/Givaudan/Sillage_Modele_V2_30aliments_PISTACHE_PROVISOIRE
source ../sillage_pipeline_m1_v02/.venv/Scripts/activate
python -m pip install -r requirements.txt
python -m pytest -q
python -m sillage_v2.train --input data/raw/reference_30_aliments_pistache_PROVISOIRE.csv --out artifacts/v2_pistache_PROVISOIRE
```

Le code `sillage_v2/train.py` a été corrigé pour nommer automatiquement le fichier `predictions_30_oof.csv` et ne plus annoncer à tort un total figé de 29. `sillage_v2/api.py` lit également le nombre de cas dans les métriques, sans casser la version d'origine à 29 cas.

Pour l'API de la version PROVISOIRE, depuis un **nouveau terminal** :

```bash
export SILLAGE_V2_ARTIFACT_DIR="artifacts/v2_pistache_PROVISOIRE"
uvicorn sillage_v2.api:app --port 8004
```

Consulter `http://127.0.0.1:8004/docs`, les routes `GET /v2/references`, `GET /v2/cases` et `GET /v2/metrics`. Ne pas confondre succès des routes et validité scientifique.

## À faire avant publication des résultats

1. Joseph/Tech : confirmer le label de pistache et sa pertinence comme **tendance** (un ingrédient ancien dont la popularité progresse n'est pas nécessairement une nouvelle tendance émergente).
2. Réextraire la pistache avec le **même périmètre temporel et la même méthode de normalisation** que les autres références.
3. Auditer les 30 labels historiques. Conserver l'ancienne évaluation à 29 cas comme point de comparaison, sans prétendre que 30 cas sont devenus indépendants ou validés.
4. Effectuer l'évaluation temporelle à une date T ; l'évaluation actuelle porte uniquement sur des trajectoires complètes 2019–2026.

**Ce lot constitue une préparation de développement, pas un nouveau modèle scientifique validé.**
