# Sillage — Evaluation expérimentale M2 V2

- Données : **30 sujets**, dont **30 alimentaires évalués** ; [] hors scope.
- Validation : **Leave-One-Topic-Out** (un sujet entièrement absent de son entraînement).
- Labels : **provisoires, non vérifiés par une revue historique indépendante**.

## Comparaison

| Métrique | Logistic Regression | Toujours buzz |
|---|---:|---:|
| Accuracy | 0.933 | 0.500 |
| Balanced accuracy | 0.933 | 0.500 |
| Macro F1 | 0.933 | 0.333 |
| ROC-AUC | 0.996 | 0.500 |

## Limites

- Classification RETROSPECTIVE de signatures 2019-2026, PAS prévision à date historique.
- Labels buzz/tendance fournis mais NON vérifiés indépendamment : métriques exploratoires.
- 30 sujets alimentaires évalués sur 30 références ; exclus: [].
- Whipped lemonade: 1 seul pays disponible ; profil exploité à titre exploratoire avec couverture faible.
- Même indicateur Google Trends ne permet pas la comparaison des volumes absolus entre pays.
- Séries rééchelonnées sur la fenêtre complète ; données futures présentes dans les features rétrospectives.
- Score logistique non calibré : ne pas l’appeler probabilité métier ni confiance validée.
- Test Leave-One-Topic-Out évite fuite du même sujet entre apprentissage et test mais non les biais de sélection des sujets.
- Vérifier les requêtes et les exports API Google Trends, ainsi que les labels, avant toute validation scientifique.
- CAS PISTACHE PROVISOIRE: label tendance proposé par hypothèse de travail, non validé indépendamment ; il ne constitue PAS un cas de test indépendant.
- NORMALISATION NON HOMOGENE: pistache provient du P0 2019-2026, alors que le référentiel historique provient de séries exportées 2014-2026 puis limitées à 2019-2026 ; métriques de comparaison affectées.
