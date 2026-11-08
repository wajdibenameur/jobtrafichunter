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

## D-019 — 2026-11-07 — Plan de phase 3 approuvé

- Le propriétaire répond « vasi » après présentation de PLAN-PHASE-3.md.
- Accord pour les lots 3.1–3.4 et migrations additives 0004–0006 : profils,
  recherche des imports, provenance/déduplication conservatrice, worker/queue,
  progression et pages Angular. Continuer sans nouvelle confirmation de ce plan.
- Les limites D-015 et du plan restent applicables : aucun accès fournisseur,
  CV, matching IA ou notification simulé. Conserver les tables existantes.

## D-020 — 2026-11-07 — Fuseaux horaires et exécutions locales

- Le plan approuvé exige « aujourd’hui » Europe/Paris ; ZoneInfo seul échoue
  sur le Windows local sans base de fuseaux système. Ajouter le paquet de données
  tzdata (aucun framework/service), verrouillé et haché sans autres mises à jour.
- Documentation officielle consultée : https://pypi.org/project/tzdata/ et
  https://tzdata.python.org/ ; paquet de repli IANA pour zoneinfo, version résolue
  2026.6. Contrôler hiver/été dans les tests, sans coder un décalage UTC fixe.
- Les états de collecte restent SKIPPED/MANUAL_ONLY. Les tâches effectuent
  uniquement scan local, déduplication, filtrage et snapshots de résultats.

## D-021 — 2026-11-07 — Livraison de la phase 3 locale

- Lots 3.1–3.4 du plan D-019 livrés, migrations additives 0004–0006 appliquées.
  Les imports originaux sont conservés et les résultats utilisent des snapshots.
- Bornes effectives : 500 imports récents, 100 candidats par identité. Dépassement
  explicitement PARTIAL ; nouveauté de groupe non vérifiée si le rapprochement
  est incomplet. Aucun faux résultat exhaustif ou compteur de collecte.
- L’E2E avec worker distinct a exposé un défaut masqué par le chargement de l’API
  dans les tests : références ORM non enregistrées dans ce processus. Imports
  publics au point de composition, test dédié de worker neuf et E2E verts.
- Livraison vérifiée : 105 tests backend, 21 Angular et 9 E2E ; rapport phase-3.md.
  Attendre la validation avant de proposer le plan CV de phase 4.

## D-022 — 2026-11-08 — Apify : analyse de Phase A uniquement

- Le propriétaire demande une intégration LinkedIn Jobs via l’API Apify, selon
  trois étapes : A inspection/plan maintenant, B après accord, C test réel de
  dix offres après validation et autorisation financière explicite. Aucune
  activation, implémentation, dépense ou modification des secrets autorisée en A.
- Cette demande ouvre l’étude d’une source automatisée supplémentaire ; elle
  ne supprime pas D-015 ni l’interdiction de scraping LinkedIn dans AGENTS/SPEC.
  Les quatre modes manuels et la recherche locale doivent rester disponibles.
- Recommandation, pas encore approuvée : carte « LinkedIn — Apify » distincte
  dans Sources, composant dédié, suivi/résultats communs. Une page/menu séparé
  dupliquerait le parcours ; fusionner avec LinkedIn manuel masquerait la facturation.
- Inspection : matching CV non implémenté. Ne pas prétendre le réutiliser ;
  statut indisponible et choix de périmètre explicite avant B. Pas de CV vers Apify.
- Conditions/robots officiels consultés dans docs/sources/linkedin-apify.md :
  aucune permission établie pour un Actor précis, aucun statut PERMITTED attribué.
- Plan concret : docs/reports/apify-phase-a.md, migration additive proposée,
  consentement unitaire, run_id/checkpoints et arrêt en cas de lancement incertain.
  Aucun outil Apify exposé dans cette session ; aucune dépendance Codex envisagée
  pour le fonctionnement de l’application. Aucune conclusion sur le MCP local.
- La validation de la livraison générale de phase 3 reste en attente ; ne pas
  interpréter cette demande de fonctionnalité comme validation implicite ou phase 4.

## D-023 — 2026-11-08 — Apify reporté après CV et matching

- Après « contenue », reprise du plan Apify et lecture du code, sans modification
  applicative ni migration. Avant l’implémentation, clarification du périmètre
  car le plan A constate que CV/matching n’existent pas encore.
- Le propriétaire choisit explicitement « Attendre les modules CV et matching »,
  plutôt qu’une première version de collecte sans matching. Ce choix reporte
  l’ensemble de l’implémentation Apify B ; ne pas livrer silencieusement une
  variante collecte seule ou poursuivre le client/la carte à sa place.
- Préparation documentaire de `PLAN-PHASE-4.md` : stockage CV privé, extraction
  locale isolée, versions et profil candidat validé ; matching en phase 5.
  Ce plan reste PROPOSED. Aucun module CV/matching n’est prétendu disponible.
- La phase 3 attend toujours sa validation et le plan de phase 4 son approbation
  selon AGENTS.md/SPEC §24. Le choix d’attendre n’autorise pas leur code.
- Le plan Apify A et les preuves de source restent conservés. Revoir ensuite
  leur intégration au matching réel et les conditions de l’Actor avant reprise B.
  Aucun appel Apify authentifié/facturable, secret ou fichier applicatif modifié.

## D-024 — 2026-11-08 — Phase 3 validée et plan CV approuvé

- À la question explicite de valider la phase 3 et `PLAN-PHASE-4.md`, le
  propriétaire répond « ok ». Les deux validations sont acquises ; ne pas les
  redemander. Le plan de phase 4 est autorisé, Apify reste reporté selon D-023.
- Commencer par le coffre privé de CV et les tests d’intégrité/immutabilité.
  La clé existante est consommée via Settings, jamais modifiée ou affichée.
- Revue officielle : AESGCM/HKDF de cryptography et isolation AppContainer de
  Microsoft. Pas de nouvelle dépendance pour le coffre ; cryptography existe.
  Sources : https://cryptography.io/en/latest/hazmat/primitives/aead/ et
  https://learn.microsoft.com/en-us/windows/win32/secauthz/implementing-an-appcontainer.
- Sonde locale : Python 3.11.9 ; API CreateAppContainerProfile présente ; aucun
  WindowsSandbox.exe, Tesseract, soffice ou antiword trouvé dans PATH. Cela ne
  prouve pas l’impossibilité d’AppContainer, ni l’existence d’une sandbox prête.
  Aucune extraction de document non fiable dans un subprocess ordinaire.

## D-025 — 2026-11-08 — Extraction locale PDF/DOCX bornée

- Dans le plan CV approuvé, utiliser pypdf 7.x pour les PDF textuels, uniquement
  dans le runtime AppContainer testé. Bibliothèque Python pure, BSD-3-Clause,
  Python >=3.10 (compatible 3.11), sans nouveau service. Dépendance verrouillée
  avec hashes. Références officielles : https://pypi.org/project/pypdf/,
  https://github.com/py-pdf/pypdf/blob/main/LICENSE et
  https://pypdf.readthedocs.io/en/stable/user/extract-text.html.
- La documentation avertit de consommations mémoire importantes et de l’absence
  d’OCR ; garder les limites Job Object, pages/texte et durée. Pas de PDF chiffré,
  JavaScript/actions actives, pièces jointes ou exécutables acceptés.
- DOCX : lecture ZIP/XML bornée dans le même environnement isolé, sans Word,
  macro, conversion ou téléchargement de liens. Validation structurelle requise.
- DOC historique et OCR : outils non présents ; capacité indisponible visible,
  pas de parsing hors sandbox ni prétention de support complet.

## D-026 — 2026-11-08 — Livraison locale de phase 4

- Lots CV/profil du plan D-024 livrés avec migrations additives 0007 et 0008,
  sans altérer les tables/migrations antérieures. Python 3.11 et le worker unique
  conservés ; sa maintenance reprend les intentions de stockage, pas une seconde
  infrastructure. UI Mes CV dans le shell Velson existant, FR/EN/mobile.
- Upload binaire avec en-tête de nom UTF-8 encodé, plutôt qu’ajouter multipart ;
  signature/structure inspectées dans AppContainer avant publication. Original,
  nom, texte et profil chiffrés, preuves séparées des corrections/préférences.
- Installation/runtime Windows AppContainer vérifiés par sondes réelles ; limites
  Job Object, refus d’écriture dans le runtime et dans son dossier de profil.
  Compilation et ACL de cette ressource dédiée approuvées par l’exécution locale
  des outils ; aucun changement de droits du Python original, de service ou de réseau global.
- Les données de formation/expérience restent des sections à relire, pas une
  interprétation sémantique calibrée de dates/années. Matching et modes CV/hybride
  de recherche restent indisponibles en attendant la phase 5. Aucun LLM externe.
- Validation courante : 131 tests backend, 24 Angular, 10 E2E, Ruff/mypy/build,
  migrations sans drift et audit runtime sans vulnérabilité connue. Rapport phase-4.md.
  Aucun CV réel/label propriétaire ou permission fournisseur fabriqué.
- La phase 4 attend sa validation avant le plan matching. D-023 reste en vigueur :
  ne pas reprendre Apify sur la seule disponibilité des CV ; matching et permission
  d’Actor restent nécessaires, puis l’autorisation C distincte avant tout run réel.

## D-027 — 2026-11-08 — Audit AI Job Agent et mise à jour documentaire seulement

- Demande : auditer l'extension recherche récente, matching, alertes, CV adapté,
  lettre et dossier de candidature avant tout développement. L'audit a été rendu
  dans la conversation sans modifier le code ni les documents.
- Après clarification, le propriétaire demande « ouii ffaire mise ajour de toute
  document necessaiee ». Autorisation acquise pour enregistrer l'audit, le plan
  proposé et synchroniser les documents nécessaires, dont AGENTS/CLAUDE/PROGRESS.
- Cet accord documentaire ne valide ni la livraison de phase 4 ni le nouveau
  plan d'implémentation. Aucun nouveau lot, module, migration, dépendance ou
  connecteur n'est autorisé par cette seule mise à jour.
- Évidence de l'audit : 131 tests backend en 148,13 s, 24 Angular, 10 E2E en
  30,2 s, Ruff/format/mypy/typecheck/build réussis, Alembic à 0008 sans drift.
- Constats : matching/notifications/applications/documents absents ; les CV
  originaux et profils validés existent. Publication par défaut toutes dates,
  inconnus inclus selon préférence ; ne pas présenter les nouveaux filtres stricts
  ou le défaut 24 h comme déjà implémentés. Les dates importées ne prouvent pas
  une vérification indépendante de publication auprès d'un fournisseur.
- Proposition conservée dans PLAN-AI-JOB-AGENT.md : sept lots sur le monolithe
  et le worker existants, migrations additives seulement si nécessaires,
  module documents proposé et frontières à approuver, IA payante non obligatoire.
  Alternative écartée au stade du plan : reconstruire ou dupliquer les moteurs.
- D-012/D-015/D-023 restent applicables : local sans Docker, quatre sites manuels,
  Apify différé après CV/matching, permission vérifiée et accord C distinct.
- SPEC conservé intact. Historique préservé ; correction des états documentaires
  obsolètes plutôt que création de PHASE1.md/PHASE2.md en doublon.

## D-028 — 2026-11-08 — Scraping Engine : audit enregistré, code non approuvé

- Nouvelle demande : audit préalable d'un moteur Python indépendant d'Apify,
  page Scraping, connecteurs extensibles, collecte permise puis matching/alertes.
  Rapport d'audit et proposition en huit lots rendus dans la conversation.
- Après le rapport, le propriétaire demande « ouui ajouté au fichier ».
  Interprétation limitée à l'ajout de l'audit/plan et aux mises à jour de suivi ;
  aucun accord d'implémentation, de dépendance, de migration ou de collecte réelle.
  La livraison de phase 4 reste en attente de validation.
- Fichiers : reports/scraping-engine-audit.md, PLAN-SCRAPING-ENGINE.md et
  sources/scraping-review.md ; liens/suivi synchronisés. SPEC immuable.
- Architecture proposée : étendre les contrats et le registre sources, la queue
  search et le worker existants. Alternative écartée dans le plan : second moteur,
  second worker ou Protocol concurrent. Contrats précis à approuver avant code.
- Évidence : 131 tests collectés en 1,05 s, Ruff et mypy (97 fichiers) réussis
  pendant l'audit ; les dernières suites complètes restent celles de D-027.
  Ne pas confondre collecte de tests et exécution. Aucun test réel de collecteur absent.
- Revue officielle détaillée dans sources/scraping-review.md : LinkedIn interdit
  le scraping sans autorisation ; portée Indeed à vérifier ; Keejob documente
  Markdown/RSS sans établir tous les droits de réutilisation ; Tanitjobs ne permet
  pas d'établir une permission complète de collecte périodique. Robots Tanitjobs
  inaccessible via l'outil. Aucun statut PERMITTED attribué ni source activée.
- Greenhouse/Lever : candidats techniques par board, pas permission universelle.
  Pas de cookies privés, identifiants LinkedIn, contournement ou visite automatisée
  d'annonces sous prétexte de tester une source non approuvée.
- Les lots communs aux deux plans (filtres, matching, notifications, documents)
  seront réalisés une seule fois après accord. D-012/D-015/D-023 conservées :
  local sans Docker, imports manuels préservés, Apify différé et accord C distinct.
