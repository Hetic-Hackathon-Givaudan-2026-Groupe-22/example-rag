# GitHub — Publication groupée M1/M2/M3

Pour les intervenants, publier **code + README + rapport + tests + métriques synthétiques**. Les fichiers CSV d'observations collectées, séries temporelles et dérivés ré-identifiables de source Google Trends doivent faire l'objet d'une vérification des droits de redistribution avant d'être publiés dans le dépôt public. Il est possible de publier le code sans ces CSV, en documentant la façon de les générer depuis des sources autorisées.

**Preuve M3 v0.3** :
- 28 tests réussis localement dans le package préparé ;
- 136 séries, 30 aliments, 11 288 états dynamiques, 408 prévisions à 3 mois ;
- prévision Last Value strictement identique à M3 v0.2 ;
- `metrics_rolling_v03.json` / `manifest_rolling_v03.json` / `RAPPORT_M3_V03_FENETRES.md` ;
- API `/m3/dynamics/*` vérifiable avec le même dossier.

**Statut :** développement et tests locaux ; non publié sur GitHub à ce stade. La classification dynamique M2 (Buzz/Trend avant le pic) n'est pas implémentée.
