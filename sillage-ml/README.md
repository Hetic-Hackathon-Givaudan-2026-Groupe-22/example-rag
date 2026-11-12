# Sillage — Livrable collectif Data & ML | Équipe G22 — Auralis

**À lire en premier :** [`LIVRABLES_V2.md`](LIVRABLES_V2.md) (les 5 livrables), [`GUIDE_PUBLICATION_EQUIPE.md`](GUIDE_PUBLICATION_EQUIPE.md) (publication GitHub).

**Date :** 12 novembre 2026 · **Statut :** V2 expérimentale · **Projet :** Sillage — Équipe G22 / Auralis · **Dépôt officiel :** `hackathon-app` (la branche de contribution n’est pas l’identité de l’équipe).

Cette archive rassemble les **modules développés et testés séparément** pendant le hackathon. **Elle ne prétend pas être une application intégrée M1→M5.** Les sources, indices et labels sont soumis à validation. Les fichiers d'entrée utilisés pour les tests Python sont inclus pour faciliter la reproduction ; contrôler les droits de redistribution avant de fusionner dans une branche publique.

## Modules et résultats (reproduits localement)

| Module | Dossier | Résultat | Limite |
|---|---|---|---|
| Nettoyage Wikipédia | `lot01_wikipedia_cleaning` | 12 690 observations M1 admissibles ; 2 522 en quarantaine | édition linguistique ≠ pays |
| M1 — Détection | `m1_detector`, `lot02_google_trends` | 56 alertes candidates sur 1 786 observations GT et 19 séries ; 450 alertes Wikipédia | alertes non vérifiées comme véritables tendances |
| M2 — Buzz / Trend | `m2_classifier_v2` | Random Forest, LOOTO, 29/30 corrects, F1 macro ≈ 0,967 | évaluation rétrospective ; 30e cas pistache provisoire, labels à auditer ; pas une prédiction avant le pic |
| M3 v0.2 — Forecast | `m3_forecasting` | 30 aliments ; 136 séries ; Last Value sélectionné, MAE sélection 7,6517 ; holdout 10,9743 | résultat rétrospectif ; normalisation Google Trends a posteriori |
| M3 v0.3 — Fenêtres glissantes | `m3_forecasting` | suivi de 11 288 états temporels ; mêmes 408 prévisions et MAE que v0.2 | gain descriptif, **pas de gain de précision** |
| M4 — Cross-market | `m4_crossmarket` | 104 séries avec signal, 22 aliments comparables entre ≥2 pays | chronologie relative, pas causalité ni leader historique établi |
| M5 — LLM + RAG | `m5_rag_prototype` | Qwen2.5 1.5B + embeddings nomic + ChromaDB : prototype documentaire fictif | **non relié** au corpus alimentaire ou aux résultats M1–M4 |

## Commandes de vérification (Git Bash / Python 3.12)

Depuis le dossier `sillage-ml` :

```bash
source ~/Projects/Givaudan/sillage_pipeline_m1_v02/.venv/Scripts/activate
(cd lot01_wikipedia_cleaning && python -m unittest discover -s tests -v)
(cd lot02_google_trends && python -m pytest -q)
(cd m1_detector && python -m pytest -q)
(cd m2_classifier_v2 && python -m pip install -r requirements-comparison.txt && python -m pytest -q)
(cd m3_forecasting && python -m pytest -q)
(cd m4_crossmarket && python -m pytest -q)
```

Les chemins `artifacts/` conservent les calculs versionnés, métriques et sorties du backtest. Les fichiers `README*` et `RAPPORT*` de chaque module détaillent les paramètres et limites.

## Vérification métier et scientifique

1. **M1** : les signaux sont des candidats sans précision/rappel validés.
2. **M2** : les 30 sujets sont distincts, mais évaluation a posteriori et label pistache encore provisoire ; pas de capacité prospective démontrée.
3. **M3** : la sélection Last Value privilégie la MAE sur folds de sélection ; le saisonnier gagne en MAE sur holdout. Fenêtres glissantes v0.3 = diagnostic, non amélioration prédictive.
4. **M4** : aucune preuve de diffusion causale ; effets de normalisation et de traduction ; 26/30 cas à revoir.
5. **M5** : les tests fictifs ne valident pas les citations ni les hallucinations sur Givaudan.

## Provenance / reproduction

- Données collectées au sein du groupe G22 : collecte du lot Google Trends réalisée par Joseph, puis préparation/expérimentation au sein du travail Data/ML collectif. Les contributions et leurs sources sont décrites dans [`CONTRIBUTIONS.md`](CONTRIBUTIONS.md).
- Séries Wikipédia conservées sans faux pays ; séries `WORLD` tenues distinctes.
- Données Google Trends : indices **relatifs à chaque requête/fenêtre/pays** (0–100) ; ne jamais sommer les marchés ni convertir en volumes.
- Les tests unitaires valident des invariants du code et des artefacts ; ils ne démontrent pas à eux seuls la validité scientifique.
- Publication : la branche de contribution est une étape technique ; **le livrable final et son README sont au nom de l’équipe G22 / Auralis**. Revue collective puis PR vers `develop` avant remise.
