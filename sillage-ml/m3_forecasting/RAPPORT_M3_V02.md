# Rapport technique — M3 Forecasting étendu (30 aliments)

**Date de l'expérience :** 12 novembre 2026  
**Statut :** reproductible, expérimental et rétrospectif.

## 1. Objectif

Tester si les conclusions du M3 v0.1 fondées sur 4 ingrédients / 19 séries se maintiennent quand le périmètre atteint 30 ingrédients / 136 séries géographiques. Prévision de l'indice Google Trends à M+1, M+2 et M+3.

## 2. Préparation des sources

| Source | Règle | Séries | Points |
|---|---|---:|---:|
| Référentiel historique | Exclure `oud`, exclure `WORLD` | 131 | 12 314 |
| Lot pilote P0 | Ajouter seulement `pistachio` pour éviter les doublons de sujets | 5 | 470 |
| **Total** | 30 ingrédients distincts | **136** | **12 784** |

Tous les points sont des observations originales ; aucun mois manquant ou zéro de remplacement. Les requêtes originales, URLs, fichiers source et la distinction des fenêtres de normalisation sont conservés.

**Important :** 4 818 indices nuls originaux dans le lot préparé. Les indices Google Trends sont relatifs et n'équivalent pas à des volumes de demande.

## 3. Validation

- **Folds de sélection :** 10 origines trimestrielles de janvier 2024 à avril 2026, horizon 1 à 3 mois.
- **Holdout :** dernière origine de juillet 2026, utilisée après sélection.
- **Four candidates :** Last Value, Holt amorti, Ridge Direct (appris seulement sur le passé de chaque série), naïve saisonnière à 12 mois.
- **Mesures :** MAE moyen par prédiction, RMSE, biais et MAE macro par ingrédient.
- **Effectifs :** 4 080 prédictions de sélection et 408 prédictions de holdout **par modèle**.

## 4. Résultats principaux

| Modèle | MAE sélection | RMSE sélection | MAE holdout | RMSE holdout |
|---|---:|---:|---:|---:|
| **Last Value** | **7,6517** | **15,2725** | 10,9743 | **19,7728** |
| Holt amorti | 8,1532 | 15,3727 | 13,5714 | 22,1151 |
| Ridge Direct | 8,3804 | 15,8695 | 12,1589 | 21,3696 |
| Naïve saisonnière | 10,7967 | 20,3898 | **10,1593** | 20,2431 |

**Décision :** Last Value retenu, car meilleur sur le critère préenregistré de **MAE des folds de sélection**, même si la naïve saisonnière a une meilleure MAE sur le holdout. Ce résultat ne justifie **pas** de changer de modèle a posteriori en utilisant le holdout.

Sur 30 ingrédients, Last Value est le meilleur en MAE de sélection pour 18 ingrédients ; Ridge pour 6, Holt pour 5, naïve saisonnière pour 1. Ces effectifs soulignent l'hétérogénéité des trajectoires et le potentiel futur d'un système choisissant le modèle selon le profil, à étudier sur de nouvelles données pour éviter l'overfitting.

## 5. Ablation de la pistache provisoire

Sur les **29 ingrédients historiques / 131 séries** : Last Value reste le meilleur selon la MAE de sélection (**7,4298**) devant Holt (**7,9714**), Ridge (**8,1731**) et naïve saisonnière (**10,6228**). Sur le holdout, naïve saisonnière gagne en MAE (**10,4198**), suivie de Last Value (**10,9046**). L'ajout de pistache ne renverse donc pas la sélection principale.

## 6. Interprétation et limites

1. L'expérience est **rétrospective** : les exports Google Trends historiques sont normalisés à l'aide de fenêtres finissant en octobre 2026 ; le dénominateur historique peut intégrer de l'information future.
2. La pistache a un périmètre de normalisation 2019–2026, tandis que les 29 historiques ont une extraction 2014–2026. Les indices ne sont pas comparables en volumes entre séries.
3. Les métriques globales traitent les séries également par prédiction, pas nécessairement les ingrédients également : les moyennes macro par ingrédient sont donc archivées séparément.
4. Les 30 labels Buzz/Trend proviennent de M2 mais **ne sont pas utilisés** pour entraîner les prévisions de M3. Le label de la pistache n'a aucune incidence.
5. Méthodes comparées sur seulement une origine finale ; pas de preuve de généralisation hors distribution.

## 7. Preuves à montrer aux intervenants

- Scripts `sillage_m3/prepare_reference.py`, `core.py`, `run.py`, `api.py` ;
- `data/processed/audit_preparation_30_aliments.json`, empreintes SHA256 ;
- métriques, prédictions complètes et résultats par ingrédient dans `artifacts/m3_30_aliments_v02/` ;
- **20 tests automatisés réussis** dont contrôles de conservation des données, non-fuite via code, protocole chronologique et API réelle.

**Statut :** M3 v0.2 première extension validée techniquement. Recherche supplémentaire requise pour la validation prospective et le choix d'un modèle plus avancé.
