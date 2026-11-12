# Protocole scientifique — Sillage M2 V2

## Ce qui a été réellement évalué

- 30 sujets dans le référentiel, mais 29 sujets alimentaires retenus : 15 buzz et 14 tendances ; Oud non évalué.
- Une observation supervisée = **un sujet**, pas un mois, un pays ni une ligne de CSV.
- Trajectoires mensuelles 2019-01 → 2026-10 ; cinq pays maximum ; WORLD ignoré.
- Sept caractéristiques résumant la trajectoire complète, agrégées par médiane entre pays.
- Modèle `StandardScaler` et régression logistique L2 (`C=0.3`), hyperparamètres fixes avant l'évaluation.
- Leave-One-Topic-Out = 29 entraînements/évaluations, sujet de test absent des données d'apprentissage de chaque fold.
- Résultats : accuracy 27/29 ; F1 macro 0,931 ; TN=14, FP=1, FN=1, TP=13 ; baseline constante toujours buzz F1 macro 0,341.

## Ce qui reste NON évalué

- Labels indépendants et définitions objectives du statut « durable » (p. ex. intérêt soutenu à +6 ou +12 mois après une date d'alerte).
- Performance prospective du score après détection M1 (à date t).
- Robustesse à l'échantillonnage Google Trends, au scope de normalisation et au choix des requêtes multilingues.
- Comportement sur d'autres ingrédients non présélectionnés.
- External validation on new data and true confidence calibration.

## Protocole recommandé pour V2.1

1. Faire vérifier les 30 cas par des annotateurs métier, avec dates, critères et preuves. Remplacer Oud par un sujet alimentaire.
2. Définir pour chaque cas une **date de décision t**, calculer les features uniquement avec des observations disponibles à t et construire une étiquette fondée sur ce qui arrive après t, dans une fenêtre d'horizon fixe.
3. Si Google Trends est renormalisé avec un maximum futur, obtenir des exports historiques reconstitués à la date t ou des extractions horodatées ; sinon signaler le biais rétrospectif.
4. Mesurer à chaque horizon précision, rappel, F1, Brier score, courbe ROC-AUC et comparatif avec une baseline naïve, sans utiliser le même sujet de part et d'autre du split.
5. Enrichir la collection : 29 cas suffisent pour une démonstration, pas pour garantir les performances d'un classifieur généralisable.

**Règle d'affichage produit :** afficher « classement expérimental » ; pas « probabilité de succès » ou « tendance prouvée ».
