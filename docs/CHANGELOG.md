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
