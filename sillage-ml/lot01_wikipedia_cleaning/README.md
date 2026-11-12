# SILLAGE — G22 Auralis | Lot 01 : Wikipédia, nettoyage et audit v1.1

**Date de collecte consignée :** 12 novembre 2026 (fournie dans la collecte).  
**Fenêtre maximale :** juillet 2015 à octobre 2026. **Granularité :** mensuelle.  
**Périmètre :** signaux d'attention documentaire pour ingrédients / sujets alimentaires, **pas des ventes ni des recherches Google**, et **pas encore une analyse de demande par pays**.

## 1. Résultats vérifiés

| Contrôle | Résultat |
|---|---:|
| Observations reçues et conservées après validation de format | 15 212 |
| Sujets (`topic_id`) | 21 |
| Éditions linguistiques Wikipédia (`wiki_project`) | 10 |
| Séries sujet × édition | 159 |
| Doublons de clé | 0 |
| Valeurs numériques invalides ou négatives | 0 |
| Zéros conservés comme mesures (pas comme manquants) | 81 |
| Séries utilisables **comme proxy Wikipédia pour M1** | **115** |
| Observations dans ces séries | **12 690** |
| Séries à examiner manuellement | 14 (1 065 observations) |
| Séries d'historique trop court / lacunaire | 21 (445 observations) |
| Séries hors pilote alimentaire | 9 (1 012 observations) |
| Données non publiées directement dans le lot M1 (mais conservées en quarantaine) | 2 522 observations |

**Qualification « usable » :** au moins 85 % de couverture mensuelle depuis la première observation jusqu'à octobre 2026 **et** au moins 24 mois consécutifs ; aucune page signalée comme correspondance douteuse et pas de sujet exclu. Ces seuils sont ceux du rapport reçu, pas une validation de l'aptitude à prédire les tendances alimentaires.

## 2. Fichiers livrés

- `raw/` : **copies immuables** des cinq fichiers fournis : Parquet, script d'origine, dictionnaire, manifeste de recherche, rapport qualité. Le CSV `observations_wikipedia_extracted.csv` est une extraction tabulaire vérifiée du Parquet, ajoutée pour faciliter la reproductibilité sans `pyarrow`.
- `code/clean_wikipedia.py` : pipeline auditable et relançable ; vérifie dates, clés, sources, types, doublons, règles d'éligibilité et cohérence du rapport original ; préserve les zéros, pics et trous.
- `output/observations_clean_all.csv` : **15 212 observations validées**, avec leur statut de qualité, y compris les séries mises de côté.
- `output/observations_m1_eligible.csv` : **12 690 observations** du lot retenu pour expérimentation.
- `output/m1_wikipedia_contract.csv` : données M1, colonnes `ingredient`, `date`, `value`, `segment_type`, `segment_id` (édition Wikipédia), `country_iso2` vide, provenance, origine réelle/synthétique. **Ne contient PAS les labels de référence préparatoires**, pour prévenir les fuites.
- `output/observations_quarantine.csv` : **2 522 observations** conservées mais non injectées dans l'essai M1 (correspondance article à vérifier, historique insuffisant, hors périmètre).
- `output/observations_invalid.csv` : lignes techniquement invalides ; vide pour ce lot, en-têtes présents.
- `output/series_quality_recomputed.csv` : indicateurs qualité recomputés par série et concordance avec le rapport original.
- `output/quality_summary.json` : chiffres et limites de ce lot.
- `output/processing_manifest.json` : paramètres, version, horodatage de transformation, **SHA-256** du fichier d'entrée et de chaque sortie — traçabilité des livrables.
- `output/NOTE_QUALITE_ET_LIMITES.md` : synthèse livrable Data.
- `tests/test_cleaning.py` : contrôles automatiques de cohérence, périmètre et non-fabrication des pays.

## 3. Comment relancer sur Windows / VS Code

Dans Git Bash, après avoir extrait **le dossier** dans `~/Projects/Givaudan/` :

```bash
cd ~/Projects/Givaudan/Sillage_Wikipedia_Nettoyage_V1
source ../sillage_pipeline_m1_v02/.venv/Scripts/activate
python -m pip install pyarrow   # seulement si nécessaire pour lire/écrire du Parquet
python code/clean_wikipedia.py --input raw/observations_wikipedia.parquet --out output
python -m unittest discover -s tests -v
```

Si tu ne souhaites **pas** installer `pyarrow` tout de suite, utilise directement le CSV d'extraction inclus :

```bash
python code/clean_wikipedia.py --input raw/observations_wikipedia_extracted.csv --out output
python -m unittest discover -s tests -v
```

La relance réécrit les tables transformées déterministiquement et actualise le manifeste de traitement. **Avant une nouvelle collecte**, copie le dossier complet dans `batches/2026-11-12_wikipedia_v1/` ou versionne-le sur une branche Git, pour conserver l'historique.

## 4. Très important pour Sillage et le cross-market

**`fr.wikipedia` n'est pas `FR` et `ja.wikipedia` n'est pas `JP`.** Ces chiffres indiquent des consultations par édition linguistique, sans géolocalisation de l'utilisateur. `country_iso2` reste volontairement vide. Ne jamais renseigner de pays en devinant depuis la langue.

Le pipeline M1 `sillage_pipeline_m1_v02` actuel **refuse à juste titre les pays vides**. Le fichier `m1_wikipedia_contract.csv` n'est **pas** compatible tel quel avec son contrat `country` : il faut soit adapter un détecteur aux dimensions `segment_type/segment_id`, soit attendre les vraies séries par pays (Google Trends ou autre). Ne PAS remplacer `country` par `wiki_project` pour contourner le contrôle.

Les 4 sujets présents dans `dictionnaire_requetes.csv` concernent la planification **Google Trends** ; ils ne sont pas une liste blanche de la collecte Wikipédia (21 sujets). Les 17 autres sujets Wikipédia n'ont donc pas été supprimés.

Les champs `label_reference` de la source (`buzz`, `tendance`, `a_tester`) correspondent à des annotations préliminaires ; ils ne forment **pas** 30 labels de référence vérifiés. Ils sont absents du fichier M1 de features. Aucune métrique réelle M1, M2 ou cross-market n'a été calculée dans ce lot : c'est un livrable de **nettoyage/qualification uniquement**.

**Limitation de provenance :** le fichier brut amont `data/wikipedia/echantillon_pageviews.csv` cité dans le script d'origine n'était pas parmi les uploads. Le traitement présenté est reproductible **à partir du Parquet fourni**, mais pas jusqu'à la requête API source sans l'export amont. Demander au Tech de conserver cet export et les logs API.

## 5. Passation Tech → Data / Product

1. Conserver le dossier brut daté, ajouter les SHA-256 à l'inventaire du dépôt.
2. Vérifier manuellement `pink_sauce`, `raindrop_cake`, `unicorn_frappuccino` (pages ou homonymes potentiels) ; `oud` est hors périmètre.
3. Pour l'analyse cross-market, obtenir des séries historiques **explicitement géolocalisées**, au même pas de temps et avec le périmètre de normalisation de chaque mesure.
4. Développer un M1 par `wiki_project` **uniquement en tant que signal documentaire**, ou utiliser la collecte géographique pour le M1 principal.
5. Définir et vérifier 30 cas historiques indépendants pour les métriques du modèle : ce lot n'en tient pas lieu.

**Ce lot constitue :** nettoyage documenté + contrôle qualité + contrat préparatoire M1 + données et manifestes réutilisables pour la V2.
