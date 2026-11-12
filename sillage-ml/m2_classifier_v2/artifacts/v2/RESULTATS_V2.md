# Sillage — Evaluation expérimentale M2 V2

- Données : **30 sujets**, dont **29 alimentaires évalués** ; ['oud'] hors scope.
- Validation : **Leave-One-Topic-Out** (un sujet entièrement absent de son entraînement).
- Labels : **provisoires, non vérifiés par une revue historique indépendante**.

## Comparaison

| Métrique | Logistic Regression | Toujours buzz |
|---|---:|---:|
| Accuracy | 0.931 | 0.517 |
| Balanced accuracy | 0.931 | 0.500 |
| Macro F1 | 0.931 | 0.341 |
| ROC-AUC | 0.995 | 0.500 |

## Limites

- Classification RETROSPECTIVE de signatures 2019-2026, PAS prévision à date historique.
- Labels buzz/tendance fournis mais NON vérifiés indépendamment : métriques exploratoires.
- 29 sujets alimentaires seulement ; 30e oud (parfumerie) exclu des métriques.
- Whipped lemonade: 1 seul pays disponible ; profil exploité à titre exploratoire avec couverture faible.
- Même indicateur Google Trends ne permet pas la comparaison des volumes absolus entre pays.
- Séries rééchelonnées sur la fenêtre complète ; données futures présentes dans les features rétrospectives.
- Score logistique non calibré : ne pas l’appeler probabilité métier ni confiance validée.
- Test Leave-One-Topic-Out évite fuite du même sujet entre apprentissage et test mais non les biais de sélection des sujets.
- Vérifier les requêtes et les exports API Google Trends, ainsi que les labels, avant toute validation scientifique.
