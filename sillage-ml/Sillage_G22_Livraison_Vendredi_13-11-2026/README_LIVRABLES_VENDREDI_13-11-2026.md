# SILLAGE — Livraison Data & ML | Vendredi 13 novembre 2026

**G22 · Auralis — Hackathon Givaudan**  
**Livraison collective :** Joseph, Rossaina et Roua — pôle Data & ML  
**Repository :** [example-rag / main / sillage-ml](https://github.com/Hetic-Hackathon-Givaudan-2026-Groupe-22/example-rag/tree/main/sillage-ml)  
**Rapport PDF :** [Sillage_G22_Livrables_Vendredi_13-11-2026.pdf](docs/Sillage_G22_Livrables_Vendredi_13-11-2026.pdf)

## Synthèse des cinq livrables

| Livrable demandé | Travail réalisé et preuve |
|---|---|
| **1. Code et documentation finalisés** | Code Python, jeux de données préparés, modèles, résultats exportés, tests, API FastAPI et README de chaque module M1–M4 ; prototype RAG M5 documenté. |
| **2. Procédure de reproduction des résultats** | Instructions d'installation, commandes de tests et d'exécution, jeux préparés, métriques et manifestes de provenance. |
| **3. Comparaison V1/V2 avec métriques** | Comparaison de la V1 du mardi 10/11 et de la V2 du jeudi 12/11, ancrée dans l'historique Git et les mesures enregistrées. |
| **4. Analyse des limites et des biais** | Analyse documentée des sources, de la normalisation Google Trends, de la validation rétrospective, du périmètre de 30 cas et du RAG. |
| **5. Résultats Data pour la démonstration finale** | Quatre API Data testées localement, exposant les résultats calculés de détection, classification, prévision et analyse cross-market ; résultats et sources disponibles pour le prototype Tech. |

## 1 — Code, données et documentation livrés

Le travail s'appuie sur **Google Trends et Wikipédia**. La préparation produit notamment **12 690 observations Wikipédia exploitables pour M1**, **1 786 observations Google Trends pour le pilote M1** et **12 784 observations mensuelles, réparties en 136 séries géographiques et 30 sujets alimentaires**, pour M3/M4. Ces ensembles couvrent des usages différents : ils ne doivent pas être additionnés.

| Composant | Ce qui a été réalisé | Preuve principale |
|---|---|---|
| **M1 — Détection** | Détecteur statistique avec Z-score robuste, MAD et croissance ; **56 alertes candidates** sur le pilote Google Trends. | `m1_detector/`, `lot02_google_trends/` |
| **M2 — Classification** | Trois modèles comparés : régression logistique, Random Forest et XGBoost ; candidat Random Forest enregistré. | `m2_classifier_v2/artifacts/comparison_v2/` |
| **M3 — Prévision** | Quatre méthodes comparées : Last Value, Ridge, Holt amorti et Seasonal Naive ; prévisions à 3 mois et analyse par fenêtres glissantes. | `m3_forecasting/` |
| **M4 — Cross-market** | Chronologie des signaux de hausse par pays ; **104 séries présentant un signal** et **22 aliments comparables entre plusieurs pays**. | `m4_crossmarket/` |
| **M5 — RAG** | Prototype de recherche documentaire et génération de réponses avec sources, documenté dans le dépôt. | `m5_rag_prototype/`, `benchmark_llm.pdf` |

Le pôle Data & ML travaille sur des **indices statistiques agrégés**, sans recourir à des données individuelles identifiables dans ces modèles, conformément au principe de minimisation des données du RGPD.

## 2 — Reproduction des résultats

**Environnement :** Python 3.11+ ; essais conduits sous Python 3.12. Chaque module possède ses dépendances et son README. Les résultats de référence sont archivés dans ses répertoires `artifacts/`, avec les métriques et les fichiers de provenance.

```bash
# Cloner le dépôt et rejoindre les modules
 git clone https://github.com/Hetic-Hackathon-Givaudan-2026-Groupe-22/example-rag.git
 cd example-rag/sillage-ml
 python -m venv .venv
 source .venv/Scripts/activate
```

**Exécuter les tests** (installer les dépendances du module concerné avant l'exécution) :

```bash
(cd lot01_wikipedia_cleaning && python -m unittest discover -s tests -v)
(cd lot02_google_trends && python -m pytest -q)
(cd m1_detector && python -m pytest -q)
(cd m2_classifier_v2 && python -m pip install -r requirements-comparison.txt && python -m pytest -q)
(cd m3_forecasting && python -m pytest -q)
(cd m4_crossmarket && python -m pytest -q)
```

**Rejouer les calculs depuis les jeux de données préparés :**

```bash
# Dans sillage-ml/m3_forecasting
python -m sillage_m3.run_rolling \
  --input data/processed/m3_30_foods_geo_2019_2026.csv \
  --out artifacts/reproduction_m3_v03

# Dans sillage-ml/m4_crossmarket
python -m sillage_m4.run \
  --input data/processed/m3_30_foods_geo_2019_2026.csv \
  --out artifacts/reproduction_m4_v01
```

**Tester les API :** M1 `sillage.api:app` (port 8003), M2 `sillage_v2.api:app` (8004), M3 `sillage_m3.api:app` (8005), M4 `sillage_m4.api:app` (8006). Chaque module possède son mode de lancement exact et ses variables de sélection d'artefacts dans son README. La documentation interactive est accessible sur `/docs` après démarrage local.

Les **données préparées, artefacts enregistrés, métriques et tests** sont livrés. Les exports sources bruts conservés en dehors de GitHub pour les droits de redistribution sont distincts du jeu préparé publié : la reproduction des résultats enregistrés et la réextraction de toutes les sources depuis l'origine sont deux opérations différentes.

## 3 — Comparaison V1 mardi / V2 jeudi et métriques

**Historique Git vérifié :** [commit V1 du mardi 10 novembre (`21930115`)](https://github.com/Hetic-Hackathon-Givaudan-2026-Groupe-22/example-rag/tree/21930115f5) → [commit V2 du jeudi 12 novembre (`78fd84b`)](https://github.com/Hetic-Hackathon-Givaudan-2026-Groupe-22/example-rag/tree/78fd84b288). Le passage à V2 a ajouté **181 fichiers Data & ML** sous `sillage-ml/`, en préservant les fichiers du prototype RAG de mardi.

| Dimension | V1 — mardi 10/11 | V2 — jeudi 12/11 |
|---|---|---|
| **Démonstrateur** | Prototype RAG et contrat OpenAPI ; score de démonstration simulé. | Modules Data & ML exécutables et résultats calculés. |
| **Données** | Histoire fictive et questions de benchmark RAG. | Jeux Google Trends/Wikipédia nettoyés et données géographiques préparées. |
| **Fonctions** | Recherche documentaire et réponses LLM ; contrat de score. | Détection, classification, prévision à trois mois et cross-market, avec API dédiées. |
| **Validation** | Benchmark RAG et tests du démonstrateur. | Comparaison ML, backtests, métriques, tests et rapports de validation. |
| **Livraison** | Fichiers RAG, OpenAPI et démonstrateur. | Code, données préparées, modèles, API, sorties, tests, PDF et documentation. |

**Résultats mesurés de la V2 :**

| Résultat | Mesure publiée |
|---|---|
| **M1** | 56 alertes candidates sur 1 786 observations Google Trends (19 séries). |
| **M2 — régression logistique** | 28/30 classifications correctes ; F1 macro 0,933. |
| **M2 — Random Forest** | **29/30** classifications correctes ; **F1 macro 0,967** en validation Leave-One-Topic-Out rétrospective. |
| **M2 — XGBoost** | 27/30 ; F1 macro 0,900. |
| **M3 — Last Value** | MAE 7,6517 (sélection), 10,9743 (holdout). |
| **M3 — Seasonal Naive** | MAE holdout 10,1593 ; meilleure MAE que Last Value sur ce holdout. |
| **M3 — diagnostic temporel** | 11 288 états calculés ; 408 prévisions inchangées entre v0.2 et v0.3. |
| **M4** | 104 séries avec hausse détectée ; 22 aliments comparables entre au moins deux pays. |

**Lecture des métriques :** mardi, le benchmark mesure la performance du RAG ; jeudi, M2 mesure la classification et M3 la prévision. Ces mesures sont chacune présentées dans leur unité et leur protocole : la progression V1→V2 est une **extension vérifiable des fonctionnalités et des résultats mesurés**, pas un pourcentage de progression artificiel.

Preuves : `m2_classifier_v2/artifacts/comparison_v2/metrics_v2.json`, `m3_forecasting/artifacts/m3_30_aliments_v02/metrics_m3.json`, `m4_crossmarket/artifacts/m4_v01/metrics_m4.json` et les rapports de module.

## 4 — Analyse des limites et des biais

Ces points identifient les **conditions de lecture des résultats et les améliorations prioritaires** du système ; les modèles, API et expérimentations présentés ci-dessus ont bien été réalisés.

| Sujet | Constat scientifique | Suite méthodologique |
|---|---|---|
| **Couverture des données** | Google Trends et Wikipédia mesurent principalement l'attention, non les ventes ; les sources couvrent une partie des usages consommateurs. | Enrichissement des données, diversification des sources autorisées. |
| **Indices relatifs** | Les séries Google Trends sont normalisées par requête et fenêtre ; leurs niveaux ne sont pas des volumes comparables entre pays. | Conservation des requêtes, pays, dates et scopes de normalisation. |
| **Validation de M2** | Référentiel de 30 cas, labels à consolider et trajectoires évaluées a posteriori. | Référentiel métier élargi et validation prospective à date fixe. |
| **Prévision M3** | Les backtests mesurent la qualité sur les périodes étudiées ; v0.3 ajoute du diagnostic sans changer la précision des prévisions. | Évaluation continue sur de nouvelles périodes et nouveaux ingrédients. |
| **Chronologie M4** | Les décalages détectés décrivent des hausses relatives, pas une causalité entre pays. | Revue métier de chronologies et analyse de sensibilité. |
| **RAG M5** | Le premier corpus utilisé est une histoire fictive : il valide le mécanisme du prototype documentaire. | Extension vers un corpus alimentaire documenté et vérification des réponses sourcées. |

## 5 — Contribution Data à la démonstration finale

**La chaîne de valeur démontrée par la Data** repose sur quatre résultats accessibles via les API :

1. **Détecter** les premiers signaux d'émergence dans les séries d'intérêt.
2. **Qualifier** la trajectoire historique comme buzz ou tendance durable.
3. **Anticiper** les indices d'intérêt à un horizon de trois mois.
4. **Comparer** l'apparition relative des signaux entre marchés.

La couche RAG illustre la possibilité de restituer ces analyses sous forme d'explications documentées. **Le pôle Data a livré les services et sorties nécessaires à la démonstration du prototype Tech**, avec une documentation Swagger et des artefacts mesurés. Le dépôt conserve également le démonstrateur simulé de mardi, séparément des API Data alimentées par les calculs de jeudi.

### Accès direct aux preuves

- [Dossier des livrables Data & ML](https://github.com/Hetic-Hackathon-Givaudan-2026-Groupe-22/example-rag/tree/main/sillage-ml)
- [Diff Git V1 mardi → V2 jeudi](https://github.com/Hetic-Hackathon-Givaudan-2026-Groupe-22/example-rag/compare/21930115f5...78fd84b288)
- [PDF de validation du jeudi 12/11](https://github.com/Hetic-Hackathon-Givaudan-2026-Groupe-22/example-rag/blob/main/sillage-ml/docs/Sillage_G22_Validation_Data_ML_12-11-2026.pdf)
- [M2 : métriques détaillées](https://github.com/Hetic-Hackathon-Givaudan-2026-Groupe-22/example-rag/blob/main/sillage-ml/m2_classifier_v2/artifacts/comparison_v2/metrics_v2.json)
- [M3 : métriques de forecasting](https://github.com/Hetic-Hackathon-Givaudan-2026-Groupe-22/example-rag/blob/main/sillage-ml/m3_forecasting/artifacts/m3_30_aliments_v02/metrics_m3.json)
- [M4 : rapport cross-market](https://github.com/Hetic-Hackathon-Givaudan-2026-Groupe-22/example-rag/blob/main/sillage-ml/m4_crossmarket/RAPPORT_M4_V01.md)
- [M5 : prototype RAG](https://github.com/Hetic-Hackathon-Givaudan-2026-Groupe-22/example-rag/tree/main/sillage-ml/m5_rag_prototype)
