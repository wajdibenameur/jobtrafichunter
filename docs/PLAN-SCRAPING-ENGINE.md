# Plan proposé — Scraping Engine indépendant d'Apify

Date : 2026-11-08. Statut : LOT_3_GENERIC_EXTRACTION_DELIVERED / WAITING_FOR_VALIDATION.
D-028 autorise l'enregistrement des documents, pas leur implémentation.
La continuation « contenue » autorise ensuite le lot 2 seulement (D-029).
Livraison/limites : [rapport du lot 2](reports/scraping-lot-2.md).
Lot 2 validé et extraction lot 3 autorisée par « contenue » (D-030).
Extraction générique livrée : [rapport du lot 3](reports/scraping-lot-3.md).
Adaptateurs fournisseurs toujours conditionnés à des permissions établies.
Voir [audit](reports/scraping-engine-audit.md), [revue des sources](sources/scraping-review.md)
et [plan AI Job Agent](PLAN-AI-JOB-AGENT.md). Phase 4 toujours en attente de validation.

## Cadre et dépendances

Même FastAPI Python 3.11, PostgreSQL local, Angular/Velson et worker existants.
Étendre sources/search/listings, sans module moteur parallèle ni seconde queue.
Conserver les quatre sources manuelles. Une source automatique doit être PERMITTED,
activée et couverte par des preuves actuelles. Aucun scraping LinkedIn ni contournement.
Gratuit au sens sans fournisseur de collecte payant obligatoire ; aucune garantie
d'absence de coût machine, réseau ou de disponibilité des sites.

Les huit lots ne remplacent pas les phases historiques ni les sept lots AI Job Agent.
Filtres, matching, alertes et documents sont des chantiers communs à réaliser une fois.
Rapport/contrôles puis validation du propriétaire après chaque lot de développement.

## Lot 1 — Audit

Audit livré en conversation puis enregistré sur demande ; aucun code de collecte.
Constats, état des tests et preuves officielles dans les documents liés.
Ordre d'implémentation encore proposé ; permission source indépendante de l'accord au plan.

## Lot 2 — Infrastructure des connecteurs

Livré selon le [rapport](reports/scraping-lot-2.md), validé par continuation D-030.

- Étendre sources/connectors/contracts.py et registry.py : requête typée avec
  limites/fenêtre/cursor, résultat paginé avec compteur/checkpoint et erreurs typées,
  capabilities et health_check compatibles avec le manuel. Pas de second Protocol.
- Créer sources/connectors/http_client.py : HTTPS, domaines/chemins approuvés,
  contrôle DNS IPv4/IPv6 et IP de connexion, protection contre DNS rebinding,
  redirections contrôlées une à une, pas de proxy d'environnement implicite.
- Délais connexion/lecture et échéance globale, taille après décompression bornée,
  pages/requêtes/résultats limités, concurrence/fréquence par source, backoff borné
  et Retry-After. Arrêt et erreur explicite sur blocage ; aucun faux succès vide.
- Réutiliser sources/policy.py ; contrôle avant test réseau et chaque reprise,
  pas seulement au clic. Ne pas transformer un toggle en permission de collecte.
- httpx à promouvoir en runtime ; beautifulsoup4 à examiner, verrouiller et auditer.
  Aucun Playwright runtime par défaut ; étude distincte si une source permise l'exige.
- Tests simulés : HTTP, quotas, plafonds, DNS/redirections, permissions expirées.

## Lot 3 — Extraction et première source permise

Extraction générique livrée, validation attendue. Aucun fournisseur enregistré,
car aucune permission pour un périmètre source concret n'est encore établie.

- Créer sources/connectors/jsonld.py : listes, @graph, mainEntity, ListItem.item,
  types simples/multiples, champs optionnels validés ; limites profondeur/objets.
  Aucun contexte distant chargé, JavaScript exécuté ou lien embarqué visité par défaut.
- Normaliser descriptions HTML en texte sûr, entreprise/localisations multiples,
  identifiant, emploi/type de contrat, dates et URL candidature réelle.
- datePosted date seule/sans fuseau : conserver précision et provenance ; ne pas
  inventer une heure pour les filtres stricts 2/6 h. Choix de stockage à approuver.
- Adaptateurs séparés pour chaque source permise. Keejob RSS/API carrières : candidats,
  pas engagements d'activation. Tanitjobs/Indeed restent manuels faute de permission.
- Étendre le générateur de lien LinkedIn existant pour le filtre de temps si vérifié,
  sans accès automatisé aux annonces. Import manuel toujours disponible.
- Tests JSON/HTML synthétiques : malformés, formats, URLs, dates, tailles et pagination.

## Lot 4 — Angular

- Ajouter pages/scraping/ (composant/template/styles/tests), route dans app.routes.ts,
  entrée shell, client typé et traductions FR/EN. Reprendre le design Velson.
- Profil, sources, mots-clés, lieu, expérience, maximum d'offres et fréquence ;
  droits/statuts, dernière exécution, découverts/nouveaux/erreurs sans nombres inventés.
- Tester/Lancer/Arrêter/Résultats/Historique utilisent les interfaces existantes
  étendues ; aucun endpoint générique acceptant une URL arbitraire à télécharger.
- Réutiliser le même éditeur temporel que Recherche : radios 2/6/24 h, 7/30 jours,
  défaut 24 h seulement sans préférence existante, autres filtres conservés.
  Préserver les profils historiques et définir les bornes strictes explicitement.
- Réutiliser les vues Résultats/historique ; ne pas recopier leurs services.
  Fréquence désactivée/indisponible jusqu'à livraison de l'ordonnanceur du lot 6.
- Tests accessibilité/clavier/mobile, exclusivité radios, SSE/rechargement/erreurs.

## Lot 5 — Intégration queue, worker et PostgreSQL

- Étendre search/executions.py, queue.py, schémas/API et app/worker.py au besoin.
  Mode collecte explicite et optionnel, recherche locale historique inchangée.
- Étape COLLECT dans la queue actuelle, checkpoints par source ; pages persistées
  avec ingestion idempotente avant avancement du curseur. Reprise sans perte ni
  double comptage, résultats enregistrés conservés lors d'annulation.
- Étendre les interfaces publiques sources/listings : aucune lecture privée
  intermodule. Collecte normalisée distincte de la confirmation d'un import manuel.
- Migrations additives proposées : configurations de collecte/domaines/limites,
  checkpoints et métriques par source rattachés à l'exécution, métadonnées d'offre
  (précision de publication, type de contrat, provenance). Éviter de modifier les
  tables actuelles ; faire approuver toute contrainte/champ existant à changer.
- Aucune réécriture de migrations 0001–0008. Numéros futurs attribués au moment du code.
- Tests PostgreSQL : concurrence, crash aux frontières de transaction, reprise,
  déduplication ambiguë, compteurs exacts et sources désactivées pendant l'exécution.

## Lot 6 — Matching, alertes et Early Applicant

- Réaliser les modules communs prévus dans le lot 3 AI Job Agent, pas les dupliquer.
  Profil validé obligatoire, score expliqué/versionné/calibré, confiance et cache.
- Planification dans le worker existant : 15/30/60 minutes ou 24 h, défaut proposé
  30 minutes, quotas source prioritaires. Verrous PostgreSQL et exécution non chevauchante.
- Fraîcheur sur publication connue/précise, pertinence d'abord ; aucun engagement
  à être premier candidat. Notifications Angular et Telegram facultatif.
- Déduplication profil/offre/événement, état durable d'envoi et gestion explicite
  de l'incertitude réseau ; pas de promesse exactly-once sans support fournisseur.
- Migrations/tests matching/alertes communs au plan AI Job Agent ; fixtures et
  clients simulés, aucun Telegram réel automatique ou label de calibration inventé.

## Lot 7 — Candidature

Raccorder les lots 4–6 AI Job Agent : CV adapté, lettre, exports DOCX/PDF, dossier
validé et suivi. Ces fonctions sont encore absentes ; ne pas prétendre les réutiliser
comme livrées. Un seul générateur/versionnement, original immuable, faits confirmés.
Utiliser application_url sinon original_url. Clic distinct de confirmation d'envoi.
Aucune soumission automatique. Tests/stockage privés communs au chantier documentaire.

## Lot 8 — Validation et documentation

Ruff/format/mypy/pytest, Alembic, typage/build/Karma et E2E sur fournisseurs simulés ;
tests d'isolation, absence de secrets, quotas, annulation/reprise et non-régression.
Un test réel borné n'est envisageable qu'après permission et accord appropriés.
Mettre à jour README, preuves source, décisions/TODO/CHANGELOG et PROGRESS en dernier.
Ne pas revendiquer une collecte réelle réussie sur la seule base des fixtures.

## Validation attendue

Lot 2 validé D-030 ; attendre validation de l'extraction lot 3 avant le lot 4.
Autres lots et articulation avec AI Job Agent encore proposés ; validation de
phase 4 séparée. Migrations/dépendances concrètes à examiner aux lots concernés.
Ce chantier ne réactive pas Apify (D-023) et n'autorise aucune dépense.
