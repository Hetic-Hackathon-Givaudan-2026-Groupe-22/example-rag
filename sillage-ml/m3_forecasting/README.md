# Sillage — M3 v0.3 : Last Value + fenêtres glissantes de 3 mois

**Statut : prototype expérimental reproductible — 12 novembre 2026.**  
**Objectif :** suivre chaque mois la dynamique d'intérêt d'un ingrédient dans un pays, et conserver la prévision **Last Value** à M+1, M+2, M+3.  
**Périmètre :** 30 aliments, 136 séries géographiques et 12 784 observations mensuelles (2019-01 à 2026-10). La pistache est un ajout provisoire.  
**Projet / responsables :** Sillage — Équipe G22 / Auralis ; expérimentation ML réalisée au sein du pôle Data/ML avec les données collectées par l’équipe.

## Ce qui change par rapport à M3 v0.2

- **La méthode de prévision reste Last Value** : elle copie le dernier indice observé pour les 3 mois suivants. Les **408 prévisions du dernier mois sont strictement identiques** à celles de v0.2 (test automatisé de non-régression).
- **Nouveau moteur descriptif indépendant** : chaque mois, sur chaque ingrédient/pays, il compare **trois intervalles consécutifs non chevauchants de 3 mois**, utilisant uniquement les observations connues à la date T. La comparaison est recalculée **tous les mois** avec la fenêtre décalée.
- **États possibles** : `hausse_a_confirmer`, `hausse_persistante`, `stable_niveau_eleve`, `stable`, `repli_a_confirmer`, `repli_persistant`, `faible_attention`.
- **Une phase stable ou en repli n'est PAS automatiquement un buzz.** Ces états décrivent uniquement la dynamique d'une courbe ; la classification durable/buzz relève de **M2**, qui n'est **pas** réentraîné ici.
- **Diagnostic plus ciblé** : erreurs Last Value mesurées selon l'état observé au moment de la prévision, et selon M+1/M+2/M+3.

### Règles exploratoires, fixées avant cette exécution

À la date T, calculer les moyennes :
- A : T−8 à T−6 (3 mois),
- B : T−5 à T−3 (3 mois),
- C : T−2 à T (3 mois).

Une hausse est significative si **C−B ≥ 5 points** et **(C−B)/max(B,5) ≥ 15 %**. Un repli utilise la règle symétrique. Deux hausses successives (A→B et B→C) donnent `hausse_persistante`, sinon `hausse_a_confirmer`. Même principe pour les replis. Sans mouvement significatif, niveau C ≥ 15 donne `stable_niveau_eleve`, niveau A/B/C faible avec B et C < 5 donne `faible_attention`, sinon `stable`.

**Ces seuils sont heuristiques, non calibrés**. Les indices Google Trends restent propres à leur période de normalisation : ils ne sont pas des volumes, et les niveaux ne sont pas directement comparables entre pays. Le seuil de 5 points peut avoir des significations différentes selon les requêtes.

### Exemples observés dans les fichiers (octobre 2026)

| Série | État descriptif | Interprétation prudente |
|---|---|---|
| Matcha — FR | `stable_niveau_eleve` | Attention encore élevée ; l'absence d'augmentation ne signifie pas un buzz |
| Dalgona coffee — FR | `faible_attention` | Attention devenue faible à cette date ; ne préjuge pas de sa classification dans le passé |
| Dubai chocolate — US | `repli_persistant` | Deux intervalles de baisse successifs |
| Pistache — FR | `stable_niveau_eleve` | Niveau récent stable ; cas provisoire M2, mais source M3 réelle |

## Résultats de vérification

| Élément | Résultat |
|---|---:|
| Tests automatisés | **28 réussis** (20 hérités + 8 nouveaux) |
| Séries analysées | 136 |
| Lignes de suivi temporel (12 à 94 mois par série) | 11 288 |
| Derniers états individuels | 136 |
| Prévisions à trois mois | 408 |
| MAE Last Value — périodes de sélection | 7,6517 |
| MAE Last Value — holdout | 10,9743 |
| Changement des prévisions par rapport à v0.2 | **Aucun** (contrôlé par test) |

Le suivi temporel **n'améliore pas à lui seul** l'erreur des prévisions : il sert à savoir *quand* Last Value risque d'être inadapté (croissance ou retournement). Les phases ne constituent pas encore une classification M2 réentraînée et validée à chaque date.

## Installation / test Windows Git Bash

Cette archive ZIP contient directement les fichiers **à la racine**, sans dossier interne supplémentaire. L'extraire dans `C:\Users\VOTRE_UTILISATEUR\Projects\Givaudan\Sillage_M3_Fenetres_Glissantes_V03`.

```bash
cd ~/Projects/Givaudan/Sillage_M3_Fenetres_Glissantes_V03
source ../sillage_pipeline_m1_v02/.venv/Scripts/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

Attendu : `28 passed` (le nombre d'avertissements de dépendances peut varier).

## Reproduire M3 v0.3 et archiver les résultats

```bash
python -m sillage_m3.run_rolling \
  --input data/processed/m3_30_foods_geo_2019_2026.csv \
  --out artifacts/m3_fenetres_v03
```

Les résultats **v0.2 restent dans** `artifacts/m3_30_aliments_v02/`, sans être écrasés.

### Sorties ajoutées dans `artifacts/m3_fenetres_v03/`

- `rolling_states_monthly.csv` : tous les états de T mois en T mois, avec dates, trois moyennes, sources et provenance.
- `rolling_states_latest.csv` : dernier état de chaque ingrédient/pays.
- `forecast_last_value_with_state.csv` : **mêmes 408 prévisions Last Value**, enrichies de la phase à la date de prévision.
- `backtest_last_value_by_state.csv` : 4 488 prédictions Last Value historiques, associées à l'état disponible **à leur date d'origine**.
- `metrics_last_value_by_state.csv` : MAE, RMSE, biais par phase, horizon et split.
- `metrics_last_value_by_split.csv` : comparaison sélection / holdout.
- `metrics_rolling_v03.json` : configuration, effectifs et limites.
- `manifest_rolling_v03.json` : empreinte SHA256 des entrées/sorties, version et dates.

## Swagger / API

Dans ce dossier, après génération des artefacts :

```bash
export SILLAGE_M3_ARTIFACT_DIR="artifacts/m3_30_aliments_v02"
export SILLAGE_M3_ROLLING_ARTIFACT_DIR="artifacts/m3_fenetres_v03"
uvicorn sillage_m3.api:app --port 8005
```

Swagger : http://127.0.0.1:8005/docs  
Nouveaux endpoints :
- `GET /m3/dynamics/metrics`
- `GET /m3/dynamics/latest?ingredient=matcha&country=FR`
- `GET /m3/dynamics/history?ingredient=matcha&country=FR&limit=12`
- `GET /m3/dynamics/forecast?ingredient=matcha&country=FR`

Les anciens endpoints M3 v0.2 restent accessibles, inchangés.

## Ce qu'il reste réellement à valider

1. La **normalisation Google Trends a posteriori** peut indirectement utiliser des données futures (dans l'échelle 0–100), même si les calculs des états/prévisions ne regardent que le préfixe temporel. Un vrai test prospectif nécessitera des snapshots des requêtes à chaque date.
2. Les seuils des phases doivent être ajustés sur un ensemble de développement séparé puis testés sur de nouveaux sujets/périodes ; ne pas déclarer des « tendances durables » grâce aux seules règles ci-dessus.
3. **M2 dynamique n'est PAS implémenté** : Random Forest M2 était appris sur les trajectoires 2019–2026 complètes, donc l'appliquer tel quel à chaque préfixe serait méthodologiquement trompeur. Il faudra produire un protocole pré-pic et réentraîner M2 avec des features calculées à T.
4. Le meilleur modèle sur M3 v0.2 reste Last Value selon MAE sélection (7,6517), mais la naïve saisonnière fait mieux sur le holdout (10,1593 vs 10,9743). Pas de gain de MAE revendiqué pour v0.3.
5. Avant GitHub public, contrôler les droits de republication des CSV collectés ; voir `NOTE_GITHUB.md`.

Voir également `README_M3_V02_ORIGINAL.md` pour toutes les justifications et comparaisons de M3 v0.2.
