# [Produit / Data] SILLAGE — Extension de 30 à 500 concepts et état des sources sociales

## Pourquoi passer de 30 à 500 concepts ?

Les premiers travaux SILLAGE reposent sur **30 sujets alimentaires** et environ **25 474 observations historiques Google Trends / Wikimedia**. Cette base a permis de construire les premiers prototypes, mais reste trop limitée pour évaluer des tendances diversifiées, distinguer buzz et phénomènes durables, et étudier leur diffusion entre pays.

Nous visons donc **environ 500 concepts alimentaires validés**, sélectionnés parmi **530 candidats V4**, couvrant ingrédients, saveurs, recettes, produits et phénomènes alimentaires. L'idée est d'inclure des trajectoires variées, y compris des tendances faibles ou qui n'émergent pas dans tous les marchés.

**Périmètre :** FR, US, JP, KR et AE ; historique recherché **2019–2026** ; granularité temporelle native, idéalement hebdomadaire lorsque disponible.

## La base de données est déjà cadrée

L'architecture retenue comporte huit tables : `concepts`, `markets`, `signal_series`, `raw_signals`, `market_time_features`, `future_labels`, `cross_market` et `evidence_documents`.

Les données sont d'abord collectées **source par source en RAW**, avec leurs requêtes, dates et références, puis nettoyées et harmonisées. Les hashtags synonymes d'un même concept restent distincts tant que leur chevauchement n'est pas étudié ; aucune donnée manquante ni géographie ne sont inventées.

## Essais TikTok et Instagram : résultats et limites

**TikTok.** L'extension Chrome avec ChatGPT Work a permis d'accéder à un compte connecté, de rechercher des vidéos et de voir certaines métriques. Mais la collecte automatique de vidéos n'a pas été autorisée par les conditions TikTok applicables : **0 observation RAW réutilisable archivée**. Creative Center montre des tendances agrégées sur des fenêtres courtes, sans export historique réutilisable confirmé.

**Instagram.** Des références publiques ont pu être repérées, mais **aucun dataset RAW officiel n'a été acquis**. L'API Hashtag Search impose des accès professionnels et des autorisations Meta ; elle ne donne pas librement des séries historiques exhaustives depuis 2019, ni une géographie fiable. La Meta Content Library est destinée à des chercheurs éligibles, avec restrictions d'export.

Ces plateformes restent **stratégiques pour détecter des signaux alimentaires précoces**, mais les tests montrent que connecter un compte personnel ne suffit pas pour constituer des séries historiques exploitables. Nous ne poursuivons pas ces essais de navigation à répétition tant qu'un accès adapté n'est pas identifié.

## Une solution payante testée : Exolyt

Nous avons testé **Exolyt**, une plateforme d'analyse TikTok, sur le hashtag **`#dubaichocolate`**. L'interface montrait des **courbes d'évolution des vues et du nombre de vidéos**, des hashtags voisins (`#dubai_chocolate`, `#chocolatedubai`, etc.) et un bouton **CSV**. Elle affichait également une limite d'historique d'abonnement allant de novembre 2024 à novembre 2026, sans que l'export complet de cette période ait été vérifié.

**Le blocage est économique et contractuel :** l'export utile est payant, et les conditions Exolyt exigent de clarifier les droits pour constituer des datasets et entraîner des modèles. La couverture de 500 concepts, des cinq marchés et de 2019–2026 n'est pas démontrée.

**Exolyt pourrait donc être présenté à Givaudan comme une piste d'enrichissement sous licence**, en complément du MVP gratuit, à étudier en fonction des coûts, de la couverture et des droits de réutilisation. Ce n'est pas une solution déjà acquise.

## Sources explorées en parallèle — budget 0 €

En attendant, la collecte progresse sur des sources gratuites ou accessibles sous conditions à confirmer : **Google Trends et Wikimedia** (historiques V4 à étendre), **Open Food Facts** (produits/ingrédients et pays déclarés), **GDELT et presse sectorielle** (signaux médiatiques datés), et **YouTube Data API** (vidéos et métadonnées historiques, sous réserve des quotas et droits).

La méthode reste **progressive, par lots de 20 à 50 concepts**, avant extension aux 500 concepts validés. TikTok et Instagram pourront enrichir la base plus tard si une solution autorisée est obtenue.

---
**Références :** [Dépôt SILLAGE](https://github.com/Hetic-Hackathon-Givaudan-2026-Groupe-22/example-rag/tree/main/sillage-ml) · [Conditions TikTok EEE](https://www.tiktok.com/legal/page/eea/terms-of-service/en) · [Creative Center](https://ads.tiktok.com/creative/creativeCenter/trends/hashtag) · [Exolyt : tarifs](https://exolyt.com/pricing) / [conditions](https://exolyt.com/terms) · [Meta Content Library](https://developers.facebook.com/documentation/meta-content-library)

*État des recherches au 25 novembre 2026.*
