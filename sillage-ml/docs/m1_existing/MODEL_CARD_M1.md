# Fiche de modèle — Sillage M1 (baseline statistique v0.3.0)

**Modèle :** `M1-statistical-baseline-0.3.0`  
**Tâche :** détection d'augmentation inhabituelle d'intérêt, par sujet et par série de référence.  
**Nature :** méthode statistique non entraînée ; **pas un classifieur buzz/durable, pas un forecast**.

## Entrée

Colonnes obligatoires (Google Trends): `ingredient`, `country` ISO2, `date`, `source`, `metric`, `value`, `normalization_scope`, `is_synthetic`, `source_url`.

Fréquence **mensuelle**, valeur Google Trends 0–100, pays FR/US/JP/KR/AE. La clé de série inclut les dimensions et le périmètre de normalisation ; les séries `WORLD` sont séparées. Pour Wikipédia, adapter la clé à `wiki_project` sans inventer un pays.

## Features et décision

- Niveau de référence issu des données antérieures (historique glissant de **12 mois**).
- Score d'écart robuste par rapport à la médiane passée (`robust_z`).
- Croissance calculée sur **4 mois** (`growth_lag=4`).
- Détection quand `robust_z >= 3` **et** `growth >= 0.25` ; *cooldown* **4 mois** après alerte.
- Manques / irrégularités temporelles : ne pas remplir par zéro ; certaines séries sont exclues ou découpées en séquences continues.

Ces paramètres sont **exploratoires** : ils n'ont pas été optimisés sur des cas de référence indépendants.

## Résultats archivés

| Jeu | Observations M1 | Séries | Alertes candidates |
|---|---:|---:|---:|
| Wikipédia, par édition linguistique | 12 690 | 115 | 450 |
| Google Trends P0, par pays | 1 786 | 19 | 56 |

**Métriques prédictives : aucune à ce stade.** Le nombre d'alertes ne mesure ni précision, ni rappel, ni F1. `evaluation_status.json` indique pourquoi le référentiel des 30 labels M2 ne permet pas de valider M1.

## Architecture d'exécution

`load_and_clean` → `detect` → `publish`, avec `manifest.json`, `quality.json`, `features.csv`, `signals.json/csv`, `series.json` conservés par lot. `sillage.api:app` sert les artefacts du run choisi via `SILLAGE_ARTIFACT_DIR`, sans créer des prédictions dans l'endpoint.

## Risques et limites

1. **Fuite informationnelle liée aux données sources :** les features n'utilisent pas des lignes futures dans les tests unitaires, mais les indices Google Trends téléchargés sur une fenêtre allant jusqu'en 2026 peuvent être rééchelonnés par rapport au maximum de cette fenêtre. Pour un backtest historique strict, obtenir des séries « à date de décision » ou évaluer soigneusement cet effet.
2. **Comparabilité cross-market :** deux indices égaux ne représentent pas des volumes absolus égaux ; vérifier la sémantique des requêtes locales, les délais et les effets d'échelle.
3. **Dépendance à la source :** les recherches Google et les vues Wikipedia mesurent l'attention, pas les ventes / l'innovation réellement commercialisée.
4. **Alertes nombreuses :** contrôler les faux positifs sur cas documentés, avec négatifs et seuils gelés avant le test final.
5. **Labels :** absence actuelle de vérité terrain événement-date-pays pour M1. Ne pas réutiliser les labels M2 par sujet comme vérité terrain M1.

## Versionnement et attribution

Version du modèle dans chaque `manifest.json` ; sources sha256 dans rapports. Une version ultérieure « V2 évaluée » devra publier son protocole, ses références indépendantes, un rapport d'erreurs, et ses métriques, sans écraser cette baseline.
