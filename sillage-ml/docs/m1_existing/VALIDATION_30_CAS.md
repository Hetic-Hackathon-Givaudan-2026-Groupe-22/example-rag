# Protocole de validation à réaliser — 30 cas de référence

## 1. Ne pas confondre M1 et M2

**M1, détection d'émergence :** il faut une vérité terrain **par événement** (ingrédient × pays × date de décision). Le fichier actuel « 30 cas » comprend **30 sujets étiquetés buzz/tendance**, pas ces 30 événements. Il ne permet pas de calculer immédiatement F1/precision/recall de M1.

**M2, buzz vs durable :** les 30 labels actuels sont **provisoires**, nécessitent un audit documentaire (sources et critères de persistance), et il n'y a que 29 sujets alimentaires si `oud` est exclu. Ne pas faire un split aléatoire par ligne mensuelle ; grouper par sujet pour éviter la fuite.

## 2. Plan recommandé pour une référence M1 indépendante

Proposer au Product / Tech et aux membres Data **30 situations historiques** documentées avec au moins des **cas sans émergence**. Colonnes proposées (format de travail, non validé actuellement) :

| Champ | Rôle |
|---|---|
| case_id | identifiant stable |
| ingredient, country, source, metric, normalization_scope | clé de série |
| as_of_date | date à laquelle le système aurait eu les données |
| reference_label | 1 = émergence confirmée ; 0 = absence de signal selon critères prédéfinis |
| reference_event_date | début estimé de l'événement, si applicable |
| rationale, source_url | justification externe et provenance |
| reviewer, reviewed_at | validation humaine indépendante |
| label_status | `proposed`, `reviewed`, `disputed` |

Critères écrits **avant** la comparaison au modèle ; échantillonner des négatifs difficiles, des périodes saisonnières, des événements récurrents et des signaux à faible volume. Vérifier indépendamment la correspondance entre le terme recherché et le concept alimentaire.

## 3. Évaluation temporelle

1. Geler les règles de vérité terrain et identifier les dates de décision.
2. Pour chaque cas, ne calculer les features qu'avec les points observables à cette date, en tenant compte des séries Google Trends rééchelonnées a posteriori.
3. Garder des cas séparés pour l'ajustement des seuils et le test final ; si 30 cas seulement, présenter tous les comptages, incertitudes et cas individuels.
4. Mesurer TP, FP, TN, FN ; precision, recall, F1, alertes / série / an, délai de détection. Ne pas rapporter des métriques non définies (division par zéro).
5. Joindre les faux positifs/négatifs, preuves et versions d'artefacts.

## 4. Livrables visés

- `reference_m1_30_cases_REVIEWED.csv` (non fourni, à construire).
- `evaluation_protocol.md` figé (échantillonnage, seuils et séparation entraînement/test).
- `evaluation_run_<id>.json` et tableau par cas.
- `model_card_v2.md` mis à jour avec résultats réels et limites.

**État au 12/11/2026 :** aucun score indépendant M1 justifiable ; ne pas déclarer « V2 validée sur 30 cas ».
