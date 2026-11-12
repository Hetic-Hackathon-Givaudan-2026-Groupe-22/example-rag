# Sillage — Dossier de preuve des 5 livrables (V2 expérimentale)

**Date :** 12 novembre 2026. **Porteur du livrable :** **Équipe G22 / Auralis (Sillage)**, contributions Data, ML, Tech et Product. **Dépôt final :** `Hetic-Hackathon-Givaudan-2026-Groupe-22/hackathon-app`, branche collective `develop` après revue/PR. La branche de publication initiale peut être personnelle sans modifier l’auteur collectif du projet.

> **Statut global :** les modules M1–M4 et le prototype M5 ont été développés et testés séparément en local. Ce dossier ne prétend pas être une chaîne M1→M5 intégrée ni un produit déployé. Les 30 cas ont une **validation rétrospective exploratoire**, avec des labels à auditer et la pistache provisoire.

## 1 — Données nettoyées et préparées

- `lot01_wikipedia_cleaning/output/observations_m1_eligible.csv` : **12 690 observations Wikipédia éligibles** après nettoyage ; quarantaine séparée, rapports qualité et manifeste. `wiki_project` représente une édition linguistique, pas un pays.
- `lot02_google_trends/data/clean/google_trends_p0_M1_pays.csv` : **1 786 observations géographiques** (19 séries pays×aliment, 4 aliments), et `google_trends_p0_WORLD_separe.csv` pour le niveau mondial, non traité comme pays.
- `m2_classifier_v2/data/processed/features_by_topic.csv` : caractéristiques numériques pour les cas du premier référentiel ; `m2_classifier_v2/artifacts/comparison_v2/features_by_topic.csv` pour la comparaison **30 aliments**.
- `m3_forecasting/data/processed/m3_30_foods_geo_2019_2026.csv` : **12 784 observations / 136 séries / 30 aliments** ; mêmes données préparées également disponibles pour M4.

**Provenance et droits :** les CSV originaux ont été conservés dans le ZIP local quand nécessaires à la reproduction, mais `data/raw/`, `data/source/` et `m3_forecasting/data/input/` sont exclus du `git add` par `.gitignore` jusqu'à autorisation de redistribution. Vérifier aussi les droits des tables *préparées*, qui dérivent des sources, avant publication sur le dépôt public.

## 2 — Pipeline fonctionnel

| Composant | Chemin | Résultat démontré |
|---|---|---|
| Nettoyage Wikipédia | `lot01_wikipedia_cleaning/code/` | Tests de nettoyage, rapports et données éligibles |
| M1, détection | `m1_detector/sillage/` | Détection sur Wikipedia/Google Trends, alertes candidates |
| M2, classification | `m2_classifier_v2/sillage_v2/` | Comparaison et chargement du modèle RF |
| M3, prévision | `m3_forecasting/sillage_m3/` | Backtests v0.2 ; suivi temporel v0.3 |
| M4, cross-market | `m4_crossmarket/sillage_m4/` | Chronologies par pays et seuils de robustesse |
| M5, démonstrateur RAG | `m5_rag_prototype/` | Prototype sur `story.txt` fictif, non intégré au métier |

Tester chaque module depuis son propre dossier. **Des tests unitaires réussis ne suffisent pas à valider la fiabilité métier.**

## 3 — Modèle V2 retenu et fichier publié après le push

**Module officiel de classification : M2 Random Forest** (candidat provisoire retenu sur la comparaison rétrospective des 30 aliments).

- Fichier de modèle : `m2_classifier_v2/artifacts/comparison_v2/model_v2.joblib`
- Code d'entraînement : `m2_classifier_v2/sillage_v2/compare_models.py`
- Identité / caractéristiques : `GET /v2/model`
- **Important :** la version de l'API incluse dans cette livraison pointe **par défaut sur `artifacts/comparison_v2`**, et non sur l'ancien modèle Logistic Regression dans `artifacts/v2`.
- Le mot **« publié »** ne sera exact qu'après un `git push` réussi (et vérification sur GitHub).

## 4 — Métriques et validation sur 30 cas de référence

| Modèle M2 | Corrects | F1 macro |
|---|---:|---:|
| Logistic Regression | 28/30 | 0,933 |
| **Random Forest** | **29/30** | **0,967** |
| XGBoost | 27/30 | 0,900 |

**Protocole :** Leave-One-Topic-Out, 30 aliments (= 15 buzz et 15 tendances selon les labels fournis), avec une ligne de features par sujet ; pas de découpage aléatoire des observations du même sujet. Données Google Trends évaluées **a posteriori** sur des trajectoires complètes. Les labels ne sont pas indépendamment vérifiés ; la pistache a un label provisoire et une normalisation distincte. Il faut **éviter de parler de prédiction avant le pic** ou de validation prospective.

Preuves :

- `m2_classifier_v2/artifacts/comparison_v2/metrics_v2.json`
- `m2_classifier_v2/artifacts/comparison_v2/predictions_30_oof.csv`
- `m2_classifier_v2/artifacts/comparison_v2/comparaison_par_sujet.csv`
- `m2_classifier_v2/artifacts/comparison_v2/RAPPORT_COMPARAISON_V2.md`
- `m2_classifier_v2/artifacts/comparison_v2/manifest_comparison_v2.json`

## 5 — API fonctionnelle renvoyant le véritable modèle

Depuis le dossier `sillage-ml/m2_classifier_v2`, dans le venv Python 3.12 :

```bash
python -m pip install -r requirements-comparison.txt
python -m pytest -q
export SILLAGE_V2_ARTIFACT_DIR=artifacts/comparison_v2
uvicorn sillage_v2.api:app --port 8004
```

Documentation : `http://127.0.0.1:8004/docs`. Vérifications recommandées :

- `GET /v2/model` doit renvoyer **`Random Forest`**.
- `GET /v2/metrics` doit renvoyer **30 cas** et la comparaison des trois méthodes.
- `GET /v2/cases` expose les prédictions de validation par sujet.
- `POST /v2/predict` calcule une réponse à partir de **nouvelles observations**, en chargeant réellement `model_v2.joblib`, et ne doit pas renvoyer un verdict codé en dur. Exemple de format dans Swagger.

**L'API est vérifiée en local ; elle n'est pas encore déployée ni reliée à l'API NestJS ou au front de l'équipe.** L'API ne remplace pas un test de bout en bout du produit.

## Modules complémentaires à inclure sans les sur-vendre

- **M1** : résultats exploratoires de détection, pas de précision/rappel validés.
- **M3 v0.2** : 30 aliments, sélection Last Value par MAE ; **v0.3** suit 11 288 états temporels, mais **mêmes prévisions et mêmes MAE**. Les deux versions et leur analyse sont conservées.
- **M4** : 104 séries avec hausse détectée ; 22 aliments comparables entre pays ; chronologie relative **sans preuve de causalité**.
- **M5** : Qwen2.5 1.5B + nomic-embed-text + ChromaDB via Ollama ; prototype RAG sur histoire fictive ; **pas de corpus alimentaire, pas de couplage M1–M4 et pas de métriques métier**. Le choix LLM reste ouvert pour validation ultérieure.

## Commandes rapides de vérification du modèle V2 et du dépôt

```bash
cd ~/Projects/Givaudan/hackathon-app
# après copie de sillage-ml/ et activation du venv
(cd sillage-ml/m2_classifier_v2 && python -m pytest -q)
git status -sb
git add sillage-ml/
git diff --cached --stat
git diff --cached --check
# vérifier les fichiers stagés AVANT le commit
```

Pour le rendu collectif, joindre : URL de la PR ou de la branche revue, lien vers ce fichier, lien vers `model_v2.joblib`, lien vers `metrics_v2.json`, résultat des tests et capture Swagger `GET /v2/model`. **Ne pas confondre mise en ligne GitHub et déploiement de l'API.**
