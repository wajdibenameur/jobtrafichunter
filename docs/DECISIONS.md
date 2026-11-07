# Decisions

## D-001 — 2026-11-07 — Référentiel du projet

- Décision : conserver une copie exacte du document fourni dans `docs/SPEC.md`.
- Alternatives : reformuler le document ou conserver uniquement un lien externe.
- Motif : référentiel local durable, sans modification du cahier des charges.
- Autorisation : demande utilisateur de lire la section 27 et de créer les fichiers.
- Vérification : comparaison SHA-256 entre le fichier fourni et sa copie.

## D-002 — 2026-11-07 — Report de l'analyse Velson

- Décision : reporter l'analyse détaillée et la validation de la maquette au début
  du travail frontend. Ne modifier aucun fichier du template pendant le démarrage.
- Alternative : réaliser immédiatement l'audit demandé en sections 3 et 27.2.
- Motif : instruction explicite du propriétaire dans la conversation.
- Approbation : propriétaire, « LAISSE MAQUETE VELSON LORSQUE TU COMMANCE EN FRONTEND ».
- Conséquence : l'étape 0 porte sur les documents et l'état du projet. L'audit
  visuel reste à réaliser, sans être présenté comme terminé.

## D-003 — 2026-11-07 — Arbitrages proposés, non approuvés

Les propositions techniques de `docs/reports/phase-0.md` et du plan de phase 1
restent des propositions. Aucune modification d'architecture, installation de
dépendance, initialisation Git ou activation de connecteur n'a été réalisée.

## D-004 — 2026-11-07 — Démarrage autorisé

- Approbation du plan de phase 1 par le propriétaire : « DONC COMMANCER ».
- Le socle démarre par le backend ; Velson reste réservé au lot frontend.
- Les propositions des phases suivantes restent à traiter au moment concerné.

## D-005 — 2026-11-07 — Python 3.11 et Docker différé

- Instruction propriétaire : « USE PYTHON 3.11 VERSION LAISSE DOCKER APRES ».
- Décision : exécuter le backend avec Python 3.11 local ; reporter les fichiers,
  démarrages et validations Docker. SPEC reste inchangé ; cette dérogation prévaut.
- La tentative de téléchargement 3.12 lancée avant cette instruction était déjà
  terminée ; cette version ne sera pas utilisée pour le projet.
- PostgreSQL reste le moteur prévu. Le service local observé est PostgreSQL 17 ;
  aucun accès ni changement à ses bases existantes n'est présumé.

## D-006 — 2026-11-07 — Vérifications locales PostgreSQL sans Docker

- Décision : utiliser les binaires PostgreSQL 17 déjà installés pour une instance
  de test isolée sous `.cache/postgres-tests`, avec port et identifiants propres.
- Alternative : attendre les identifiants de la base de test configurée par le
  propriétaire. Le helper ne modifie ni `.env.test` ni le serveur système.
- Motif : vérifier immédiatement migrations, concurrence et sécurité sans Docker.
- Autorisation : développement et tests locaux du plan approuvé ; démarrage du
  processus autorisé via l'outil après une restriction initiale du sandbox.
- Limite : les résultats locaux concernent PostgreSQL 17.10 ; PostgreSQL 16 doit
  encore être vérifié par la CI préparée, qui n'a pas été exécutée sur GitHub.
- Les tests utilisent chacun un schéma aléatoire dédié, supprimé après usage.

## D-007 — 2026-11-07 — Correctif de dépendance de sécurité

- L'audit initial a signalé des avis de vulnérabilité sur cryptography 48.0.1.
- Mise à jour vers 50.0.2, verrous et hashes régénérés, tests relancés.
- Nouvel audit runtime : aucune vulnérabilité connue détectée.
- Aucun changement du modèle de chiffrement ou de l'architecture.

## D-008 — 2026-11-07 — Démarrage du lot frontend

- Instruction propriétaire : « contenue », après le rapport Velson et les tests DB.
- Interprétation : poursuivre le lot frontend du plan déjà approuvé et reprendre
  le layout/connexion suivant le rapport d'audit. Référence originale inchangée.
- Application distincte sous `frontEnd/jobhunter`, exécution locale uniquement ;
  aucune publication, aucune modification du moteur DB ou des cookies d'auth.
- Les fichiers commerciaux du template restent locaux et ignorés par Git.

## D-009 — 2026-11-07 — Compatibilité Angular vérifiée

- Versions stables vérifiées sur le registre npm : Angular 22.2.5, CLI 22.2.6.
- Le Node système 22.21.1 est inférieur au minimum demandé (22.22.3).
- Utiliser un Node 22.22.3 portable sous `.tools`, sans remplacer Node global.
- Source : https://angular.dev/reference/versions ; métadonnées npm officielles.
- Conforme à la demande Angular stable du SPEC et au plan approuvé. Aucune
  migration ou altération de l'application de référence Angular 18.

## D-010 — 2026-11-07 — Assets et preview local

- Reprendre la palette/dimensions du template dans des composants SCSS/Angular.
  Copier localement seulement l'illustration fournie, dans un dossier ignoré.
- Poppins est servi localement avec sa licence OFL, depuis le dépôt Google Fonts.
  Aucun bundle JS vendor, page de démo ou fichier commercial n'est commité.
- La CI utilise un remplacement d'illustration lorsque le template privé manque.
- Les tests navigateur emploient le build de production et un preview HTTPS
  loopback avec proxy vers FastAPI. Ce helper de développement n'est ni un nouveau
  service déployable ni une modification de l'architecture de production.
- Le CSS critique à gestionnaire inline généré par Angular est désactivé pour
  respecter la CSP, plutôt que permettre du JavaScript inline.
- Les identifiants du propriétaire E2E sont jetables ; le schéma et leur fichier
  sont supprimés après le test. Aucune donnée propriétaire réelle n'est modifiée.
