# Rapport expérimental — M3 v0.3 fenêtres glissantes

## Hypothèse
La précision moyenne globale de Last Value peut masquer de fortes erreurs lorsque l'attention est en hausse ou en déclin. On conserve Last Value comme prévision à 3 mois mais on ajoute, *pour le diagnostic*, un état de dynamique calculé à la date de prévision.

## Méthode
Fenêtres adjacentes (A/B/C) de 3 mois, décalées mensuellement ; aucune observation de T+1 ou ultérieure n'entre dans l'état à T. Historique minimum 12 mois. Seuils indicatifs: variation ≥5 points d'indice et ≥15 % de l'intervalle précédent. Deux variations successives qualifient la persistance; stabilité en niveau haut conservée comme état distinct. Ni la présence d'une phase haussière ni la stabilité en niveau élevé n'impliquent un label M2 de durabilité.

## Résultats
- 30 aliments, 136 séries par pays, 12 784 points ; 11 288 états calculés mois par mois.
- Au dernier mois de données (octobre 2026) : 35 `faible_attention`, 16 `hausse_a_confirmer`, 0 `hausse_persistante`, 6 `stable`, 33 `stable_niveau_eleve`, 28 `repli_a_confirmer`, 18 `repli_persistant`.
- Les **408 prévisions Last Value à M+1/M+2/M+3 sont numériquement identiques** à M3 v0.2 ; test de non-régression sur les 408 lignes.
- Sur les mêmes 10 dates de sélection : MAE Last Value = **7,6517**. Sur holdout juillet 2026 : **10,9743**. Les diagnostics par phase sont conservés dans `metrics_last_value_by_state.csv`. Ils ne servent pas à sélectionner un modèle après coup.
- Exemples : matcha FR = `stable_niveau_eleve`, dalgona FR = `faible_attention`, Dubai chocolate US = `repli_persistant` (octobre 2026). Données source et états vérifiables dans les CSV exportés.

## Interprétation / limites
La règle Last Value ne « choisit » ni buzz ni tendance : elle prolonge la dernière observation. Un nouveau mois réactualise les états, *sans* entraîner de modèle de classification de durabilité. Une stagnation après une hausse peut être compatible avec une tendance durable. L'analyse par phase permet de situer les erreurs mais ne démontre pas une amélioration prédictive. Les indices Google Trends ont une normalisation rétrospective potentiellement affectée par les mois futurs, ce qui empêche de prétendre à une validation prospective stricte.

## Livrables
Code `sillage_m3/rolling.py`, `sillage_m3/run_rolling.py`, extensions API, 8 nouveaux tests, 8 fichiers d'artefacts et manifeste de traçabilité ; 28 tests au total.
