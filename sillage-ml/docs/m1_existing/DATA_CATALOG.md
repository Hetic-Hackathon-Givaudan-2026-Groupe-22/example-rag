# Catalogue Data — Sillage

## Lot 01 : Wikipédia / attention documentaire

Source reçue : `observations_wikipedia.parquet` (15 212 observations). Après contrôle : **12 690 observations M1 admissibles**, **2 522 en quarantaine**. Documents principaux :

- `lot01_wikipedia_cleaning/output/m1_wikipedia_contract.csv` : format M1 prêt à charger (clé `ingredient`, `segment_type=wiki_project`, `segment_id`, `date`, `value`, `source`, `metric`, `source_url`).
- `lot01_wikipedia_cleaning/output/observations_quarantine.csv` : lignes écartées du lot M1, conservées avec statut.
- `lot01_wikipedia_cleaning/output/series_quality_recomputed.csv` et `quality_summary.json` : couverture et motifs.
- `lot01_wikipedia_cleaning/output/processing_manifest.json` : empreintes et paramètres du nettoyage.

**Ne jamais remplacer `fr.wikipedia` par `FR`.** Le pays d'un lecteur n'est pas identifiable par l'édition linguistique.

## Lot 02 : Google Trends P0 / géographie

| Fichier préparé | Colonnes principales | Lignes | Utilisation |
|---|---|---:|---|
| `lot02_google_trends/data/clean/google_trends_p0_M1_pays.csv` | ingredient, country, source, metric, normalization_scope, date, value, is_synthetic, source_url | **1 786** | M1 national, futures analyses cross-market sous conditions |
| `lot02_google_trends/data/clean/google_trends_p0_WORLD_separe.csv` | ingredient, segment_type, segment_id, normalization_scope, date, value, ... | **282** | Contexte mondial, pas une série « pays » |
| `lot02_google_trends/data/clean/reference_30_sujets_labels_A_REVOIR.csv` | topic_id, reference_label, zones, n_observations, review_required, status... | **30** | Préparation M2 uniquement, labels provisoires |

**Grain M1 :** 1 ligne = 1 sujet × 1 pays × 1 mois × 1 source/métrique × 1 périmètre de normalisation. Pas de duplication de dates par clé ; 19 séries nationales. Pays observés : **AE, FR, JP, KR, US**.

Google Trends est un **indice relatif**. Les requêtes multilingues et fenêtres de normalisation diffèrent entre P0 et le référentiel historique (2014–2026) : aucun collage direct des séries. Les flags `inferieur_a_1` requièrent un traitement explicite avant des prévisions sensibles.

## Autres sources du lot reçu (non intégrées comme features M1)

- Wikipédia additionnel 2019–2026 : 11 776 observations ; langue ≠ pays ; corpus documentaire RAG non fourni.
- Prix matières 2019–2026 : 279 observations / 3 séries ; cacao, café arabica, pistache ; **unités hétérogènes**, pas de concaténation avec l'indice Google.
- Référence : 15 604 observations mensuelles sur **30 sujets** et 166 séries par zone ; les **30 labels** ne constituent pas 15 604 cas indépendants. `oud` = hors pilote alimentaire.

## Traçabilité / intégrité

- `lot02_google_trends/reports/audit_lot02.json` contient SHA-256 des quatre fichiers sources reçus et des fichiers nettoyés.
- `lot02_google_trends/reports/comparaison_p0_vs_reference.csv` documente les écarts de requêtes et d'indices.
- Chaque `artifacts/**/manifest.json` conserve les paramètres et empreintes de l'entrée utilisée par M1.
- Les exports originaux ne sont pas inclus dans cette livraison Git, pour éviter publication non autorisée et doublons ; ils doivent être gardés séparément par l'équipe, avec vérification des droits de redistribution.

## Contrôles qualité exécutés

- Lot 01 : 6 tests nettoyage (doublons, zéro vs absent, faux pays, label leakage, quarantine, compteurs).
- M1 : 12 tests (features temporelles, manque de mois, non-fuite dans la fonction, API sur sorties calculées).
- Lot 02 : 6 tests (pays, WORLD séparé, indices 0–100, provenance, labels 30 sujets, manifest).

**Statut :** contrôles techniques réussis ; validation scientifique des tendances et preuve d'authenticité des sources à poursuivre.
