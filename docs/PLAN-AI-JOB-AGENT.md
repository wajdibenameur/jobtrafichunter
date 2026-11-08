# Plan proposé — AI Job Agent et dossier de candidature

Date : 2026-11-08. Statut : **PROPOSED / WAITING_FOR_OWNER_APPROVAL**.
D-027 autorise uniquement l'enregistrement documentaire de ce plan et de
[l'audit](reports/ai-job-agent-audit.md). Aucun nouveau lot de code approuvé.
La livraison de phase 4 attend aussi sa validation ; ne pas la déduire de cet accord.

## Cadre et correspondance avec les phases

Extension du backend FastAPI Python 3.11, PostgreSQL et Angular standalone/Velson.
Un monolithe modulaire et le worker existant, aucune reconstruction ou seconde queue.
Local uniquement, sans Docker ni hébergement. Imports LinkedIn/Indeed/Keejob/Tanitjobs
conservés. Aucune soumission automatique, dépense ou activation fournisseur implicite.

Les lots ci-dessous ne renumérotent pas les phases historiques : matching rejoint
la phase 5, alertes/planification la phase 6, suivi/hardening la phase 7. CV adapté,
lettre et dossier constituent une extension proposée. Les phases 1–4 ne sont pas
à reconstruire. Rapport, contrôles et validation du propriétaire à chaque lot.

## Lot 1 — Audit et consolidation

- Audit terminé : état fonctionnel, écarts et résultats dans le rapport lié.
- Mise à jour documentaire autorisée : README, AGENTS/CLAUDE, DECISIONS, TODO,
  CHANGELOG, états des plans/rapports et PROGRESS en dernier ; SPEC intact.
- Préserver les changements de code de phase 4 et les changements utilisateur.
  Finaliser ce code dans un lot Git distinct après les contrôles pertinents,
  sans inclure angular.json ni le template par erreur.
- Aucune nouvelle migration. Validation de phase 4 et du plan encore attendue.

## Lot 2 — Filtres temporels et radios

- Modifier backend search/schemas.py, filters.py et leurs tests ; côté Angular,
  core/search-api.ts, shared/criteria-editor.ts/html, pages/search et traductions.
- Étendre les critères avec une fenêtre optionnelle en minutes, compatible avec
  publication_days et les snapshots anciens ; une seule fenêtre effective, sans
  combinaison ambiguë. Paramètres et validation exacts à figer avant code.
- Radios exclusives 2/6/24 h et 7/30 jours, fieldset/legend, clavier et FR/EN.
  Défaut 24 h pour une nouvelle configuration sans préférence enregistrée.
  Préserver les profils existants et les choix avancés toutes dates/3 jours.
- 2 h = 120 min, 6 h = 360 min, 24 h = 1 440 min. Exclure publication absente
  ou future des fenêtres strictes ; ne jamais utiliser first_seen_at comme substitut.
  Garder la sémantique glissante et les bornes historiques des 7/30 jours.
  Clarifier explicitement la frontière exacte 24 h : l'ancien filtre inclut son
  cutoff, la formulation « moins de » est stricte. Aucun changement silencieux.
- Calcul UTC ; présentation Europe/Paris ou Africa/Tunis sans décalage fixe.
  Montrer date non vérifiée/inconnue sans promettre une validation fournisseur.
- Migration normalement inutile : critères JSONB. Si une précision/provenance
  supplémentaire de date devient nécessaire, soumettre une proposition additive.
- Tests : cinq fenêtres, juste avant/à/après borne, inconnues, futur, UTC/DST,
  Paris/Tunis, rechargement des anciens profils, radios et accessibilité.

## Lot 3 — Matching expliqué, puis alertes

- Créer modules/matching/ : models, schemas, service, scoring, calibration,
  api, exports __init__ et tests. Étendre ai/ avec l'analyse structurée des offres
  et un contrat de fournisseur configurable ; réutiliser la taxonomie existante.
- Réutiliser ProfileService.validated_active et les interfaces publiques listings.
  Ajouter si nécessaire un accès public à une offre/snapshot appartenant au compte.
- Calcul déterministe avec sous-scores, preuves, lacunes obligatoires, plafonds,
  confiance et version des poids ; le langage généré ne peut changer le score.
  Tester les pièges de SPEC §23 et les données inconnues sans inventer les faits.
- Cache : version CV + révision candidat + hash de tous les champs d'offre utiles
  au scoring + taxonomie/scoring/configuration modèle. Le fingerprint de déduplication
  seul ne suffit pas. Pas d'altération des snapshots ou imports originaux.
- Intégrer search/executions.py, queue.py et les vues Recherche/Résultats ;
  travail borné, annulation/checkpoints/reprise sans recollecte inutile.
- Calibration : loader et métriques sur données anonymisées labellisées par le
  propriétaire, seuils convenus. Aucun label synthétique présenté comme réel,
  aucun score non calibré présenté comme probabilité d'embauche.
- Ensuite créer notifications/ et search/scheduler.py dans le worker existant :
  15/30/60 min ou 24 h, recommandation 30 min, activation par profil et source permise.
  Reprendre les garanties de claim/lease et verrou d'ordonnancement PostgreSQL.
- Priorités proposées : <2 h et score >=85 ; 2–6 h >=80 ; 6–24 h seuil utilisateur.
  Seuils configurables, pertinence et confiance obligatoires, aucune garantie de
  premier candidat. Sans collecte autorisée, aucune promesse de découverte externe.
- Centre Angular, préférences, historique, Telegram facultatif. Déduplication par
  propriétaire/profil/offre/événement, outbox et tentatives persistées ; traiter
  honnêtement l'incertitude d'un timeout après envoi externe, sans promettre
  un exactly-once que le fournisseur ne garantit pas.
- Migrations additives proposées : analyses/matches/cache/calibration, préférences,
  planifications et alertes/livraisons. Numéros à attribuer à l'implémentation,
  après 0008 si la tête n'a pas changé. Pas d'édition des migrations appliquées.
- Tests scoring/cache/calibration, accès croisés, concurrence, reprise/annulation,
  quotas, déduplication et envois simulés. Aucun Telegram réel dans les tests.

## Lot 4 — CV adapté à une offre

- Proposition à approuver : module documents/ interne au même monolithe, avec
  modèles/schémas/service/API/stockage/export/tests et interface publique.
  Dépendances proposées : documents → cv/profile/ai/listings ; sans cycle.
  Mettre à jour les tests de frontières, pas contourner leurs règles.
- Réutiliser les primitives publiques de chiffrement et de propriété ; garder
  les dérivés distincts des originaux, hors répertoire web, avec audit/suppression.
- Résultats : génération à la demande, aperçu sûr, édition, différences et validation.
  Conserver dates/entreprises/diplômes ; provenance des faits jusqu'au profil validé.
  Les coordonnées absentes nécessitent une saisie/confirmation, jamais une invention.
- Modèle ATS sobre, exports DOCX/PDF, versions liées à l'offre et au propriétaire.
  Dépendances et moteur de rendu à vérifier officiellement avant choix/installation.
- Migration additive : documents et versions, états, liens et provenance.
- Tests : original intact, pas de qualification ajoutée depuis l'annonce seule,
  contenu/export/rendu, autorisations et version figée après validation.

## Lot 5 — Lettre de motivation

- Étendre documents/ et l'éditeur Angular du lot 4, sans second générateur ni coffre.
  Français/anglais/langue supportée de l'annonce ; styles classique/moderne/concis.
- Informations manquantes explicites, motivations à confirmer ; aucun recruteur
  ou contact d'entreprise inventé. Édition, validation, versions et DOCX/PDF.
- Réutiliser le schéma du lot 4 si suffisant, migration seulement si nécessaire.
- Tests factuels, langues/styles, données absentes, exports et contrôle d'accès.

## Lot 6 — Dossier et suivi des candidatures

- Créer applications/ : API, service, modèles, schémas, événements, tests et exports.
  Dépendances proposées : applications → listings/documents, à approuver.
- Compléter pages/results ; ajouter pages/applications, client et route Angular,
  traductions et shell existant. Pas de pages en doublon.
- Bouton Postuler : application_url réelle sinon original_url, HTTPS validé,
  nouvel onglet sûr. Confirmer séparément un envoi, aucun automatisme de candidature.
- États : à consulter, CV préparé, envoyée, entretien, refusée, acceptée ; notes,
  date d'envoi confirmée, snapshots et identifiants exacts des versions utilisées.
- Téléchargements séparés et ZIP uniquement de documents validés/autorisés,
  chemins internes maîtrisés et taille bornée. Pas de génération systématique.
- Migration additive : candidatures/historique/liens documentaires. Définir la
  conservation après suppression du CV : pas de rétention cachée de données privées.
- Tests statuts/historique, clic sans envoi, URLs, ZIP, propriété et suppression.

## Lot 7 — Validation globale et exploitation

- Ruff/format/mypy/pytest, Alembic, typage/build/Karma et Playwright ; nouveaux tests
  ciblés à chaque lot et anciens parcours conservés. Fournisseurs simulés par défaut.
- Vérifier flux CV validé → offre → analyse → documents validés → ZIP → confirmation
  manuelle → suivi ; alertes et reprise, données d'un autre propriétaire inaccessibles.
- Vérifier absence de secrets/contenu CV dans logs, limites, sauvegarde/restauration
  locale et suppression des dérivés. Rapports honnêtes sur échecs et limites.
- README/runbook, DECISIONS/TODO/CHANGELOG et PROGRESS en dernier, sans écraser
  l'historique ni revendiquer CI distante ou source autorisée sans preuve.

## IA et autorisations restantes

Aucun fournisseur génératif existant à remplacer. Prévoir un mode local par règles
et modèles documentaires, et une interface facultative de fournisseur local.
Modèle, ressources machine, nouvelle dépendance ou service nécessitent une proposition
concrète avant installation ; aucun service payant obligatoire, aucun envoi de CV
à un tiers présumé autorisé. Cache et génération à la demande pour limiter les coûts.

Approbations encore nécessaires : livraison de phase 4, plan et arbitrages du lot 2,
puis frontières/migrations/dépendances concrètes aux lots concernés. Apify B reste
différé selon D-023 ; permission source et autorisation C séparée avant run réel.
