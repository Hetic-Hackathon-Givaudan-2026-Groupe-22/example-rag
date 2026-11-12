# Conserver M3 v0.2 et v0.3 : justification pour la livraison

## M3 v0.2 — Prévision
- Jeu : 30 aliments, 136 séries par pays, 12 784 observations mensuelles.
- Horizon : 3 mois ; backtest chronologique avec 10 origines de sélection et un contrôle final distinct (origine 2026-07).
- Sur sélection : **Last Value MAE 7,6517**, Holt amorti 8,1532, Ridge direct 8,3804, saisonnière 10,7967.
- Sur contrôle final : Last Value **10,9743**, Holt amorti 13,5714, Ridge 12,1589, saisonnière **10,1593**.
- Last Value est choisi par MAE sur sélection, non sur le contrôle final. La naïve saisonnière gagne le contrôle final.

## M3 v0.3 — Diagnostic temporel
- Conserve **exactement Last Value** : prévisions à 3 mois identiques à v0.2 (408 lignes).
- Ajoute des fenêtres glissantes de 3 mois et des états observés (hausse à confirmer/persistante, stabilité, repli, faible attention).
- 11 288 états temporels calculés ; seuils exploratoires.
- **Aucun gain de MAE** : sélection 7,6517 et contrôle final 10,9743, identiques à v0.2.
- Apport réel : suivi explicable des phases où la baseline Last Value est plus/moins fiable.
- Les états dynamiques ne constituent pas des labels prospectifs Buzz/Trend et ne sont pas une optimisation prédictive démontrée.

## Limites communes

Les indices Google Trends sont normalisés dans des fenêtres pouvant inclure des dates futures par rapport à certains backtests historiques. Les tests restent rétrospectifs, sans preuve de généralisation prospective. La pistache provient d'une fenêtre de normalisation différente et reste un cas provisoire. L'enrichissement futur du jeu de données et la validation avec données collectées à chaque date historique restent nécessaires.

**Conclusion de livraison : conserver les deux variantes** : v0.2 pour la prévision comparative, v0.3 pour l'interprétation par état temporel. Ne pas présenter v0.3 comme un modèle prédisant mieux.
