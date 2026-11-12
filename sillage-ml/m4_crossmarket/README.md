# Sillage — M4 Cross-market v0.1 (expérimental)

**Équipe G22 × Givaudan — 12 novembre 2026.** Module exploratoire d'analyse de la chronologie des *signaux d'attention* Google Trends par pays. **Ce module ne prouve ni une propagation causale, ni l'origine mondiale d'un ingrédient, ni un volume de demande.**

## Objet et résultats réels

À partir des données préparées M3 v0.2/v0.3 : **30 aliments, 136 séries ingrédient × pays, 12 784 observations mensuelles**, entre 2019-01 et 2026-10 pour FR, US, JP, KR, AE. Les séries ne sont **pas** 136 nouvelles tendances indépendantes : ce sont des séries d'intérêt mensuel distinctes.

Exécution exploratoire fournie dans `artifacts/m4_v01/` :
- **104/136 séries** présentent au moins une hausse relative *confirmée par la règle* ; absence de détection ≠ absence de marché.
- **22/30 aliments** présentent un signal dans **au moins deux pays** et peuvent faire l'objet d'une comparaison chronologique.
- **13/30** conservent les mêmes pays premiers sur les seuils de 6, 8, 12 points, avec un signal dans >= 2 pays à chacun de ces seuils.
- **26/30** requièrent une revue manuelle pour au moins l'un des motifs : signal très proche de la borne d'observation, premier pays sensible au seuil, couverture insuffisante ou termes de recherche différents.

**Exemple : `dubai_chocolate`.** Au seuil nominal de 8 points, premier signal confirmé aux **Émirats arabes unis (AE) en 2024-06**, KR 2024-07, JP et US 2024-08, FR 2024-10. Au seuil 12 points : **AE et KR ex æquo**, juillet 2024 ; l'ordre exact est donc **sensible au seuil**. Cette chronologie est un indicateur issu de l'algorithme, pas un récit historique ni une preuve de diffusion.

**Exemple : `dalgona_coffee`.** Au seuil nominal, les cinq pays ont un premier signal confirmé en 2020-04 (ex æquo) : aucune avance mensuelle discernable ici.

**Exemple : `matcha`.** Première hausse *détectable dans l'intervalle analysé* en US 2020-05, mais ce n'est surtout **pas** une preuve d'origine du matcha aux États-Unis : l'aliment et sa consommation précèdent la fenêtre 2019–2026. L'algorithme cherche le premier *rebond relativement à la référence locale*, pas la première adoption historique.

## Méthode — uniquement des informations observables à la date T

Pour chaque combinaison `topic_id × country_iso2` :
1. Conserver les mois originaux, sans conversion de manque en zéro ; rejeter fréquence non mensuelle, séries incomplètes, doubles observations, données synthétiques, pays non ISO2. Exclure `WORLD` et les projets linguistiques Wikipédia.
2. À la date T, construire une **baseline locale de 12 mois** précédant immédiatement les **3 mois récents** ; seuil = `max(8 points, 35 % × max(médiane_baseline, 5), 2 × MAD_baseline)`.
3. Confirmer une hausse seulement si **au moins deux des trois mois récents** dépassent `médiane + seuil` ET si leur moyenne dépasse ce seuil. Le *mois de confirmation* est T, pas le premier mois de la hausse.
4. Garder le **premier mois confirmé dans la fenêtre disponible**, puis ordonner les pays détectés pour le même aliment. Les écarts sont des **mois calendaires**, et les ex æquo restent ex æquo. Une seule série pays → aucune conclusion cross-market.
5. Répéter avec seuils absolus 6 et 12 points, en maintenant le reste des critères fixe, pour indiquer la sensibilité du premier pays.

**Limite fondamentale :** la série Google Trends 0–100 d'un pays est normalisée indépendamment. Nous ne comparons **jamais directement** 80 points en FR à 80 points en JP comme des volumes. Nous comparons seulement des **dates de hausse relatives aux historiques locaux**, pour une même notion alimentaire. Les périodes de normalisation couvrent des dates postérieures à certains points de notre chronologie : la reconstitution est **rétrospective** et ne fournit pas une détection prospective strictement sans fuite liée à la source.

**Autres limites :** comparaison temporelle mensuelle (pas journalière), recherches en anglais ou langues locales qui ne couvrent pas forcément les mêmes populations, fortes fluctuations sur faibles volumes, saisonnalité, censure à gauche (début d'observation 2019), seuils non calibrés, absence de vérité terrain sur la propagation. Aucune précision / F1 de M4 n'est mesurable sans vérité terrain externe. Les résultats peuvent être trompeurs sur des buzz à faible attention ; ils restent des **candidats à revue**.

## Installation / test dans Git Bash (Windows)

Décompresser à `C:\Users\VOTRE_UTILISATEUR\Projects\Givaudan\Sillage_M4_CrossMarket_V01` ; le ZIP a directement les fichiers à sa racine, sans double dossier.

```bash
cd ~/Projects/Givaudan/Sillage_M4_CrossMarket_V01
source ../sillage_pipeline_m1_v02/.venv/Scripts/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

**Reproduire les résultats** :

```bash
python -m sillage_m4.run \
  --input data/processed/m3_30_foods_geo_2019_2026.csv \
  --out artifacts/m4_v01
```

**API FastAPI** :

```bash
export SILLAGE_M4_ARTIFACT_DIR="artifacts/m4_v01"
uvicorn sillage_m4.api:app --port 8006
```

Swagger : http://127.0.0.1:8006/docs ; essayer `GET /m4/summary?ingredient=dubai_chocolate`, `GET /m4/lags?ingredient=dubai_chocolate`, `GET /m4/timelines?ingredient=matcha`, `GET /m4/methodology`.

## Livrables et fichiers

| Fichier | Contenu |
|---|---|
| `artifacts/m4_v01/market_timelines.csv` | 136 lignes, par pays : premier signal, preuve de seuil, requête et URL source, drapeaux qualité |
| `artifacts/m4_v01/cross_market_lags.csv` | Pays détectés, ordre et décalage mensuel depuis le premier confirmé |
| `artifacts/m4_v01/ingredient_summary.csv` | Synthèse des 30 aliments, pays premiers / ex æquo, couverture et alertes |
| `artifacts/m4_v01/threshold_sensitivity.csv` | Premier marché avec seuils 6/8/12 ; stabilité |
| `artifacts/m4_v01/review_needed.csv` | Aliment demandant une revue humaine et contexte |
| `artifacts/m4_v01/metrics_m4.json` | Comptages descriptifs et avertissements — **pas** métriques de prédiction |
| `artifacts/m4_v01/manifest_m4.json` | SHA-256 des entrées et sorties, paramètres, date de calcul |

## Place de M4 dans la chaîne Sillage

- **M1** : détecteur statistique d'émergence ; ne pas confondre ses alertes avec le premier signal de M4.
- **M2 v2** : Random Forest expérimental Buzz / Trend, entraîné sur trajectoires historiques entières ; **ne pas l'utiliser directement pour conclure à une tendance durable à une date antérieure**.
- **M3 v0.2** : prévision à trois mois et comparaison de quatre méthodes, `last_value` retenu sur la MAE de sélection.
- **M3 v0.3** : mêmes prévisions / MAE que v0.2, plus diagnostic par fenêtres glissantes ; **aucun gain de prévision revendiqué**.
- **M4 v0.1** : chronologie exploratoire des hausses locales entre pays ; résultats distincts des classes M2 et des forecasts M3.

Voir `RAPPORT_M4_V01.md` et `NOTE_M3_VERSIONS.md` avant toute présentation aux intervenants.

## Pour GitHub

Publication recommandée à la fin du travail sur `hackathon-app`, branche dédiée, avec scripts, tests, README et rapports. **Vérifier les droits de redistribution avant d'inclure** `data/processed/` ou les exports contenant des valeurs Google Trends ; sans autorisation, ne pousser que les scripts et des exemples synthétiques **explicitement étiquetés**. Ne pas inclure de `.venv` ou de caches Python.
