# TODO

## Prochaine action

- Scraping Engine : audit `reports/scraping-engine-audit.md`, preuves
  `sources/scraping-review.md`, plan `PLAN-SCRAPING-ENGINE.md`.
  D-029 : lot 2 livré, 181 tests backend réussis ; rapport `reports/scraping-lot-2.md`.
  Lot 2 validé D-030 ; extraction générique lot 3 livrée, rapport
  `reports/scraping-lot-3.md`, à valider avant lot 4. Aucun fournisseur activé.
  Articulation AI Job Agent : un seul chantier filtres/matching/alertes/documents.
- Demande AI Job Agent auditée : `reports/ai-job-agent-audit.md` et
  `PLAN-AI-JOB-AGENT.md`. Mise à jour documentaire autorisée (D-027), plan PROPOSED.
  Attendre la validation de la livraison de phase 4 et du plan avant les nouveaux lots.
- Priorité courante : valider la livraison de phase 4 (`reports/phase-4.md`, D-026),
  puis faire approuver le détail du matching/calibration dans le lot 3 proposé.
  Ne pas confondre les numéros des nouveaux lots et ceux des phases historiques.
  Le propriétaire choisit d’attendre CV et matching avant Apify (D-023).
- Apify : plan A conservé dans `reports/apify-phase-a.md` (D-022), B reportée
  après CV/matching. Vérifier l’Actor/méthode avant reprise et obtenir l’accord
  distinct C avant tout run réel. Ne pas substituer une version collecte seule.
- Recommandation UI : carte LinkedIn — Apify séparée dans Sources, pas de menu
  supplémentaire ; conserver les quatre modes manuels et la recherche locale.
- Phase 2 validée (D-017), continuation vers la phase 3 confirmée (D-018).
- Phase 3 locale livrée et validée ; rapport `reports/phase-3.md`.
- D-015 : LinkedIn, Indeed, Keejob et Tanitjobs en liens/import manuel ; aucune
  collecte automatisée attendue dans cette livraison. Ajout de sites personnalisés disponible.

## Fonctionnalités à venir

- Lots proposés : filtres 2 h/6 h et radios ; matching expliqué/calibré puis alertes ;
  CV adapté ; lettre ; dossier ZIP et suivi ; validation globale. Rien de livré
  pour ces nouvelles fonctionnalités du seul fait de leur inscription dans le plan.
- Arbitrages avant code : défaut actuel toutes dates contre nouveau défaut 24 h,
  dates inconnues exclues des fenêtres strictes, bornes 24 h, conservation des
  profils/choix historiques 3 jours et toutes dates, présentation Paris/Tunis.
- Module documents et nouvelles dépendances d'export/local IA : propositions
  seulement ; faire approuver les frontières et vérifier licences/compatibilité.
- Pas de découverte automatique de nouvelles offres avec les seules sources manuelles.
  Toute surveillance fournisseur reste conditionnée à une source autorisée/activée.
- CV privés PDF/DOCX, parsing Windows isolé et profil validé livrés en phase 4.
  DOC historique et OCR non disponibles ; outils/chaîne isolée à prévoir séparément.
  Qualité d’extraction non calibrée : obtenir le jeu propriétaire de dix CV anonymisés.
- Matching explicable et extraction IA : constituer dix CV anonymisés avec
  résultats attendus, puis cinquante offres anonymisées labellisées par le
  propriétaire. Aucun label de calibration ou résultat réel ne doit être inventé.
- Fixer les seuils d’extraction/calibration avec le propriétaire.
- Vérifier linkedin_email séparément avant toute activation ; consentement et
  accès boîte mail non présumés. Telegram, planification et historique à venir.
- Compléter le dashboard pour le matching/notifications quand ces API existent ;
  les imports et la dernière exécution locale sont déjà réels en phase 3.

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

- Revue Scraping du 2026-11-08 : aucun PERMITTED attribué. LinkedIn reste sans
  scraping ; Indeed/Tanitjobs manuels faute de permission établie pour cet usage.
  Keejob publie un guide Markdown/RSS ; clarifier droits, stockage, attribution et
  fréquence. Greenhouse/Lever : étudier des boards d'entreprises précis.
- Avant transport HTTP : contrôles DNS/IP effectives/redirections, limites de
  téléchargement/décompression et quota livrés dans le transport isolé du lot 2.
  Il reste à raccorder l'autorisation DB courante et les quotas/checkpoints durables
  au worker et persister les métadonnées JSON-LD/précision des dates (lot 5).
  Extraction générique livrée au lot 3 ; adaptateurs réels conditionnés aux permissions.
  La validation syntaxique historique des liens seule reste insuffisante contre SSRF.
- Aucun fournisseur automatisé livré ou activé. Les candidats documentaires
  Remotive, Arbeitnow, JobTech, Jobicy/Himalayas n’accordent aucun accès implicite.
- Si le propriétaire redemande une collecte automatique : vérifier documents,
  conditions, robots, accès, stockage/attribution et quotas avant son code.
  Prévoir alors transport, cache, timeouts, pagination, retries et tests réseau.
- La génération de liens ne garantit pas la pertinence des résultats externes.
