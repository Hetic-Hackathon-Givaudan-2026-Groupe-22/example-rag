# GitHub — publication collective du livrable Sillage V2

**Dépôt de destination :** `Hetic-Hackathon-Givaudan-2026-Groupe-22/hackathon-app` (pas `example-rag`).
**Auteur du livrable dans le README :** **Équipe G22 — Auralis**.
**Destination finale après revue :** branche `develop`, via Pull Request.

## Avant de pousser

1. Vérifier avec l'équipe les droits de redistribution des données préparées : le dépôt `hackathon-app` est public. Les sources brutes exclues dans `.gitignore` ne doivent pas être ajoutées de force.
2. Depuis Git Bash, dans `~/Projects/Givaudan`, cloner le dépôt **une seule fois** si `hackathon-app` n'existe pas localement.
3. Si `hackathon-app` est déjà présent, vérifier `git status -sb` avant tout changement. Ne pas écraser des modifications locales.
4. Mettre à jour `develop` puis créer une branche de contribution, par exemple `roua/sillage-ml-v2` **si elle n'existe pas**. Le nom de branche identifie la contribution Git et non la propriété du livrable.
5. Décompresser **le dossier unique `sillage-ml/`** à la racine de `hackathon-app` ; il contient ce guide, `README.md` et `LIVRABLES_V2.md`.

## Commandes de publication depuis Git Bash

```bash
cd ~/Projects/Givaudan/hackathon-app
git status -sb
git fetch origin
git switch develop
git pull --ff-only origin develop
git switch -c roua/sillage-ml-v2
# Après extraction du dossier sillage-ml dans ce dépôt :
git add sillage-ml/
git diff --cached --stat
git diff --cached --check
git status -sb
# Vérifier les fichiers stagés, notamment les données, avant de committer :
git commit -m "feat(sillage): publish G22 collective V2 ML deliverables"
git push -u origin roua/sillage-ml-v2
```

**Si la branche existe**, employer `git switch roua/sillage-ml-v2` à la place de `git switch -c ...`. **Si la branche existe à distance seulement**, faire d'abord `git fetch origin` puis `git switch --track origin/roua/sillage-ml-v2`.

**Ne jamais utiliser `git push --force` ni `git add -f` pour les données ignorées.** Le nom et l'e-mail de l'auteur du commit seront ceux configurés dans Git ; c'est normal, même lorsque le projet appartient à l'équipe.

## Après le push

- Vérifier `sillage-ml/README.md`, `sillage-ml/LIVRABLES_V2.md` et le fichier `m2_classifier_v2/artifacts/comparison_v2/model_v2.joblib` sur la branche distante.
- Ouvrir une **Pull Request** de `roua/sillage-ml-v2` vers `develop` en titre : **« Sillage G22 — livraison collective V2 (données, pipeline, modèle, métriques et API) »**.
- Inviter l'équipe à la revue ; **ne pas fusionner sans accord**.
- Dans la PR, joindre le protocole des 30 cas, les métriques, la capture Swagger RF et les limitations. Le prototype M5 reste une démonstration RAG fictive, pas une intégration métier validée.
