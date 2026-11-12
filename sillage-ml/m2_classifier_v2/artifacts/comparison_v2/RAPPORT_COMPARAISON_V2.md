# Sillage — Comparaison M2 V2 (exploratoire)

**Données :** 30 aliments, 15 buzz / 15 tendances, label pistache PROVISOIRE.

**Méthode :** Leave-One-Topic-Out, prétraitement appris dans chaque fold, hyperparamètres prédéfinis ; mêmes 7 features pour les trois modèles.

| Modèle | Corrects | Accuracy | F1 macro | Erreurs |
|---|---:|---:|---:|---|
| Logistic Regression | 28/30 | 0.933 | 0.933 | butter_board, dubai_chocolate |
| Random Forest | 29/30 | 0.967 | 0.967 | dubai_chocolate |
| XGBoost | 27/30 | 0.900 | 0.900 | butter_board, dubai_chocolate, whipped_lemonade |

**Candidat technique :** Random Forest. Une sélection sur le même jeu n'est pas une validation indépendante.

## Sensibilité : exclure pistache

- Logistic Regression : 27/29 ; F1 macro 0.931
- Random Forest : 28/29 ; F1 macro 0.965
- XGBoost : 26/29 ; F1 macro 0.897

## Limitations

- M2 caractérise des trajectoires complètes 2019–2026 : AUCUNE prédiction pré-pic validée.
- Les labels ont été fournis par l'équipe, non vérifiés indépendamment.
- Le label tendance de pistachio est PROVISOIRE (hypothèse de travail).
- La normalisation Google Trends de pistachio P0 diffère de l'historique de référence.
- Choisir le meilleur des 3 sur ces mêmes 30 cas introduit un biais de sélection.
- Les scores retournés par les modèles ne sont pas des probabilités calibrées.
- La taille n=30 rend l'incertitude importante ; les mois ne sont pas des exemples indépendants.
- Les sujets ont été choisis par l'équipe et peuvent être particulièrement faciles à séparer a posteriori.
- WORLD est exclu ; whipped_lemonade n'a qu'un seul pays exploitable.
- Les features incluent des mois futurs par rapport à une date historique T éventuelle.

## Fichiers de preuve

- `comparaison_par_sujet.csv` : prévisions comparables par sujet
- `predictions_*.csv` : OOF de chaque modèle
- `metrics_v2.json` : scores et matrices de confusion
- `manifest_comparison_v2.json` : version, paramètres et SHA256 de la source
- `model_v2.joblib` : modèle entier sélectionné sur 30 sujets (à ne charger que depuis une source fiable)
- `predictions_30_oof.csv` : OOF du modèle retenu pour l'API
