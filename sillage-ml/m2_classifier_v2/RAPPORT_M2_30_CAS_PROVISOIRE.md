# Sillage — expérimentation M2 sur 30 aliments (PROVISOIRE)

**Date : 12/11/2026 | Ne pas annoncer comme benchmark prospectif validé.**

## Origine des données
- Référentiel original conservé : 30 sujets dont `oud` (parfum) = 29 aliments exploitables.
- Copie expérimentale : `oud` remplacé par `pistachio` (pistache), déjà présent dans `google_trends_lot_P0_2019_2026.csv` fourni par Joseph.
- 564 observations pistache, dont 470 observations pays (FR, US, JP, KR, AE) et 94 WORLD ; valeurs copiées sans interpolation.
- 30 sujets alimentaires distincts : 15 étiquetés buzz et 15 étiquetés tendance ; label pistache attribué **provisoirement**.

## Résultat exploratoire Leave-One-Topic-Out
- Logistic Regression (StandardScaler, C=0.3, class_weight=balanced, random_state=42).
- **30 sujets** évalués, **28/30** correctement classés, **F1 macro 0.933**.
- Baseline constante `buzz` : F1 macro 0.333.
- Erreurs : `butter_board`, `dubai_chocolate`.
- 16 tests Python réussis ; API FastAPI contrôlée à HTTP 200 (health, metrics, references, pistachio).

## Ce que cela ne démontre PAS
1. L'étiquette pistache n'a pas été vérifiée indépendamment. Les autres labels non plus.
2. **Normalisation différente** : P0 pistache export 2019–2026, alors que les autres séries de référence viennent d'un export 2014–2026 tronqué à 2019–2026. L'indice n'est pas automatiquement comparable.
3. Le modèle voit toute la trajectoire 2019–2026 et **ne prédit pas** à date T qu'une tendance sera durable dans six mois.
4. La collecte et les labels ont été choisis par l'équipe ; les 30 cas ne forment pas un test externe aveugle.

**Action pour Joseph/Tech** : confirmer la classe de pistache et harmoniser son export Google Trends (mêmes plages de dates et paramètres que les 29 autres sujets). Conserver la version initiale 29-cas pour la comparaison historique.
