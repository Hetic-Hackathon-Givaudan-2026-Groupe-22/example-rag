# Sillage — M3 Forecasting v0.2 sur 30 aliments

**Statut :** prototype expérimental reproductible — 12 novembre 2026.  
**Module :** M3, prévision de l'indice d'intérêt Google Trends pour les **trois mois suivants**.  
**Responsabilité :** expérimentation ML, en collaboration avec l'équipe Data pour les données collectées.

## Résumé des résultats

| Élément | M3 v0.1 (pilote) | M3 v0.2 (étendu) |
|---|---:|---:|
| Sujets alimentaires | 4 | **30** (pistache provisoire) |
| Séries géographiques exploitables | 19 | **136** |
| Observations mensuelles | 1 786 | **12 784** |
| Date de dernier relevé | 2026-10 | 2026-10 |
| Horizon | 3 mois | 3 mois |
| Méthode sélectionnée (MAE folds de sélection) | Last Value | **Last Value** |

### Comparaison sur la base étendue

| Algorithme | MAE sélection | MAE contrôle final | RMSE contrôle final |
|---|---:|---:|---:|
| **Last Value** | **7,6517** | 10,9743 | **19,7728** |
| Holt à tendance amortie | 8,1532 | 13,5714 | 22,1151 |
| Ridge Direct | 8,3804 | 12,1589 | 21,3696 |
| Naïve saisonnière (12 mois) | 10,7967 | **10,1593** | 20,2431 |

La meilleure MAE de **sélection** détermine le choix ; la période **final holdout** ne sert pas à choisir le modèle. La naïve saisonnière obtient la meilleure MAE sur ce seul contrôle final : il faut conserver cette nuance.

**Protocole :** 10 dates de backtest de sélection (2024-01 à 2026-04, trimestre par trimestre), 1 origine finale isolée (2026-07), 3 horizons (M+1 à M+3), 136 séries pays/ingrédient. **4 080 prédictions de sélection** et **408 prédictions de holdout par algorithme**.

## Données et préparation

Entrées originales :
- `data/input/reference_30_cas_google_trends_2019_2026.csv` : 30 sujets historiques, dont **`oud` non alimentaire** (conservation de l'original intact).
- `data/input/google_trends_lot_P0_2019_2026.csv` : collecte pilote contenant notamment la **pistache**.

La préparation produit `data/processed/m3_30_foods_geo_2019_2026.csv` :
- **29 sujets historiques alimentaires**, 131 séries par pays ;
- **1 sujet supplémentaire, pistache**, 5 séries par pays issues uniquement du P0 ;
- aucune série `WORLD` assimilée à un pays ;
- aucune duplication de matcha, dalgona ou Dubai chocolate entre P0 et référentiel ;
- **94 mois** par série, de janvier 2019 à octobre 2026 ;
- provenance conservée (`source_url`, `raw_file`, `query_original`, identifiant de normalisation) ;
- **aucune imputation**, aucun zéro fabriqué ; 4 818 valeurs zéro originales préservées ;
- les labels `buzz/tendance` ne figurent pas dans les variables M3.

Voir `data/processed/audit_preparation_30_aliments.json` pour les chiffres et empreintes SHA256 des deux fichiers sources.

### ⚠️ Limite scientifique majeure : normalisation Google Trends

Le référentiel historique provient de requêtes normalisées sur **2014–2026**, tandis que la pistache P0 est normalisée sur **2019–2026**. Les indices 0–100 ne sont ni des volumes de recherche comparables entre pays, ni des quantités de demande. Chaque série reste dans sa propre normalisation.

En outre, l'échelle du référentiel a pu être calculée à partir de données postérieures aux dates utilisées comme *origines* du backtest. L'algorithme ne lit pas ces valeurs futures lors de l'entraînement, mais **les indices normalisés anciens peuvent contenir une information future indirecte**. Ce test n'est donc **pas** une preuve de performance prospective stricte ; il faut obtenir des extractions datées, figées à la date de décision, pour aller plus loin.

La pistache est un **cas supplémentaire provisoire** ; son label M2 n'intervient dans aucun entraînement ni prédiction de M3. L'ablation du 30e cas est archivée dans `ablation_without_pistachio.json` : Last Value reste sélectionné même sur les 29 historiques.

## Exécution sur Windows / Git Bash dans VS Code

**IMPORTANT :** cette archive ZIP contient les fichiers directement à sa racine, **sans dossier interne supplémentaire**. Dans Windows : clic droit sur le ZIP, « Extraire tout » et sélectionner le dossier `C:\Users\VOTRE_UTILISATEUR\Projects\Givaudan\Sillage_M3_Forecasting_V02_30aliments` (ou le dossier créé automatiquement par Windows). En cas de doute, vérifier que `requirements.txt` est visible après `cd`.

```bash
cd ~/Projects/Givaudan/Sillage_M3_Forecasting_V02_30aliments
source ../sillage_pipeline_m1_v02/.venv/Scripts/activate
ls requirements.txt sillage_m3
python -m pip install -r requirements.txt
python -m pytest -q
```

Résultat attendu dans l'environnement testé : **20 passed**.

Recréer les observations nettoyées / préparées :

```bash
python -m sillage_m3.prepare_reference \
  --reference data/input/reference_30_cas_google_trends_2019_2026.csv \
  --p0 data/input/google_trends_lot_P0_2019_2026.csv \
  --out data/processed/m3_30_foods_geo_2019_2026.csv
```

Rejouer les backtests et générer les prévisions :

```bash
python -m sillage_m3.run \
  --input data/processed/m3_30_foods_geo_2019_2026.csv \
  --out artifacts/m3_30_aliments_v02
```

Lancer l'API **après** avoir produit les artefacts :

```bash
export SILLAGE_M3_ARTIFACT_DIR="artifacts/m3_30_aliments_v02"
uvicorn sillage_m3.api:app --port 8005
```

Swagger : `http://127.0.0.1:8005/docs` ; endpoints :
- `GET /m3/health`
- `GET /m3/metrics` — métriques du run étendu
- `GET /m3/forecasts?ingredient=matcha&country=FR` — 3 prévisions calculées ; possible avec `pistachio`.

L'API lit les **vrais CSV de sortie**, et ne génère pas de réponses simulées.

## Fichiers de sortie

`artifacts/m3_30_aliments_v02/` contient :
- `backtest_predictions.csv` — chaque prédiction datée, résultat et erreur ;
- `metrics_by_split.csv` — MAE, RMSE, biais, effectifs ;
- `metrics_by_ingredient.csv` — performances pour chacun des 30 ingrédients ;
- `metrics_by_horizon.csv` — erreur selon M+1, M+2 ou M+3 ;
- `metrics_by_cohort.csv` — référence historique vs pistache provisoire ;
- `metrics_topic_macro.csv` — moyenne de MAE par ingrédient (ne pas confondre avec micro) ;
- `forecast_selected.csv` — 408 prévisions (136 séries × 3 mois) ;
- `forecast_all_candidates.csv` — prédictions des 4 méthodes, pour comparaison ;
- `metrics_m3.json`, `manifest_m3.json`, `ablation_without_pistachio.json`.

## Critères / limites avant mise en production

1. Collecter davantage d'aliments et d'observations réellement datées en production.
2. Obtenir une normalisation temporelle comparable **à chaque date de backtest** (éviter la fuite de normalisation).
3. Séparer les cas et seuils de sélection des jeux de validation externes et futurs.
4. Évaluer séparément aliments, pays et horizons, et envisager des modèles adaptés aux séries très creuses (près de 38 % de zéros, provenant des exports).
5. Ne jamais présenter cette métrique comme une prévision garantie des ventes ni une preuve d'anticipation prospective.

## Publication GitHub

**Ne pas pousser les CSV sources collectés** tant que les conditions de licence/redistribution ne sont pas vérifiées. Voir `NOTE_GITHUB.md` pour le plan de publication. Le code et les rapports peuvent être publiés indépendamment des exports bruts.
