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

## D-011 — 2026-11-07 — Configuration locale de l'application

- Le propriétaire demande de configurer `.env` avec son accès PostgreSQL local.
- Vérification : connexion disponible sur le serveur système ; rôle sans droit
  CREATEDB et aucune base applicative distincte existante.
- Utiliser la base locale existante dans le schéma dédié `jobhunter_app`, via
  DATABASE_SCHEMA déjà supporté. Les fixtures continuent dans leurs schémas
  aléatoires dédiés. Aucun changement du modèle, du moteur ou des tables existantes.
- Secrets JWT/chiffrement générés ou préservés, ancien `.env` sauvegardé localement,
  migrations appliquées dans le seul schéma applicatif. Tous ces fichiers privés
  restent ignorés par Git. Aucun secret n'est reproduit ici.
- Vérifications réelles : settings et schéma actifs corrects, santé API 200,
  compte non authentifié 401, origine HTTPS frontend acceptée.
- Compte propriétaire absent : création interactive à effectuer par l'utilisateur.
- Il s'agit de la configuration de développement locale ; la séparation en une
  base applicative propre sera à prévoir avant tout déploiement durable.

## D-012 — 2026-11-07 — Projet exclusivement local, sans Docker

- Instruction propriétaire : « pour docker pas besoin on reste en local ».
- Cette décision remplace le report provisoire D-005 : Docker et Compose ne
  seront pas implémentés ; images, scans d'images, registres et hébergement
  ne sont plus des livrables ou prérequis de validation de ce projet local.
- Conserver Python 3.11, Angular et PostgreSQL locaux, le worker séparé partageant
  le code Python et la queue PostgreSQL prévue. Aucun changement du modèle auth.
- Conserver les tests, migrations, secrets privés et HTTPS local déjà en place.
- SPEC reste une copie immuable ; cette instruction utilisateur prévaut sur ses
  exigences de conteneurisation et de déploiement. Les anciens rapports décrivent
  l'état historique ; les consignes et le plan actuels reflètent cette décision.
- Le propriétaire a également confirmé avoir testé la connexion avec succès.

## D-013 — 2026-11-07 — Phase 1 validée et préparation de la phase 2

- Le propriétaire demande « contenue » après confirmation de la connexion locale.
- Interprétation : accepter la livraison locale de phase 1 et préparer le plan
  suivant, avec Docker/hébergement hors périmètre selon D-012.
- Le plan de phase 2 reste PROPOSED : la règle AGENTS/SPEC demande son approbation
  avant le code. Aucun module, migration, dépendance ou connecteur ajouté ici.
- La modification préexistante de `frontEnd/jobhunter/angular.json` (analytics
  désactivé) est préservée et exclue du commit documentaire.
- Pré-vérification : permissions non confirmées pour les connecteurs candidats ;
  documenter les contradictions et ne pas activer de collecte sur cette base.

## D-014 — 2026-11-07 — Phase 2 approuvée

- Le propriétaire répond « oui vasi » au plan `PLAN-PHASE-2.md`.
- Accord pour les modules sources/listings minimaux, nouvelles migrations,
  principal de requête, import manuel et page Sources décrits dans ce plan.
- Continuer sans Docker/hébergement ; préserver le changement angular.json existant.
- Les vérifications de connecteurs restent obligatoires et indépendantes du toggle.

## D-015 — 2026-11-07 — Sources manuelles choisies par le propriétaire

- Après avoir envisagé JobTech/Jobicy, le propriétaire choisit explicitement
  « LinkedIn + Indeed en liens/import manuel », puis ajoute les sites tunisiens.
- Cette instruction remplace le choix provisoire JobTech/Jobicy et l'objectif
  de deux collectes automatiques pour cette livraison : LinkedIn, Indeed, Keejob
  et Tanitjobs en liens/import manuel, avec ajout de sources personnalisées.
- Aucun connecteur HTTP fournisseur n'est développé/activé à cette phase.
  Le contrat générique conserve une erreur explicite si fetch automatique est demandé.
- La recherche approfondie JobTech/Jobicy/Himalayas reste documentaire uniquement.
- L'import persistant et le registre/page Sources du plan approuvé restent à réaliser.

## D-016 — 2026-11-07 — Livraison manuelle de phase 2

- D-014/D-015 sont implémentées : quatre sites, sources personnalisées, liens,
  import explicite et CSV, sans transport fournisseur ni collecte automatique.
- Le toggle mémorise une sélection personnelle ; aucune autorisation de collecte
  n’en découle. Dernière synchronisation et compteurs restent inconnus.
- Le point de composition raccorde les interfaces publiques sources/listings via
  SourceReference ; leurs repositories et tables ne sont pas importés entre modules.
- Les aperçus CSV omettent les champs absents (`exclude_unset`) : un réimport
  incomplet n’efface pas des compétences ou preuves de visa déjà renseignées.
- URL originale et première découverte restent immuables ; la déduplication
  exacte normalisée est atomique. Fusion floue et reposts restent pour la phase 3.
- Validation exécutée : 81 tests backend, 18 Angular et 7 E2E, plus build/types,
  lint/mypy, migration et audits. Le rapport clôt la phase avant validation owner.

## D-017 — 2026-11-07 — Validation de la phase 2

- Après le rapport, le propriétaire répond « oui cv » : son « oui » valide la
  livraison de phase 2. Aucun nouveau code ni changement de périmètre autorisé
  n’est déduit de l’abréviation « cv ».
- Clarification demandée : continuation vers le plan de phase 3, ou priorité à
  la gestion des CV. Attendre ce choix avant de préparer le plan correspondant.

## D-018 — 2026-11-07 — Continuation vers la phase 3

- Le propriétaire précise : « Ça va, continuer avec la phase 3 ». La gestion
  des CV conserve sa place en phase 4 ; l’ambiguïté de D-017 est levée.
- Plan concret préparé dans PLAN-PHASE-3.md, statut PROPOSED avant code selon
  AGENTS.md/SPEC §24.1. L’accord de continuation ne vaut pas approbation anticipée
  de ses choix détaillés de tables, déduplication ou exécution locale.
- Proposition à approuver : rechercher parmi les imports existants, garder les
  fournisseurs en manuel selon D-015, file PostgreSQL et provenance additives,
  sans collecte, score IA, CV ou notifications simulés.
