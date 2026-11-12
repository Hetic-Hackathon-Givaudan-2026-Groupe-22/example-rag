# Fiche modèle — Sillage M2 V2 (comparaison exploratoire)

**Version** : `2.1.0-comparison-experimental` — 12/11/2026.  
**Tâche** : classification rétrospective de signatures de recherches alimentaires `buzz` / `tendance`.  
**Équipe responsable** : Équipe G22 / Auralis — pôle Data & ML ; collecte réalisée par le pôle Data. Contributions détaillées dans le journal Git et les tickets du projet.  
**Statut** : première livraison expérimentale, pas modèle métier validé.

## Entrées et features

- Google Trends, séries 2019–2026, 30 sujets alimentaires, jusqu'à 5 pays plus WORLD (exclu).
- Sept caractéristiques agrégées par sujet : concentration au pic, maintien d'intérêt récent, fraction de mois actifs, durée continue active, gain récent vs début, stabilité, intérêt récent vs quantile historique.
- Label `tendance` de pistache non confirmé ; requêtes linguistiques et fenêtres de normalisation hétérogènes.

## Modèles préspécifiés

- Logistic Regression : StandardScaler dans chaque fold ; C=0,3, pondération balanced.
- Random Forest : 200 arbres, profondeur max 3, minimum 2 observations par feuille, équilibrage des classes.
- XGBoost : 80 estimateurs, profondeur 2, learning rate 0,05, régularisation L2=2.
- Seed 42 ; les paramètres sont dans `sillage_v2/compare_models.py`.

## Évaluation

Leave-One-Topic-Out, 30 folds. Chaque sujet apparaît exactement une fois en test hors entraînement. Sur l'ensemble de trajectoires rétrospectives, les F1 macro sont 0,933, 0,967 et 0,900. Le meilleur candidat technique est Random Forest avec 29/30 sujets corrects. La classe Tendance est codée 1.

Un cas de test indépendant **ne fait pas partie** de cette livraison ; une sélection du meilleur de trois modèles sur la même petite base peut surestimer sa qualité. La baseline `toujours buzz` a un F1 macro de 0,333.

## Utilisation autorisée et interdite

**Approprié** : démontrer la chaîne de calcul ML, examiner les erreurs, comparer les algorithmes et brancher un prototype de test.

**Non approprié** : affirmer que ce modèle détecte avant le pic, qu'il prédit la demande commerciale ou que le score est une probabilité calibrée ; l'utiliser pour des décisions d'achat sans validation indépendante.

## Étapes restantes

1. Collecter un 30e cas alimentaire documenté de manière homogène et valider toutes les étiquettes.
2. Réextraire les séries sur fenêtres de normalisation cohérentes et documenter les termes multilingues.
3. Figurer une date T et construire des features **uniquement disponibles avant T**.
4. Mesurer les performances avec une séparation temporelle indépendante, avec incertitude et revue des erreurs.
5. Publier les artefacts autorisés sur la branche projet puis intégrer l'API avec le Tech.
