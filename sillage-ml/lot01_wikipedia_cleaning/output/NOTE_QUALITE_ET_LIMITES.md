# SILLAGE | Rapport qualité — premier lot Wikimedia

**Exécution :** lot 01, 12 novembre 2026. **Source :** Wikipédia, comptage des vues d'articles des différentes éditions linguistiques.

## Résumé quantitatif

- **15 212** observations mensuelles réelles, **21** sujets alimentaires/associés, **10** éditions linguistiques, **159** séries.
- **12 690 observations** (**115 séries**) retenues pour un test exploratoire **M1 Wikipédia**.
- **2 522 observations** mises en quarantaine et conservées : **1 065** pour vérification du mapping des pages, **445** pour historique insuffisant et **1 012** hors du périmètre alimentaire.
- **0** valeur numérique invalide, **0** doublon de clé, **0** ligne invalide, **81** valeurs nulles (zéros) préservées.
- Les **159** statuts qualité recalculés concordent avec le rapport fourni.
- Période couverte : juillet 2015 → octobre 2026, selon la disponibilité de chaque page.

## Règles du nettoyage

1. Conserver les fichiers sources intacts et identifier le traitement par son manifeste SHA-256.
2. Contrôler les dates mensuelles, la fin de chaque mois, les valeurs, l'identité unique et la provenance.
3. **Aucune interpolation** des périodes sans observation ; **aucune suppression** des pics ; **aucune substitution** des zéros.
4. Séparer les séries documentaires utilisables des séries à vérifier, sans effacer les données non retenues.
5. Conserver les annotations de collecte dans la table générale mais **les exclure du contrat d'entrée M1** (labels non vérifiés).

## Limites qui doivent accompagner toute démonstration

- Les vues Wikipédia sont des **proxys d'attention documentaire**, pas des recherches Google, ventes ni preuves de demande alimentaire.
- Les éditions linguistiques Wikipédia **ne désignent pas un pays**. Aucun résultat cross-market géographique n'est valide à partir de ce lot seul.
- L'admissibilité d'une série (24 mois consécutifs et 85 % de couverture) ne constitue **ni une validation d'un modèle ni un label de tendance durable**.
- Les noms de pages problématiques doivent être vérifiés par un humain avant usage.
- Le CSV brut amont des appels API n'est pas fourni : demander une copie au Tech pour une traçabilité complète.

## État des livrables V2

| Livrable | État de ce lot |
|---|---|
| Données nettoyées et préparées | **Terminé pour la source Wikipédia** |
| Pipeline de traitement reproductible | **Terminé pour le nettoyage de ce lot** |
| Modèle M1 V2 publié | **Non couvert** (à développer / intégrer) |
| Validation sur 30 cas et métriques | **Non réalisée** (références indépendantes manquantes) |
| API renvoyant résultats de modèle réels | **Non couverte** (intégration ultérieure) |
