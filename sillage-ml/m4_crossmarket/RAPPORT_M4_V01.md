# Rapport M4 v0.1 — Chronologies cross-market (12/11/2026)

## But
Pour chaque ingrédient, comparer la **date du premier signal de hausse relativement à sa propre référence locale** dans les marchés FR/US/JP/KR/AE. Calculer les retards par mois, conserver les ex æquo, les requêtes sources et le niveau d'incertitude. Ce système ne prouve pas une chaîne de causalité ni un lieu historique d'origine.

## Périmètre vérifié

| Mesure | Résultat |
|---|---:|
| Aliments | 30 |
| Séries géographiques | 136 |
| Points mensuels | 12 784 |
| Pays analysés | 5 (FR, US, JP, KR, AE) |
| Séries avec hausse confirmée par l'heuristique | 104 |
| Aliments avec au moins 2 pays détectés | 22 |
| Aliments dont le premier marché résiste aux 3 seuils | 13 |
| Aliments nécessitant une revue pour au moins un motif | 26 |

Les 26 cas à revoir ne signifient pas 26 échecs, mais des réserves de couverture, méthode ou sources. **La précision de M4 est inconnue faute de vérité terrain.**

## Cas illustratifs fondés sur les résultats M4

### Dubai chocolate

| Marché | Premier mois confirmé (seuil 8) | Décalage depuis premier signal |
|---|---|---:|
| AE | 2024-06 | 0 |
| KR | 2024-07 | 1 |
| JP | 2024-08 | 2 |
| US | 2024-08 | 2 |
| FR | 2024-10 | 4 |

**Sensibilité** : seuil 6 -> AE 2024-06 ; seuil 8 -> AE 2024-06 ; seuil 12 -> **AE et KR ex æquo 2024-07**. Il serait trompeur de présenter AE comme un leader certain au mois près.

### Dalgona coffee

Le premier signal confirmé est détecté en 2020-04 dans **les cinq pays en même temps**, à la résolution mensuelle et aux seuils testés. Impossible d'en inférer un ordre entre ces cinq marchés.

### Matcha

Le premier signal de hausse *dans la fenêtre considérée* est détecté en US 2020-05 (seuil 8). **Cela ne désigne pas l'origine du matcha**, dont la consommation est bien antérieure à cette période, et le premier pays change avec le seuil (12 points -> FR). Ce cas doit être marqué comme non conclusif sur une « propagation ».

### Pistachio

Séries sous termes localisés (pistache/pistachio/ピスタチオ/피스타치오/فستق حلبي) et normalisation P0 2019–2026, différente des autres sujets. **Pistache est un cas provisoire**, et son rang n'est pas interprétable comme un pays d'origine.

## Protocole de détection

Voir `README.md` ; calcul glissant 12 mois de baseline, comparaison avec 3 mois récents, 2 mois au-delà du seuil, différences entre dates de confirmation. Une confirmation ne se fait qu'avec les observations disponibles à cette date **dans la série déjà extraite**, mais la normalisation Google Trends globale (jusqu'à 2026) introduit potentiellement une information postérieure lors du replay historique. Résultats non prospectifs.

## Vérifications et limites

- Les sorties conservent **URL, termes, pays, mois, scope de normalisation** ; pas de pays inféré depuis Wikipédia.
- Pas de comparaison de volumes entre les indices 0–100 des pays.
- Les cibles ML de M2 ne sont pas utilisées pour calculer les premiers marchés.
- Les mois manquants ne sont pas remplis de zéros ; aucune date interpolée.
- Ex æquo conservés ; pour un seul pays détecté, pas de comparaison cross-market.
- Une détection au début de la période peut être un signal déjà en développement, ce qui est marqué `early_boundary_flag`.
- Aucun mécanisme n'établit que le marché A *cause* la hausse du marché B.
- La robustesse évaluée concerne seulement 3 seuils (6/8/12), pas une mesure statistique de confiance.

## Livrables

Données et scripts : `data/processed/`, `sillage_m4/`. Résultats : `artifacts/m4_v01/` (CSV synthèse/écarts/seuils/revue, JSON métriques descriptives/manifeste). API : `sillage_m4.api:app` sur le port 8006 ; Swagger `/docs`. Tests : `python -m pytest -q`.

**Priorité pour la suite :** validation experte de 5 à 10 chronologies, surtout les exceptions, et réextraction par fenêtre historique pour évaluer la fuite de normalisation avant toute affirmation prospective.
