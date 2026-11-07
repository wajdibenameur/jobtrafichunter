# TODO

## Prochaine action

- Phase 2 validée par le propriétaire (D-017). Clarifier « cv » : continuation
  vers le plan de phase 3 ou priorité à la gestion des CV. Préparer ensuite le
  plan correspondant et le faire approuver avant le code.
- D-015 : LinkedIn, Indeed, Keejob et Tanitjobs en liens/import manuel ; aucune
  collecte automatisée attendue dans cette livraison. Ajout de sites personnalisés disponible.

## Fonctionnalités à venir

- Critères de recherche, profils, orchestrateur, queue PostgreSQL, reprise worker,
  déduplication floue, republications et page Résultats : phase 3 à planifier.
- CV privés, parsing isolé, DOC historique, validation des champs : phase 4.
- Matching explicable et extraction IA : constituer dix CV anonymisés avec
  résultats attendus, puis cinquante offres anonymisées labellisées par le
  propriétaire. Aucun label de calibration ou résultat réel ne doit être inventé.
- Fixer les seuils d’extraction/calibration avec le propriétaire.
- Vérifier linkedin_email séparément avant toute activation ; consentement et
  accès boîte mail non présumés. Telegram, planification et historique à venir.
- Remplacer les états « Bientôt » et les compteurs indisponibles du dashboard
  lorsque les API de recherche/matching existent réellement.

## Vérifications et exploitation

- GitHub CI préparée, non exécutée ; PostgreSQL 16 non testé. Vérifications locales
  réalisées avec PostgreSQL, Python 3.11 et le Node portable du projet.
- Configuration locale .env dans le schéma applicatif jobhunter_app, secrets privés.
  Conserver la séparation avec la base .env.test et les schémas jetables des tests.
- Tester sauvegarde/restauration et notifications idempotentes dans leurs phases.
- SPEC reste immuable. Docker, Compose, images et hébergement hors périmètre D-012.
- Les droits du template commercial doivent être clarifiés avant redistribution ;
  la référence/illustration restent locales, Poppins est sous OFL.
- Changement utilisateur analytics:false dans angular.json conservé hors commits.

## Sources automatisées éventuelles

- Aucun fournisseur automatisé livré ou activé. Les candidats documentaires
  Remotive, Arbeitnow, JobTech, Jobicy/Himalayas n’accordent aucun accès implicite.
- Si le propriétaire redemande une collecte automatique : vérifier documents,
  conditions, robots, accès, stockage/attribution et quotas avant son code.
  Prévoir alors transport, cache, timeouts, pagination, retries et tests réseau.
- La génération de liens ne garantit pas la pertinence des résultats externes.
