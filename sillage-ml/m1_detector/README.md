# Sillage — Pipeline M1 v0.2 (prototype de détection)

**Objectif immédiat :** faire fonctionner la chaîne `CSV réel → validation/qualité → features → détection M1 → artefacts versionnés → API`.

Ce package est une **baseline statistique**, pas un modèle supervisé entraîné, **pas** un classifieur buzz/durable, **pas** encore un système cross-market prédictif. Aucune performance sur données réelles n'est affirmée tant que les 30 cas de référence ne sont pas fournis et validés indépendamment.

## 0. Où travailler

Ouvrir `sillage-ml` ou le dépôt **métier** Sillage dans VS Code. **Ne pas écraser `example-rag`** (exercice RAG commun). Copier le contenu de ce dossier dans une nouvelle branche ou un dossier de travail non partagé, et relire les différences avant un push.

## 1. Installation (Windows, terminal Git Bash VS Code)

```bash
cd ~/Projects/Givaudan/sillage-ml
py -3.12 -m venv .venv
source .venv/Scripts/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

Si Python 3.12 n'est pas installé, adapter le lanceur; ce dépôt fonctionne avec Python 3.11+.

## 2. Contrat des données réelles

Un CSV **long** : une ligne = **une observation d'un indicateur à une date pour un ingrédient et un pays**.

**Colonnes obligatoires :**

| Colonne | Exemple | Règle / avertissement |
|---|---|---|
| `ingredient` | `matcha` | Canonique, harmonisé; plusieurs alias à traiter côté collecte |
| `country` | `FR` | Pays ISO alpha-2 (format vérifié, la sémantique doit être contrôlée) |
| `date` | `2025-02-03` | ISO `YYYY-MM-DD`; **même fréquence par série** |
| `source` | `google_trends_csv` | Provenance explicite, jamais inventée |
| `metric` | `search_interest_index` | **Ne pas mélanger** indices, pageviews, comptes de produits |
| `value` | `42` | Nombre >=0; virgule décimale admise |
| `normalization_scope` | `trends_FR_matcha_2024_2026_exportA` | Identifiant exact du périmètre d'export/normalisation |
| `is_synthetic` | `false` | `true` uniquement pour simulation; **obligatoire** |

**Colonne recommandée :** `source_url` pour l'URL de l'export / de la source; son absence sur données réelles est signalée dans `quality.json`.

Pour Google Trends : les valeurs 0–100 sont relatives à leur export. Ne pas interpréter les indices de deux exports/pays indépendants comme volumes absolus comparables. Pour Wikimedia, les vues d'une édition linguistique ne sont pas des visites par pays. Il faut garder la traçabilité de la métrique et du scope.

**Si le Tech fournit d'autres noms de colonnes**, passer un fichier de mapping JSON (exemple `config_column_mapping_EXAMPLE.json`) à `--mapping`. Le mapping ne fabrique pas les valeurs absentes : harmoniser le CSV avant exécution si les champs essentiels manquent. Ne pas fusionner arbitrairement des fichiers aux granularités différentes.

## 3. Lancer sur les données **réelles** de l'équipe

Placer le CSV réel dans `data/raw/mes_donnees.csv`, sans modifier l'original, puis :

```bash
python -m sillage.pipeline --input data/raw/mes_donnees.csv --out artifacts/real --frequency weekly
```

Pour des valeurs mensuelles, utiliser `--frequency monthly`. Le détecteur utilise 12 observations passées (`--window 12`) et une comparaison à 4 observations (`--lag 4`) par défaut. Une série plus courte ou ayant des dates manquantes est **signalée et non interprétée** (`status=insufficient_history` / `irregular_frequency`). Aucune interpolation inventée.

Exemple de mapping :

```bash
python -m sillage.pipeline --input data/raw/mes_donnees.csv --out artifacts/real --frequency weekly --mapping config_column_mapping_EXAMPLE.json
```

**Artefacts produits dans `artifacts/real/` :**

- `cleaned.csv` : valeurs nettoyées (jamais de lignes synthétiques inventées)
- `features.csv` : caractéristiques temporelles calculées sans voir le futur
- `signals.json` : événements détectés et contexte (`robust_z`, croissance, origine)
- `series.json` : qualité/état de chaque série, y compris celles non exploitables
- `quality.json` : bilan des contrôles et des rejets
- `manifest.json` : version, paramètres, SHA256 du CSV d'entrée, nature des données

**Important :** les scores sont heuristiques et ne sont **pas des probabilités de tendance durable**. Le modèle M2 de classification sera une étape distincte.

## 4. Tester le pipeline sans données réelles (uniquement débogage)

```bash
python scripts/generate_synthetic_demo.py
python -m sillage.pipeline --input data/raw/demo_SYNTHETIC.csv --out artifacts/demo --frequency weekly
```

Les sorties de `artifacts/demo` doivent toujours être décrites comme **simulations**, jamais comme résultats Givaudan. Les tests unitaires utilisent eux aussi des exemples synthétiques.

## 5. API sur les **vraies sorties du modèle**

En Git Bash VS Code, après avoir exécuté le pipeline réel :

```bash
export SILLAGE_ARTIFACT_DIR="artifacts/real"
uvicorn sillage.api:app --reload --host 127.0.0.1 --port 8001
```

Ouvrir http://127.0.0.1:8001/docs . Endpoints : `GET /health`, `GET /model`, `GET /quality`, `GET /signals?ingredient=matcha&country=FR`, `GET /series`.

L'API **lit exclusivement les sorties générées**. Elle ne fabrique pas de tendance et retourne 503 lorsque les artefacts sont absents. Si la source du fichier est synthétique, la réponse le signale avec `is_synthetic: true`.

## 6. Évaluation sur 30 cas de référence indépendants

Copier `data/reference/reference_cases_TEMPLATE.csv` et constituer 30 cas **réels**, vérifiés indépendamment des sorties du modèle. Pour chaque cas : ingrédient, pays, source, métrique, scope, date `as_of_date`, label 0/1, justification et URL. La définition du label M1 est : **une émergence de référence est observée dans les 4 dernières périodes à la date de décision**. Il faut des cas positifs et négatifs. Définir les labels **avant** de régler les seuils sur ces cas.

```bash
python -m sillage.evaluation --input data/raw/mes_donnees.csv --references data/reference/30_cases_reels.csv --out artifacts/real/metrics.json --frequency weekly
```

Sorties : matrice de confusion, précision, rappel, F1, accuracy, prédiction par cas, avertissements si moins de 30 cas. **L'évaluation échoue** si une série de référence est absente/irrégulière ou sans historique suffisant. Prévoir une séparation temporelle développement/test, éviter toute fuite d'informations futures; 30 cas ne suffisent pas à généraliser un modèle supervisé.

## 7. Détection vs classification vs cross-market

- **M1** (ce code) : détecte *quand* une hausse inhabituelle a lieu dans chaque série locale.
- **M2** (à développer) : classe `buzz` vs `durable`, nécessite références et horizon temporel futur, labels réels.
- **M3** : régression / forecasting, prévision d'indice ou de croissance future, backtesting temporel.
- **M4 cross-market** : à partir des dates M1 par pays + séries sources comparables, mesurer délais/relations retardées; ne pas confondre corrélation et causalité.
- **M5 RAG/LLM** : rechercher des preuves dans les documents et expliquer les résultats ML, sans inventer des sources.

## 8. Checklist de livraison à l'équipe

1. `python -m pytest -q` réussi.
2. Premier CSV **réel** identifié et archivé, source et scope renseignés.
3. `quality.json` lu et anomalies de provenance traitées.
4. `series.json` montre quelles séries sont exploitables et pourquoi.
5. `signals.json` calculé sur la vraie collecte (ou vide si aucun signal).
6. 30 cas de référence réels documentés, métriques **effectivement calculées**.
7. API `/model` et `/signals` reflètent les fichiers produits, pas un JSON codé à la main.
8. Revue Data + Tech, validation de la publication GitHub sur une branche dédiée.

## Limites scientifiques

Seuils illustratifs : `z>=3`, croissance relative `>=25%`, écart MAD avec plancher de 1 point d'indice. Ces seuils doivent être calibrés sur des cas de développement (pas les 30 cas de validation). Le détecteur ne gère pas encore la saisonnalité, les ruptures de méthodologie de source ni les intervalles de confiance; il peut produire des faux positifs. Le découpage pays respecte les séries, mais **n'est pas encore un modèle cross-market**.
