# SILLAGE G22–Auralis — Lot 02 : audit & intégration Google Trends dans M1

**Date : 12 novembre 2026**  
**Objectif : rendre utilisable la nouvelle collecte sans écraser le pipeline M1 Wikipédia.**

## Résumé vérifié

| Fichier brut | Lignes | Usage |
|---|---:|---|
| `google_trends_lot_P0_2019_2026.csv` | 2 068 | M1/M3/M4 : Google Trends pilote |
| `reference_30_cas_google_trends_2019_2026.csv` | 15 604 | M2 : 30 sujets labellisés, à revoir avant validation |
| `wikipedia_attention_documentaire_2019_2026.csv` | 11 776 | M1 documentaire, et preuves limitées ; **langue ≠ pays** |
| `prix_matieres_2019_2026.csv` | 279 | Contexte économique uniquement ; différentes unités |
| **TOTAL** | **29 727** | Ces lignes ne sont pas des exemples statistiquement indépendants. |

La préparation extrait **1 786 observations mensuelles M1 par pays**, sur **19 séries** (= 4 sujets × pays couverts), et **282 observations de comparaison mondiale** dans un fichier distinct. Les **30 sujets** de référence ont **15 labels `buzz`** et **15 labels `tendance`**, avec **166 séries sujet × zone** ; `oud` est hors du périmètre alimentaire du pilote (reste 29 sujets alimentaires dans cette nomenclature).

Un run du détecteur existant **M1-statistical-baseline-0.3.0** a été exécuté sur les 1 786 observations géographiques et a produit **56 alertes candidates** dans 19 séries. Les alertes ne sont **pas** une mesure de précision : elles n'ont pas de label indépendant « émergence à la date t ». Les paramètres par défaut sont `history_window=12` mois, `growth_lag=4`, `z>=3`, `growth>=25%`, `cooldown=4`. Ce sont des seuils exploratoires, non calibrés.

## Plan des fichiers

```text
Sillage_Lot02_GoogleTrends_Integration/
  data/raw/                      # copies exactes des 4 fichiers reçus
  data/clean/
    google_trends_p0_M1_pays.csv # 1786 lignes, contrat M1 valide
    google_trends_p0_WORLD_separe.csv # 282 lignes mondiales, hors API 'country'
    reference_30_sujets_labels_A_REVOIR.csv # 30 lignes, labels provisoires
  reports/
    audit_lot02.json             # compteurs + SHA-256 des sources
    comparaison_p0_vs_reference.csv  # différences et requêtes non homogènes
    reference_30_series_qualite.csv # 166 résumés de séries
  artifacts/google_trends/lot02_P0_M1_statistical_v03/
    cleaned.csv, features.csv, signals.json, signals.csv,
    series.json, quality.json, manifest.json,
    evaluation_status.json
  scripts/prepare_lot02.py      # préparation reproductible, bibliothèque Python standard
  tests/test_lot02.py           # six contrôles complémentaires
```

## Utilisation dans VS Code sous Windows / Git Bash

**1.** Extraire ce ZIP à côté de ton dossier `Sillage_M1_Wikipedia_V03`, dans `C:\Users\VOTRE_UTILISATEUR\Projects\Givaudan\`. Ne fusionne pas les dossiers.

**2.** Activer l'environnement Python déjà créé :

```bash
cd ~/Projects/Givaudan/Sillage_Lot02_GoogleTrends_Integration
source ../sillage_pipeline_m1_v02/.venv/Scripts/activate
python scripts/prepare_lot02.py
python -m unittest discover -s tests -v
```

Résultat vérifié ici : **6 tests du lot 02 OK**. Les **12 tests de la version M1 v0.3** avaient également réussi dans l'environnement d'exécution.

**3.** Pour rejouer M1 avec un répertoire horodaté (ne pas écraser les artefacts) :

```bash
cd ~/Projects/Givaudan/Sillage_M1_Wikipedia_V03
RUN_DIR="artifacts/google_trends/lot02_$(date +%Y%m%d_%H%M%S)"
python -m sillage.pipeline \
  --input ../Sillage_Lot02_GoogleTrends_Integration/data/clean/google_trends_p0_M1_pays.csv \
  --out "$RUN_DIR" --frequency monthly
export SILLAGE_ARTIFACT_DIR="$RUN_DIR"
uvicorn sillage.api:app --port 8003
```

**4.** Pour tester l'API immédiatement **sans recalculer** (les sorties du lot sont déjà dans ce ZIP), depuis `Sillage_M1_Wikipedia_V03` :

```bash
export SILLAGE_ARTIFACT_DIR="../Sillage_Lot02_GoogleTrends_Integration/artifacts/google_trends/lot02_P0_M1_statistical_v03"
uvicorn sillage.api:app --port 8003
```

Swagger : <http://127.0.0.1:8003/docs> — endpoints `/health`, `/model`, `/quality`, `/signals`, `/series`. L'API retourne **56 alertes candidates calculées sur les vrais fichiers P0 déclarés**, et non un tableau fictif. `GET /signals?ingredient=matcha&country=FR` retourne **6 alertes candidates** dans le lot. **Ne pas attribuer à ces scores une probabilité calibrée de durabilité.**

## Limitations prioritaires et règles scientifiques

1. **Les labels `buzz/tendance` ne sont pas vérifiés indépendamment.** Le fichier de référence étiquette **30 sujets**, pas 15 604 cas indépendants ; chaque sujet partage son label entre toutes ses zones et dates. Évaluer M2 uniquement après validation documentaire des labels ; faire les splits **par sujet** (pas lignes aléatoires) et ne pas revendiquer de performance robuste sur ce petit nombre d'exemples.
2. **Les 30 labels M2 ne valident pas M1.** Il manque des références **(sujet, pays, date d'émergence et négatifs)** pour calculer précision/rappel/délai de M1. C'est expliqué dans `evaluation_status.json`.
3. **Les exports P0 et référence ne sont pas interchangeables.** Certains portent sur des requêtes localisées, d'autres en anglais ; la normalisation Google Trends diffère (P0 2019–2026 et référence 2014–2026). Le rapport `comparaison_p0_vs_reference.csv` fournit les écarts constatés. Ne **jamais concaténer** ces séries dans un seul historique sans remappage validé.
4. **La rééchelonnage sur toute une fenêtre temporelle peut créer une information rétrospective** pour le backtesting. Si vous simulez une décision en 2022, la série exportée jusqu'en 2026 a été normalisée avec le maximum futur. Pour une simulation prospective stricte, faire des exports « à date de décision », gérer les effets d'échelle et évaluer sur des horizons glissants.
5. **Les indices 0–100 ne sont pas des volumes absolus ni des ventes** et des valeurs différentes entre pays n'impliquent pas des volumes comparables. Pour M4, analyser le décalage temporel et les changements relatifs **sans attribuer de causalité** ; valider l'équivalence sémantique des requêtes multilingues.
6. **Les données Wikipédia sont par édition linguistique**, pas par pays. Ne pas joindre `fr.wikipedia` à `FR` comme preuve géographique.
7. **Les prix ne mesurent pas directement la demande.** La série `WPU01190106` (pistaches) est un **PPI américain en indice base décembre 1991**, pas un prix d'achat en USD/tonne ; elle est fréquemment constante sur de longs segments. Ne pas mélanger ces unités ni traiter la répétition comme une progression mensuelle du prix.
8. Les 4 fichiers transmis contiennent des `source_url` et des chemins `raw_file`, mais **pas les fichiers d'export originaux mentionnés par ces chemins**. Conserver les exports originaux, les captures de paramètres et le dictionnaire de requêtes chez le Tech pour pouvoir auditer la collecte.
9. L'attribut `is_synthetic=False` **est déclaré dans le fichier**, mais il ne prouve pas à lui seul l'authenticité externe. Les lignes reçues sont traitées comme des données collectées revendiquées réelles, dont la provenance est à contrôler par échantillonnage.
10. Le RAG a besoin de **contenu documentaire** (textes d'articles/rapports autorisés, dates, URLs), pas seulement d'URLs d'index ; le corpus complet n'est pas fourni par ces quatre CSV.

## Priorités pour la suite

- **M1** : revue des 56 alertes candidates ; construire des cas de référence indépendants et négatifs, puis calibrer les seuils.
- **M2** : revoir les 30 labels, retirer `oud` pour le pilote alimentaire, puis tester un classifieur simple en validation groupée par sujet ; ne pas prétendre avoir 15 604 observations indépendantes.
- **M3** : tester des baselines de prévision à horizon 3 et 6 mois avec backtesting temporel.
- **M4** : commencer avec décalages d'apparition pour matcha, pistache, Dalgona, Dubai chocolate, avec vérification des requêtes multilingues et de la normalisation.
- **API/Tech** : conserver `country`, `normalization_scope`, `source`, `data_version` et la provenance dans toute réponse ; exposer les résultats calculés seulement.

**Protocole de qualité :** garder les fichiers bruts intacts, versionner chaque run dans son répertoire, enregistrer les hashes SHA-256 et ne pas écraser les anciens artefacts Wikipédia.
