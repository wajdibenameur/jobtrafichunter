# Changelog

- 2026-11-08 — D-032 : lot 4 validé par continuation ; plan détaillé Scraping lot 5
  enregistré (interfaces, sept tables annexes/trois migrations, transaction atomique,
  budgets durables et tests simulés). Proposition seulement, accord attendu avant
  code/migrations ; aucune collecte ni nouvel appel réseau, SPEC inchangée.

- 2026-11-08 — D-031 : lot 3 validé, lot 4 Angular Scraping/filtres communs livré :
  profils réels sauvegardés, statuts/historique locaux, radios horaires strictes
  et compatibilité des profils historiques ; collecte non configurée explicitée.
  248 backend, 33 Angular, 11 E2E réussis ; typage/build/Ruff/mypy/Alembic verts,
  trois captures desktop/mobile inspectées. Aucune migration/dépendance/source activée.

- 2026-11-08 — D-030 : lot 2 validé, extraction générique JSON-LD lot 3 livrée :
  graphes/références locales, texte sûr, lieux/contrats, dates à précision conservée,
  provenance, avertissements et pagination sous autorisation. 38 nouveaux tests,
  219 backend réussis, Ruff/format/mypy/Alembic/audit verts ; aucune migration,
  activation fournisseur ou collecte réelle. Validation attendue avant lot 4.

- 2026-11-08 — D-029 / Scraping lot 2 livré : contrat paginé additif, registre
  interne sans fournisseur actif, transport HTTP IP épinglée/TLS, permissions
  revérifiées, quotas/retry/budgets et décompression bornée. 50 nouveaux tests,
  181 backend réussis, Ruff/format/mypy/Alembic/audit runtime verts. Aucune
  migration, UI, collecte réelle ou activation ; validation attendue avant lot 3.

- 2026-11-08 — D-028 : audit Scraping Engine, revue officielle des sources et
  plan proposé en huit lots enregistrés ; README, plan AI Job Agent, consignes
  agents, décisions, TODO et PROGRESS raccordés. Documentation uniquement :
  aucun collecteur, migration, dépendance, source PERMITTED ou run réel ajouté.

- 2026-11-08 — D-027 : audit AI Job Agent et plan en sept lots enregistrés ;
  README, AGENTS/CLAUDE, décisions, TODO, rapports et PROGRESS synchronisés.
  Accord documentaire uniquement, phase 4 en attente de validation et nouveau
  plan PROPOSED. Audit : 131 backend, 24 Angular, 10 E2E, contrôles statiques,
  build et Alembic réussis ; aucun nouveau code, migration ou appel payant.

- 2026-11-08 — Phase 4 livrée (D-026) : CV PDF/DOCX chiffrés/versionnés, inspection
  AppContainer, intentions/reprise et audit, profils candidats avec preuves,
  brouillons/validation/activation et page Angular Mes CV FR/EN/mobile. Migrations
  additives 0007–0008 appliquées, 131 tests backend, 24 Angular et 10 E2E réussis,
  Ruff/mypy/build/Alembic/audit runtime vérifiés. DOC/OCR indisponibles, matching
  en phase 5 ; Apify toujours reporté. Aucun CV réel ou secret ajouté au dépôt.

- 2026-11-08 — Phase 3 et plan CV validés (D-024). Fondations CV : coffre
  AES-256-GCM/HKDF immuable et lanceur Windows AppContainer sans réseau avec
  limites Job Object, copie locale de Python sans secrets et sondes natives.
  122 tests backend réussis, Ruff/format/mypy verts. Phase 4 toujours en cours ;
  aucune API d’upload, extraction métier ou interface CV annoncée disponible.

- 2026-11-08 — Choix propriétaire D-023 : reporter Apify jusqu’aux modules CV et
  matching ; plan de phase 4 proposé pour stockage privé, extraction isolée et
  validation du profil. Documentation uniquement, aucun développement ni appel
  Apify ; validation de phase 3 et approbation du plan CV encore attendues.

- 2026-11-08 — Apify Phase A : inspection de l’existant et des documents officiels,
  proposition de carte séparée dans Sources, migrations/additions et reprise sans
  relance facturable aveugle ; matching CV absent et permissions non établies
  explicités. Aucun code, secret, appel Apify utilisateur ou dépense modifié/lancé.

- 2026-11-07 — Phase 3.4 : pages Angular Profils/Recherche/Résultats et dashboard
  réel, FR/EN/mobile, progression persistante et détails/provenance ; worker E2E
  séparé et correction de son enregistrement de tables. 105 tests backend,
  21 Angular et 9 E2E réussis, audits runtime sans vulnérabilité connue ; rapport
  de phase livré, validation attendue avant phase 4.

- 2026-11-07 — Phase 3.3 : file PostgreSQL avec leases/heartbeat, reprise bornée,
  annulation, snapshots des résultats, SSE et filtres structurés hiver/été Paris.
  104 tests backend réussis, dédup 100 % et filtres 91 % couverts ; migrations
  jusqu’à 0006 appliquées, Ruff/mypy/Alembic vérifiés. tzdata haché ajouté sous Windows.

- 2026-11-07 — Phase 3.2 : provenance additive et reprise des imports, regroupement
  conservateur, candidats ambigus/reposts distincts et découverte ancienne conservée
  entre sources. 96 tests backend réussis ; algorithme dédup couvert à 100 %,
  migration 0005 appliquée et cohérence Alembic vérifiée.

- 2026-11-07 — Phase 3.1 : critères bornés, profils CRUD/duplication et exemples
  explicites idempotents, routes protégées et migration additive 0004 appliquée.
  91 tests backend réussis, Ruff/mypy et cohérence Alembic vérifiés.

- 2026-11-07 — Suite phase 3 confirmée (D-018), plan concret préparé : critères,
  profils, recherche dans les imports, déduplication additive et queue PostgreSQL.
  Approbation du plan attendue ; aucun code, dépendance ou migration exécutée.

- 2026-11-07 — Phase 2 validée par le propriétaire (D-017). Clarification de
  « cv » demandée avant de choisir la phase suivante ; aucun code modifié.

- 2026-11-07 — Phase 2.2/2.4 : page Sources FR/EN, filtres tunisiens, préférences,
  liens, sites personnalisés et confirmation URL/CSV ; registre de connecteurs
  manuels et erreurs typées. Réimport CSV sans effacer les champs absents.
  81 tests backend, 18 Angular et 7 parcours E2E réussis ; build/typecheck,
  Ruff/mypy/Alembic et audits runtime sans vulnérabilité connue. Rapport de phase.

- 2026-11-07 — Phase 2.3 : import manuel persistant et atomique, confirmation
  explicite, aperçu CSV borné, URL normalisée et première découverte conservée.
  79 tests backend réussis ; Ruff/mypy et cohérence Alembic vérifiés, migration
  0003 appliquée au schéma applicatif local.

- 2026-11-07 — Phase 2.1 : registre LinkedIn/Indeed/Keejob/Tanitjobs, préférences
  propriétaire, sources personnalisées, liens encodés, principal de requête,
  migration 0002 et contrat manuel sans réseau ; 64 tests backend réussis.

- 2026-11-07 — Phase 1 locale validée par continuation ; plan de phase 2 et
  pré-vérification documentaire des sources créés, sans code ni collecte.
  Contradictions Remotive et limites Arbeitnow consignées ; aucun candidat activé.

- 2026-11-07 — Étape 0 : lecture du cahier des charges et de la section 27 ; copie
  exacte dans SPEC.md, création des consignes agents, du suivi, du rapport initial,
  du plan de phase 1 et du modèle de vérification des sources ; analyse Velson
  reportée au frontend sur instruction du propriétaire. Vérifications documentaires
  détaillées dans `reports/phase-0.md` ; aucune fonctionnalité applicative livrée.
- 2026-11-07 — Phase 1, lot backend : Python 3.11, structure FastAPI modulaire,
  auth propriétaire Argon2id/cookies/rotation/verrouillage, migration PostgreSQL,
  limites de corps et origine, HTTPS local, worker de base, dépendances verrouillées,
  CI préparée. 43 tests réussis, couverture 85.32 %, Ruff/mypy passés, audit runtime
  sans vulnérabilité connue après mise à jour cryptography. Docker reporté.
- 2026-11-07 — Audit frontend Velson documenté (pages, composants, tokens, assets,
  écrans manquants et risques), sans modification du template ; validation attendue.
- 2026-11-07 — Tests d'intégration exécutés avec `backend/.env.test` configuré par
  le propriétaire : 9 passed, 34 deselected en 17.78 s ; aucun secret affiché,
  aucun changement du code applicatif.
- 2026-11-07 — Phase 1, lot frontend : Angular 22 standalone strict, layout Velson,
  connexion/compte FastAPI, session par cookies avec refresh partagé, FR/EN,
  navigation mobile accessible, TLS/proxy local, thème et Poppins OFL ; build/types
  validés, 14 tests Karma et 5 parcours Playwright réussis. CI étendue et référence
  préservée ; Docker reporté. Corrections réelles CSS/CSP et retour de focus mobile.
- 2026-11-07 — Configuration locale `.env` à la demande du propriétaire : secrets
  générés/préservés, schéma `jobhunter_app`, migration appliquée, santé API 200 et
  accès protégé 401 vérifiés ; compte propriétaire à créer interactivement.
- 2026-11-07 — Décision propriétaire D-012 : projet exclusivement local ; Docker,
  Compose, images et hébergement retirés du périmètre. Consignes et plan adaptés ;
  connexion frontend/backend confirmée par le propriétaire. Aucun code modifié.
