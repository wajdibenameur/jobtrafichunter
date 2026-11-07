# Progress

Last updated: 2026-11-07 by Codex / pr?paration phase 2
Current phase: 2 - Plan sources et connecteurs pr?par?, avant impl?mentation
Status: WAITING_FOR_APPROVAL (plan de phase 2 ; SPEC ?24.1 et ?27.3)

## Phase checklist

- [x] 0 Documentation initiale et plan approuv?s.
- [x] 1 Socle local valid? par continuation du propri?taire (D-013).
    - [x] Backend Python 3.11, auth, migration et PostgreSQL locaux.
    - [x] Angular standalone, layout/connexion/compte, FR/EN et tests navigateur.
    - [x] Configuration .env locale et connexion confirm?e par le propri?taire.
    - CI externe / PostgreSQL 16 pr?par?s mais non ex?cut?s ; pas de remote Git.
    - Hors p?rim?tre : Docker, Compose, images et h?bergement (D-012).
- [ ] 2 Sources, v?rifications et framework de connecteurs.
    - [x] 2.0 Plan ?crit et pr?-v?rification documentaire des candidats.
    - [ ] 2.0b Approbation de `PLAN-PHASE-2.md`. <- NEXT
    - [ ] 2.1 Registre des sources, checklist et migration.
    - [ ] 2.2 Framework, transport et v?rification compl?te des connecteurs.
    - [ ] 2.3 Liens de recherche et import manuel persistant.
    - [ ] 2.4 Page Sources Angular, tests et rapport.
- [ ] 3 Configuration, profils, orchestrateur, queue, d?duplication, r?sultats.
- [ ] 4 CV priv?s, parsing, ?dition et validation du profil.
- [ ] 5 Recherche CV, matching explicable, calibration, linkedin_email v?rifi?.
- [ ] 6 Telegram, planification, historique et logs.
- [ ] 7 Candidatures, durcissement, tests et sauvegarde/restauration locales.

## Last session

Done: continuation du propri?taire enregistr?e comme validation du socle local.
Cr?ation de `PLAN-PHASE-2.md` (fichiers, migrations, risques, tests et ?tapes)
et `sources/preverification-phase-2.md` avec preuves officielles et inconnues.
Revue documentaire Remotive/Arbeitnow/JobTech/France Travail : aucun candidat
marqu? PERMITTED, aucun appel de collecte d'offres et aucun contact fournisseur.
Tests: t?che documentaire seulement ; aucun test applicatif relanc?.
Contr?les : SPEC inchang?, consignes AGENTS/CLAUDE identiques et <60 lignes,
pr?sence des livrables et diff documentaire v?rifi?s avant commit.
?tat fonctionnel pr?c?dent : 43 tests backend, 14 Angular et 5 E2E r?ussis ;
connexion locale confirm?e par le propri?taire. Ces tests ne couvrent pas la phase 2.
Not done / blocked: le plan de phase 2 n?cessite l'accord pr?vu par AGENTS/SPEC.
Code/migrations/connecteurs non commenc?s. Contradictions Remotive et port?e du
stockage Arbeitnow ? clarifier ; quotas/robots/accessibilit? des candidats incomplets.
La modification pr?existante `frontEnd/jobhunter/angular.json` est conserv?e et
ne fait pas partie du commit documentaire. Pas de changement des secrets locaux.
Next step: approbation du plan puis t?che 2.1 (registre, politique et migration).
Ne pas activer de collecte avant v?rification compl?te de la source concern?e.

## Open questions for the owner

- Accord sur le plan de phase 2, incluant le socle listings minimal pour rendre
  l'import manuel persistant d?s cette phase.
- Sources de remplacement ? approuver si deux collectes autoris?es ne sont pas
  confirmables ; aucun scraping utilis? pour compenser une int?gration indisponible.
