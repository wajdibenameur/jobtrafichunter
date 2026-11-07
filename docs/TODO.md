# TODO

## Prochaine action

- Faire valider `reports/velson-audit.md` avant le code frontend, conformément à
  SPEC §3. Le lot backend de phase 1 est testé ; la phase entière reste ouverte.

## Points à traiter avant ou pendant la phase 1

- Dépôt racine initialisé ; maquette imbriquée exclue et préservée.
- Dossier normalisé en `backend`, environnement Python 3.11.9 opérationnel.
- Dépendances verrouillées, lint/typage/tests locaux passés ; voir rapport backend.
- Docker, Compose, scans images et déploiement reportés par le propriétaire.
- Exécuter la CI préparée sur GitHub et vérifier PostgreSQL 16 ; seuls les tests
  locaux PostgreSQL 17.10 ont été exécutés.
- Configurer la base applicative et le propriétaire réels lors du lancement local.
  Aucune identité utilisateur ou clé de production n'a été créée automatiquement.
- Résoudre les points techniques du rapport avant le code concerné : isolation
  du parseur, DOC historique, HTTPS local et gestion des secrets Telegram.

## Frontend différé par le propriétaire

- Analyse des sources et cartographie des dix écrans disponibles dans le rapport
  Velson ; attendre validation avant reprise du layout et de la connexion.
- Vérifier le rendu dans le navigateur et obtenir les conditions de licence du
  template : aucune licence générale trouvée à sa racine pendant l'analyse.
- Vérifier les versions Angular/Node officiellement supportées au moment du choix.
- Préserver le design, migrer vers standalone et supprimer les dépendances inutiles
  seulement dans le périmètre approuvé. Ne pas publier le template sans licence.

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

- Authentification et migration exécutées en test ; pas encore d'écran connecté.
- Worker sans file ni handlers de recherche ; modules métier des phases suivantes absents.
- Aucun connecteur activé et aucune vérification juridique encore réalisée.
