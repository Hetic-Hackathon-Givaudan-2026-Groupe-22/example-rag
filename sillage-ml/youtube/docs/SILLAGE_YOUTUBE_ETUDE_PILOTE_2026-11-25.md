# SILLAGE G22 — YouTube Data API v3 : journal des essais et décision Data/Product

**Investigation, exécution des tests et rédaction : Roua Cherni (@ROUA27)**  
**Date de l'étude : 25 novembre 2026**  
**Statut : exploration documentée — aucune base YouTube d'entraînement validée**  
**Dépôt cible :** `Hetic-Hackathon-Givaudan-2026-Groupe-22/example-rag`  
**Branche de contribution uniquement :** `docs/roua-social-data`  
**Emplacement :** `sillage-ml/youtube/docs/SILLAGE_YOUTUBE_ETUDE_PILOTE_2026-11-25.md`

> Ce rapport décrit des résultats réellement observés via des scripts exécutés localement le 25/11/2026. Aucun contenu vidéo n'a été téléchargé ; les requêtes n'ont pas créé de fichier RAW. Les exemples sont **des observations de test**, pas une mesure exhaustive de popularité ni une base de données sous licence pour l'entraînement. Aucune clé API n'est publiée.

## 1. Objectif et contexte SILLAGE

SILLAGE étudie les tendances alimentaires, sur cinq marchés (`FR`, `US`, `JP`, `KR`, `AE`). Le prototype Data existant comprend 30 concepts et environ 25 474 observations Google Trends/Wikimedia ; la trajectoire proposée vise ~500 concepts validés parmi 530 candidats V4, avec des historiques recherchés entre 2019 et 2026 et des prévisions à 12 semaines.

La question était de déterminer si **YouTube Data API v3**, sous accès gratuit, peut fournir :

1. **M1 — Découverte :** des traces datées de phénomènes alimentaires, sans prétendre mesurer le volume exact des publications ;
2. **M5 — RAG documentaire :** des preuves traçables, consultables à la demande, pour contextualiser un phénomène ;
3. **Validation des prédictions :** des sources susceptibles de corroborer une prévision, avec protocole hors-échantillon et sans fuite temporelle.

**Cas pilote :** `Dubai chocolate`, tablette chocolat/pistache/kadaïf ; période de publication interrogée 2023–2024. Aucun entraînement ni déploiement M1–M5 n'a été réalisé dans cette investigation.

## 2. Environnement et sécurité

- Activation de **YouTube Data API v3** dans Google Cloud ; création d'une **clé API pour données publiques** (non Gemini, non OAuth pour données privées).
- Authentification multifactorielle recommandée ; statut exact de son activation non consigné dans ce journal.
- Clé saisie directement dans Git Bash via `read -rsp ... YOUTUBE_API_KEY`, puis `export YOUTUBE_API_KEY` : pas de clé en clair dans les scripts, pas d'upload de secret.
- Requêtes REST officielles via Python standard (`urllib.request`, `urllib.parse`, `json`) : `search.list` et `videos.list`.
- Terminal local : `~/Projects/Givaudan/example-rag-social`, branche `docs/roua-social-data` ; scripts lancés en mémoire via `python - <<'PY'`, **aucun fichier de résultats sauvegardé**.
- Les tests ont été exécutés **sans changement dans V1, V2, `main` ou `develop`**.

## 3. Journal chronologique des expérimentations

### T1 — Recherche historique simple, 2024 (réussie)

**Endpoint :** `GET https://www.googleapis.com/youtube/v3/search` (`part=snippet`, `q=Dubai chocolate`, `type=video`, `publishedAfter=2024-01-01T00:00:00Z`, `publishedBefore=2025-01-01T00:00:00Z`, `maxResults=5`).

**Observation :** 5 vidéos retournées, avec identifiant, titre, chaîne et date de publication en 2024. Plusieurs vidéos traitaient explicitement du chocolat de Dubaï. Une page limitée à cinq résultats **n'est pas un inventaire exhaustif**.

### T2 — Statistiques publiques des 5 vidéos (réussie, mais impropre à l'historique)

**Endpoint :** `videos.list`, `part=snippet,statistics`, avec les identifiants du test T1.

**Observation :** les champs `viewCount`, `likeCount` et `commentCount` ont été retournés pour les cinq vidéos testées ; les valeurs correspondaient au **moment de l'appel en novembre 2026**, pas à la date de mise en ligne en 2024. Ces nombres ne peuvent être replacés artificiellement dans les semaines de 2024. Les compteurs bruts ne sont **pas reproduits dans ce document durable** en attendant une politique de rétention autorisée.

### T3 — Recherche par région et année : 5 marchés × 2 périodes (réussie)

**Endpoint :** `search.list` avec `q=Dubai chocolate`, `type=video`, `regionCode` parmi `FR,US,JP,KR,AE`, périodes 2023 et 2024, classement `relevance`, `maxResults=5`. Vérification des deux premiers résultats par combinaison via `videos.list(part=contentDetails)`.

**Observations :**
- **10 appels de recherche**, chacun retournant 5 résultats dans la page demandée ; **20 références examinées**, soit **9 identifiants vidéo distincts** dans cet échantillon.
- En **2023**, plusieurs résultats étaient hors sujet ou ambigus : *Chocolate Shop in Dubai*, chocolat vendu à Dubaï, dessert au chocolat. Une requête non spécifique génère des faux positifs.
- En **2024**, davantage de résultats portaient explicitement sur la tablette « Dubai chocolate » et la pistache, dont un exemple coréen.
- Les vidéos répétées dans plusieurs marchés ne doivent **pas être comptées plusieurs fois** comme publications distinctes.
- Le champ `regionRestriction` n'était pas déclaré pour ces exemples : cela **ne prouve pas une accessibilité absolue** et ne renseigne pas le pays d'audience historique.

### T4 — Recherche multilingue par marché (réussie, meilleure pertinence)

**Endpoint :** `search.list` avec `regionCode`, `relevanceLanguage`, périodes de publication 2024, `maxResults=4`, une requête par marché.

| Marché interrogé | Langue / requête exacte | Résultat du test | Exemple de lien et date observée |
|---|---|---|---|
| FR | `fr` — `chocolat de Dubaï pistache` | 4 résultats, dont une recette explicite | [Nutrivi](https://www.youtube.com/watch?v=Me6H7IEmcKM), 18/04/2024 |
| US | `en` — `Dubai pistachio chocolate` | 4 résultats, dont une recette virale explicite | [MyHealthyDish](https://www.youtube.com/watch?v=OiYVvjDpTbk), 01/06/2024 |
| JP | `ja` — `ドバイチョコレート ピスタチオ` | 4 résultats dans la langue de recherche | [Vidéo japonaise](https://www.youtube.com/watch?v=gjJViWVRc48), 16/08/2024 |
| KR | `ko` — `두바이 초콜릿 피스타치오` | 4 résultats, avec références à la pistache et au chocolat de Dubaï | [Piggest](https://www.youtube.com/watch?v=CUxhzI4Q_Is), 12/06/2024 |
| AE | `ar` — `شوكولاتة دبي فستق` | 4 résultats, dont une recette présentée comme tendance | [Recette arabe](https://www.youtube.com/watch?v=7HjVkkvgMfU), 16/06/2024 |

**Bilan : 20 références affichées et 17 identifiants vidéo distincts** ; les mêmes vidéos apparaissent parfois dans plusieurs recherches, même lorsque la langue change. Les titres traduits/localisés améliorent la pertinence **de cet échantillon**, mais ne valident pas encore le rappel ni la représentativité à grande échelle.

**Point de méthode :** `regionCode=AE` demande des vidéos recherchables/consultables dans le marché AE lors de l'appel. Cela ne signifie **ni créateur émirati, ni public émirati, ni popularité aux Émirats**. `relevanceLanguage=ar` favorise une langue, sans géolocalisation. Exemple : la recherche AE renvoie aussi du contenu francophone ou d'autres pays arabophones. Ne jamais imputer la géographie à partir de la langue.

### T5 — Enrichissement de six exemples via `videos.list(part=snippet)` (réussi)

**Échantillon :** cinq références du tableau ci-dessus + une vidéo ambiguë [L'atelier de Roxane](https://www.youtube.com/watch?v=O3WvvsTkt68).

**Observations :**
- FR : titre explicite mais description principalement promotionnelle et tags génériques ; la description n'est pas nécessairement utile.
- US et JP : titres explicites ; descriptions/tags non renseignés dans la réponse observée.
- KR : vidéo centrée sur une crème de pistache, mentionnant le Dubai chocolate ; **pertinence contextuelle**, mais pas nécessairement preuve du produit complet.
- AE : titre explicitement consacré à la tendance ; tags génériques de cuisine.
- Cas ambigu : tablette pistache sans référence explicite au « Dubai chocolate » dans le titre ou les tags ; **revue humaine/du contenu nécessaire**.

**Résultat :** on peut examiner titres, descriptions et tags, mais **la simple présence d'un mot-clé n'est pas un label de pertinence fiable**. La classification ci-dessus est **exploratoire, humaine**, non un score automatique autorisé ni une annotation de dataset produite industriellement.

## 4. Bilan des trois objectifs

| Objectif | Ce qui est démontré | Ce qui ne l'est pas | Décision |
|---|---|---|---|
| **M1 — Découverte** | Recherche de vidéos historiques datées, multi-requêtes/multilingue ; exemples pertinents | Exhaustivité, volumes par semaine, audience locale, mesure historique robuste, droit d'agrégation en production | **Candidat à la découverte qualitative uniquement** |
| **M5 — RAG** | Références YouTube datées, URL source, filtrage de recherche par marché et langue ; possibilité de reconsulter une vidéo | Véracité du contenu sans examen, marché d'origine/audience, pérennité de l'accès, droits d'une cache permanente | **Prototype de recherche documentaire à la demande envisageable** |
| **Validation prédictive** | Des documents publiés avant une date donnée peuvent servir d'éléments contextuels | Disponibilité effective dans le moteur de recherche à l'époque ; indépendance par rapport au jeu d'entraînement ; preuve de prévision sur un marché | **Non démontrée, protocole rétrospectif/prospectif requis** |

**Risque de fuite temporelle :** pour une prédiction au temps `t`, une vidéo `publishedAt <= t` ne garantit pas qu'elle aurait été retrouvée au temps `t`. Une recherche exécutée en novembre 2026 réordonne des vidéos historiques avec l'index de 2026. Pour valider M3/M4, conserver explicitement `published_at`, `queried_at`, `prediction_cutoff`, et distinguer *preuve documentaire actuelle* d'une *validation véritablement hors-échantillon*.

## 5. Contraintes techniques et juridiques — état au 25/11/2026

- **API et quota :** `search.list` permet le filtrage par `publishedAfter`, `publishedBefore`, `regionCode`, `relevanceLanguage`. Le quota reste soumis aux limites du projet ; ne pas supposer que 500 concepts × 5 marchés × plusieurs périodes est réalisable au quota standard.
- **Recherches non exhaustives :** classement, limites de pagination et changements d'index ; ne pas convertir les premières pages en courbe « nombre de vidéos par semaine » ou en mesure de popularité sans justification méthodologique et droits adaptés.
- **Vues, likes et commentaires :** mesures **courantes au moment de la requête**. Aucun historique d'audience géographique ou de vues datées n'a été obtenu.
- **Rétention :** pour les données publiques sans autorisation de propriétaire (`Non-Authorized Data`), YouTube impose une conservation temporaire limitée, avec suppression ou actualisation dans les 30 jours ; les statistiques non autorisées ne sont pas conservables au-delà de 30 jours. Éviter une archive permanente de titres, descriptions, tags, statistiques ou réponses JSON sans solution de conformité.
- **Métriques dérivées :** les règles standard restreignent la création de métriques/scores à partir des données API. Des dispositions supplémentaires existent pour certains développeurs audités, sur autorisation explicite ; **notre projet n'a pas déclaré bénéficier de ces droits**.
- **Entraînement ML :** une clé API ne confère **pas** de licence générale pour créer un corpus d'entraînement historique ou réutiliser les vidéos/transcriptions. Usage de production et réutilisation pour Givaudan à clarifier par une vérification des conditions et, si nécessaire, une autorisation adéquate.
- **Ce document :** consigne le protocole, des résultats agrégés de tests ponctuels et des URL de référence ; toute éventuelle copie locale de métadonnées détaillées devra avoir un propriétaire, une date de vérification, une durée de vie et une procédure de rafraîchissement/suppression.

**Textes officiels :**
- Documentation `search.list` : https://developers.google.com/youtube/data/reference/rest/v3/search/list
- Documentation `videos.list` : https://developers.google.com/youtube/data/reference/rest/v3/videos/list
- Objet `videos` et restrictions géographiques : https://developers.google.com/youtube/data/reference/rest/v3/videos
- Règlement pour les développeurs (notamment section III.E) : https://developers.google.com/youtube/terms/developer-policies
- Dispositions supplémentaires pour métriques dérivées / conservation : https://developers.google.com/youtube/terms/derived-metrics-policy
- Conditions de service EMEA : https://developers.google.com/youtube/terms/api-services-terms-of-service-emea-fr

## 6. Conclusion et décision

**Découverte confirmée :** YouTube Data API v3 permet de retrouver rapidement des preuves audiovisuelles datées et des références pertinentes dans plusieurs langues. Les requêtes locales ont nettement amélioré la précision apparente des exemples `Dubai chocolate` en 2024 par rapport à la requête globale et aux faux positifs de 2023.

**Décision pour SILLAGE :** retenir YouTube comme **source candidate de recherche/documentation pour M5**, et comme aide **qualitative** à la découverte M1, avec consultation à la demande et provenance explicite. Ne **pas** présenter YouTube comme mesure historique de popularité ou comme dataset d'entraînement disponible. La validation prédictive par YouTube reste **à construire**, séparément des modèles déjà entraînés et de leurs jeux de validation.

## 7. Prochaine phase — à démarrer après cette documentation

1. Prototyper un connecteur M5 **lecture seule** (`search.list` + `videos.list`) sur **`docs/roua-social-data` uniquement**, dans un nouvel emplacement `sillage-ml/youtube/` ; aucun accès aux dossiers V1/V2.
2. Définir un protocole de qualité : requêtes par marché/alias linguistiques, faux positifs, doublons, provenance, date de consultation, disponibilité déclarée, abstention si preuve insuffisante.
3. Prévoir une couche de cache **temporaire et conforme**, ou requêtes à la demande sans archivage des données API ; secret jamais stocké dans Git.
4. Tester **20 concepts** avant extension, sans lancer de collecte massive non autorisée ; documenter les coûts de quota et les droits.
5. Concevoir une évaluation de M5 indépendante de l'entraînement, avec annotations humaines et critères vérifiables, avant toute utilisation en validation prédictive.

**Suivi :** ticket Spike dans `Hetic-Hackathon-Givaudan-2026-Groupe-22/hackathon-app` ; lien réciproque à renseigner une fois le ticket créé.
