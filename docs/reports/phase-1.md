# Phase 1 — socle local backend et frontend

Date : 2026-11-07. Statut : WAITING_FOR_VALIDATION.
Périmètre local livré avec Python 3.11 ; Docker reste reporté par instruction du
propriétaire. La CI est préparée, mais son exécution GitHub et PostgreSQL 16 ne
sont pas revendiquées : aucun remote Git n'est configuré.

## Ce qui est livré

- Backend FastAPI et module auth propriétaire : voir `phase-1-backend.md`.
- Frontend indépendant `frontEnd/jobhunter` en Angular 22.2.5, CLI 22.2.6,
  TypeScript strict et composants standalone, avec routes chargées à la demande.
- Connexion propriétaire et compte alimentés par FastAPI, déconnexion avec
  révocation, restauration après rechargement et refresh partagé entre requêtes.
- Cookies Secure/httpOnly/SameSite=Strict conservés ; aucun jeton dans localStorage.
  Seul le choix de langue est persisté dans le navigateur.
- Layout vertical Velson, tokens indigo/bleu/vert, Poppins locale sous OFL,
  connexion en carte avec l'illustration de référence assemblée localement.
- Navigation desktop/mobile accessible : focus, raccourci Escape, retour du focus,
  arrière-plan inert et menu mobile fermé hors du parcours clavier.
- FR/EN, erreurs de connexion/verrouillage, session expirée, serveur indisponible,
  chargement, page introuvable et compte consultable avec réessai en cas d'erreur.
- Dashboard initial sans compteurs ou offres fictifs. Les fonctions métier encore
  absentes sont marquées « Bientôt » et ne déclenchent aucune action simulée.
- Helper Node portable, TLS et proxy local, preview du build de production.
- CI étendue : typage/build Angular, Karma, E2E avec PostgreSQL et audit npm.
  Le cluster PostgreSQL 16 prévu en CI utilise son propre port, sans Docker.

## Référence et licence

Le dossier `frontEnd/velson_template` n'a pas été modifié. L'application ne copie
aucune page de démo ni bundle JS vendor. Les composants et styles sont du code
Angular/SCSS à partir du rapport validé. `signin.png` est le seul asset commercial
copié localement, dans `public/assets/template`, ignoré par Git ; il reste inclus
uniquement dans le build local. Sans référence privée, le mode CI utilise un
remplacement CSS. Aucun site ou fichier commercial n'a été publié.

Poppins vient du dépôt officiel Google Fonts, avec son fichier OFL. La licence du
template commercial devra être clarifiée avant toute redistribution de ses assets.

## Lancement local

1. Configurer `backend/.env`, appliquer les migrations et créer le propriétaire
   interactivement selon le README racine ; aucun compte réel n'est créé en test.
2. Créer le certificat avec `python -m app.setup tls`, puis lancer Uvicorn HTTPS
   sur `https://localhost:8443` selon le README.
3. Inclure `https://localhost:4200` dans `ALLOWED_ORIGINS` de l'API.
4. Depuis la racine : `scripts/frontend.ps1 install` puis `scripts/frontend.ps1 start`.
5. Ouvrir `https://localhost:4200` et accepter le certificat local autosigné.

Le script choisit le Node portable 22.22.3 du projet s'il existe ; il ne remplace
pas l'installation Node globale. Les prérequis sont détaillés dans les README.

## Vérifications exécutées

| Vérification | Résultat réel |
| --- | --- |
| Backend `pytest -q --tb=short`, explicitement avec `.env.test` | 43 passed in 22.94s |
| Backend `ruff check .` | All checks passed! |
| Backend `ruff format --check .` | 32 files already formatted |
| Backend `mypy app` | Success: no issues found in 22 source files |
| Frontend `typecheck` (app, tests et E2E) | Code 0, sans erreur |
| Frontend `build` production | Code 0 ; initial 291.05 kB, transfert estimé 79.84 kB |
| Frontend `test` Karma / Chrome Headless | TOTAL: 14 SUCCESS |
| Frontend `audit --omit=dev` | found 0 vulnerabilities |
| E2E Playwright / build production + FastAPI HTTPS + PostgreSQL `.env.test` | 5 passed (11.1s) |

Les cinq E2E couvrent : accès protégé/connexion/compte/FR-EN/reload/logout ;
renouvellement réel du cookie d'accès via refresh ; mobile, trap de focus et
navigation ; perte de session ; API indisponible avec erreur visible.
Ils vérifient aussi les attributs des cookies et le chargement effectif du CSS.
Le propriétaire et le schéma E2E sont jetables et supprimés après exécution.

Captures inspectées visuellement : connexion desktop/mobile, dashboard
desktop/mobile et compte desktop. Elles sont dans `.cache/frontend-e2e/screenshots`
et ne contiennent que le propriétaire synthétique de test. La revue compare la
structure et les tokens au template analysé ; aucune comparaison pixel par pixel
contre une baseline navigateur du template original n'est revendiquée.

## Problèmes observés et corrigés

- Compilateur Angular bloqué par le sandbox (`spawn EPERM`) : exécution autorisée.
- Premier E2E sur serveur de développement : ressources et délais de chargement ;
  le scénario de validation emploie désormais le build de production HTTPS local.
- Styles de production non appliqués : le gestionnaire inline du CSS différé
  généré par Angular était bloqué par la CSP. Désactivation de `inlineCritical`,
  puis assertions CSS et nouvelles captures ; aucun JavaScript inline autorisé.
- Retour du focus mobile trop tôt, avant suppression de `inert` : usage de
  `afterNextRender`, vérifié au clavier par Playwright.
- Déconnexion manuelle : distinguer la sortie volontaire de l'expiration pour
  ne pas afficher un faux message de session expirée.

## Limites et prochaine phase

- Docker, images et déploiement restent différés. Le preview HTTPS est local.
- CI GitHub non exécutée, PostgreSQL 16 non vérifié localement ; les résultats
  actuels utilisent le PostgreSQL configuré dans la base de test du propriétaire.
- Les CV, sources, recherche, matching, notifications et candidatures ne sont pas
  encore implémentés ; le projet entier n'est pas déclaré terminé.
- L'E2E final upload CV → validation → recherche sera ajouté avec les modules métier.
- La phase 2 proposée est le registre des sources et le framework de connecteurs,
  après validation de ce rapport. Chaque intégration sera vérifiée à partir de
  documentation et conditions officielles avant activation ; LinkedIn restera
  sans scraping et son accès e-mail attendra sa vérification propre.

La pause à cette livraison suit SPEC §24.2 et §26.5 ; elle ne vaut pas abandon des
autres phases. Les travaux différés restent suivis dans PROGRESS et TODO.

Références techniques : [compatibilité Angular](https://angular.dev/reference/versions),
[Karma/Jasmine Angular](https://angular.dev/guide/testing/karma),
[Google Fonts Poppins/OFL](https://github.com/google/fonts/tree/main/ofl/poppins),
[setup-node](https://github.com/actions/setup-node).
