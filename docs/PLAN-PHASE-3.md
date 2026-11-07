# Plan proposé — Phase 3 : recherche locale, profils et résultats

Date : 2026-11-07. Statut : **DELIVERED / WAITING_FOR_VALIDATION — D-019**.
Livraison, vérifications et limites : `reports/phase-3.md`.
La phase 2 est validée (D-017). Le propriétaire confirme poursuivre avec la phase 3
(D-018). Ce document décrit le périmètre précis proposé pour son approbation.

## Résultat attendu et limites proposées

Enregistrer ses critères dans des profils, lancer une recherche parmi les offres
déjà importées, suivre son exécution et consulter les résultats filtrés et dédupliqués.
Le périmètre « offres importées » doit être affiché avant lancement et dans les résultats.
LinkedIn, Indeed, Keejob et Tanitjobs restent en liens/import manuel selon D-015.
Le serveur ne visite aucune offre et ne prétend pas avoir interrogé ces sites.

Mode manuel B utilisable ; modes CV A/hybride C, score IA et notifications affichés
comme indisponibles jusqu’aux phases correspondantes. Aucun score, visa, compétence,
niveau ou date n’est déduit artificiellement d’un simple titre. CV en phase 4,
matching en phase 5, Telegram et planification en phase 6. Pas de nouvelle dépendance
majeure, service, Docker ou hébergement ; Python 3.11 et PostgreSQL locaux conservés.

## Lots proposés

### 3.1 Critères et profils de recherche

- Module `backend/app/modules/search/` avec api/service/repository/models/schemas/
  events/tests et interface publique `__init__.py`. Il possède SearchProfile et
  SearchConfiguration ; `profile` reste réservé au profil candidat dérivé du CV.
- CRUD, duplication et exemples modifiables : Tunisia Junior Developer,
  Europe Visa Sponsorship, Remote International. Création explicite et idempotente
  des exemples ; aucune offre ni permission de collecte préremplie.
- Critères bornés : sources, domaines/intitulés, mots-clés inclus/exclus,
  pays/villes, remote/hybrid/onsite, niveaux/années, statuts visa, publication et
  nouveauté. Valeurs par défaut junior/graduate/entry, maximum trois ans.
- Champs réservés aux CV/score/notifications futurs sans effet simulé ; rejeter
  explicitement un lancement demandant un mode ou filtre indisponible.
- Distinguer information absente et critère satisfait : politique configurable
  pour conserver/exclure les inconnus, expliquée dans les résultats. Dates de
  publication et découverte séparées ; « aujourd’hui » selon Europe/Paris.

### 3.2 Déduplication, provenance et republications

- Étendre uniquement l’interface publique de listings avec DTO de recherche,
  consultation bornée et résultats de normalisation/déduplication.
- Conserver les lignes importées, URL originales, liens de candidature et traces.
  Ajouter des tables listings de regroupement/liens de provenance : une offre
  logique dans les résultats, toutes ses sources consultables, aucune suppression
  ni réécriture destructive des imports existants.
- Identité exacte déjà livrée conservée. Rapprochement déterministe et conservateur
  sur titre/entreprise/ville normalisés et similarité de descriptions suffisantes.
  Seuils configurables et versionnés ; cas ambigus signalés comme candidats, sans
  fusion automatique. Un champ vide n’est jamais une preuve de doublon.
- Repost : conserver une occurrence distincte et son lien vers l’offre précédente
  lorsqu’un nouvel identifiant/lien et une publication ultérieure explicite le
  justifient ; ne pas déduire une republication de la seule date de réimport.
- Nouveauté du regroupement basée sur la première découverte connue, sans rendre
  neuf un ancien poste lorsqu’un doublon ou une autre provenance est ajouté.

### 3.3 Exécutions et worker persistants

- SearchExecution, SearchTask, SourceExecutionLog et résultats d’exécution détenus
  par search ; snapshot des critères et des offres retenues pour une recherche
  reproductible, avec bornes et limites explicites.
- File PostgreSQL : claim `FOR UPDATE SKIP LOCKED`, heartbeat, verrou de tâche,
  reprise des tâches abandonnées après deux minutes et vérification du propriétaire
  du verrou avant toute écriture finale. Une seule exécution active par profil.
- États pending/running/succeeded/failed/cancelled/timed_out et exécution partial
  si borne atteinte. Maximum trois tentatives pour les erreurs transitoires ;
  aucun retry d’erreur permanente. Traitement idempotent, checkpoints et annulation
  coopérative conservant les résultats déjà enregistrés.
- Étapes locales réelles : lire les imports sélectionnés, dédupliquer, appliquer
  les filtres structurés, enregistrer les résultats. Les sources manuelles sont
  explicitement SKIPPED/MANUAL_ONLY côté collecte ; aucun faux succès réseau,
  compteur « collecté » ou état de matching n’est généré.
- API protégées proposées : `/api/search/profiles`, `/api/search/executions`,
  `/api/search/executions/{id}`, `/cancel`, `/events` et `/results` sous cet id.
  SSE restitue la progression depuis PostgreSQL après reconnexion/rechargement.
- `app.worker` exécutera les handlers ; `--once` traitera un cycle borné puis
  quittera, avec vérification DB et comportement documenté. Pas de scheduler ici.

### 3.4 Interface Angular FR/EN

- Activer Recherche, Profils de recherche et Résultats dans le shell existant.
  Pages sous `src/app/pages/search/`, `search-profiles/`, `results/` ; client typé.
- Formulaire de critères, profils éditables/duplicables, lancement local clairement
  nommé, suivi persistant, erreurs/limites visibles, annulation et reconnexion.
- Liste filtrable et paginée, tris découverte/publication/pays/domaine/visa,
  détail avec texte fourni, champs inconnus et toutes les provenances.
  Scores et recherche CV restent indisponibles et expliqués.
- Dashboard : seulement compteurs réellement disponibles (imports, résultats,
  dernière exécution locale), avec libellés distincts de collecte et de matching.
- Conserver Velson, accessibilité clavier/mobile et le changement analytics:false
  préexistant de angular.json. Préserver `frontEnd/velson_template`.

## Migrations et contrats

- `0004_search_profiles` : nouvelles tables search de profils/configurations.
- `0005_listing_provenance` : nouvelles tables listings pour regroupements,
  provenances et relations de republication ; reprise des imports existants testée.
- `0006_search_queue` : nouvelles tables search d’exécutions/tâches/logs/résultats,
  contraintes d’unicité et index de claim/progression.
- Proposition additive : aucune altération des colonnes ou contraintes existantes,
  aucun changement des migrations 0001–0003 ou contrat cassant des API de phase 2.
  Variante non retenue : fusion destructive des JobListing et déplacement des
  références d’import ; plus risquée pour la provenance et la compatibilité.
- Assemblage des interfaces publiques dans `app/main.py` et le worker ; pas
  d’import croisé de modèles/repositories. Toute nécessité imprévue d’altérer une
  table existante sera présentée avant implémentation.

## Risques, contrôles et livraison

- Faux doublons : seuils conservateurs, conservation des données, tests positifs
  et négatifs (villes/entreprises distinctes, description vide, dates inconnues).
- Concurrence/reprise : intégration PostgreSQL .env.test sur schémas jetables,
  deux workers concurrents, expiration du verrou, crash/reprise, annulation,
  unicité de profil actif, idempotence et migrations depuis l’état phase 2.
- Filtres : junior exigeant cinq ans, données absentes, inclusions/exclusions,
  statut visa explicite, frontières temporelles UTC/Paris et first_seen immuable.
- Sécurité : auth/scoping sur chaque profil/exécution/résultat/SSE, limites de
  requête et pagination, messages sans contenu privé ; aucune requête fournisseur.
- Ruff/format/mypy, tests unitaires/intégration, architecture, couverture dédup/
  nouveauté visée 80 %, Angular types/build/Karma, E2E création/duplication de
  profil, recherche d’imports synthétiques, progression/rechargement/résultats/mobile.
  Aucun label de matching, poste réel ou test réseau fictif ajouté.
- Mettre à jour CHANGELOG/PROGRESS et committer chaque lot vérifié. Rapport
  `docs/reports/phase-3.md`, limites et commandes réelles, puis validation owner.
