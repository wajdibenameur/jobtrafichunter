# Publication GitHub

Date : 2026-11-09. Décision : D-034.
Dépôt : [wajdibenameur/jobtrafichunter](https://github.com/wajdibenameur/jobtrafichunter).
Visibilité publique confirmée explicitement par le propriétaire.

## Résultat

- Remote origin configuré sur le dépôt fourni ; branche main suivie par origin/main.
- Historique existant conservé, sans force-push ni réécriture.
- Base CV/versionnement du profil : commit 2b34645, incluant les migrations 0007/0008.
- Collecte simulée/queue/checkpoints/budgets : commit 56ba4f9, migrations 0009–0011.
- Push initial réussi et SHA distant comparé au SHA local :
  56ba4f9da79ed8cb855c15b4e7d8096ec26f2ee2. Documentation de publication ajoutée à la suite.
- Les validations fonctionnelles de phase 4 CV et de livraison du lot 5 restent
  distinctes de la demande de publication ; aucun lot suivant n'est autorisé ici.

## Contrôles

Avant versionnement, 267 fichiers de travail et 535 blobs de l'historique examinés :
motifs de clés privées/tokens et comparaison en mémoire avec les valeurs des secrets
locaux. Aucune correspondance sensible détectée après exclusion d'un CHANGE_ME
documenté dans une ancienne sauvegarde d'environnement. Aucun secret affiché.
Ce contrôle ciblé ne remplace pas une rotation ou un audit exhaustif.

Les exclusions .gitignore sont vérifiées : .env et variantes locales, CV/base locale,
clés TLS, caches, outils, environnements Python, node_modules, sorties de build,
captures de tests et template commercial Velson. Aucun PDF/DOCX privé ou clé TLS
dans l'historique envoyé. Les exemples de configuration et fixtures synthétiques
restent versionnés ; aucun secret ni contenu de CV réel ajouté.

Ruff check/format, mypy (109 fichiers) et typage Angular app/spec/E2E relancés avec
succès pour cette préparation. Les suites déjà exécutées sur ce code restent
272 backend, 37 Angular et 12 Playwright ; aucune modification applicative dans
la seule préparation Git. SPEC inchangée, aucun collecteur réel ou payant activé.

## CI et usage local

Des exécutions GitHub Actions ont démarré au premier push. Lors de la consultation,
elles étaient en cours ; aucune réussite CI distante n'est revendiquée.
[Résultats actuels](https://github.com/wajdibenameur/jobtrafichunter/actions).

L'application reste locale : le push n'héberge pas FastAPI ou Angular. Pour un
nouveau clone, suivre les README, créer ses propres secrets/base/TLS et appliquer
les migrations. Sans copie privée du template, utiliser JOBHUNTER_TEMPLATE_OPTIONAL=1
pour l'illustration CSS de remplacement ; ne pas publier le template commercial.
La base personnelle n'a pas été migrée pendant cette opération.
