# Changelog

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
