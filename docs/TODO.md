# TODO

## Prochaine action

- Phase 1 locale validée par continuation du propriétaire.
- Faire approuver `PLAN-PHASE-2.md` avant implémentation, selon AGENTS/SPEC §24.1.
- Compléter les vérifications de `sources/preverification-phase-2.md` ; conserver
  les candidats non confirmés en lien/import. Ne pas promettre deux sources déjà permises.

## Points à traiter avant ou pendant la phase 1

- Dépôt racine initialisé ; maquette imbriquée exclue et préservée.
- Dossier normalisé en `backend`, environnement Python 3.11.9 opérationnel.
- Dépendances verrouillées, lint/typage/tests locaux passés ; voir rapport backend.
- Docker, Compose, scans d'images et hébergement retirés du périmètre par D-012.
- Exécuter la CI préparée sur GitHub et vérifier PostgreSQL 16 ; seuls les tests
  locaux PostgreSQL 17.10 ont été exécutés.
- Configuration locale `.env` réalisée avec schéma applicatif `jobhunter_app`,
  secrets privés et migration initiale appliquée. Le propriétaire confirme une
  connexion réussie depuis le frontend ; cette configuration fonctionne en local.
- Conserver la séparation des schémas applicatif et tests ; envisager une base
  applicative distincte en cas d'évolution des usages, sans bloquer le mode local.
- Résoudre les points techniques du rapport avant le code concerné : isolation
  du parseur, DOC historique et gestion des secrets Telegram. HTTPS local est livré.

## Frontend livré et suites

- Layout, connexion, compte et FR/EN livrés sous Angular 22 standalone.
- 14 tests Karma et 5 parcours Playwright réussis ; captures desktop/mobile
  inspectées après correction CSP/styles et focus du menu mobile.
- GitHub CI complète préparée (frontend + backend + E2E) mais non exécutée.
- Conserver l'illustration commerciale et la référence hors du dépôt public ;
  clarifier les droits avant toute redistribution du template. Police Poppins OFL.
- Développer les vrais compteurs/offres du dashboard avec les API métier futures.

## Phases ultérieures et dépendances externes

- Vérifier chaque API/feed et ses conditions avant écriture de son connecteur.
- Obtenir les accès nécessaires ; aucune clé ni autorisation n'est présumée.
- Préparer dix CV anonymisés avec résultats attendus ; aucune donnée réelle reçue.
- Constituer cinquante offres réelles anonymisées et faire labelliser les matches
  par le propriétaire. Ne pas inventer ces labels pour faire passer la CI.
- Définir les seuils d'extraction et de calibration non encore convenus.
- Vérifier `linkedin_email` séparément ; le garder désactivé jusque-là.
- Tester sauvegarde/restauration, reprise worker, déduplication et notifications
  idempotentes dans leurs phases respectives.

## Limites actuelles

- Authentification, connexion navigateur et compte sont reliés et testés.
- Worker sans file ni handlers de recherche ; modules métier des phases suivantes absents.
- Aucun connecteur activé et aucune vérification juridique encore réalisée.
