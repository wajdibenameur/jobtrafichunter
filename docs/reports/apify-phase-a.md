# Phase A — Plan d’intégration Apify dans JobHunter AI

Date : 2026-11-08. **Analyse terminée, plan proposé ; Phase B non autorisée.**
Demande spécifique A/B/C du propriétaire, distincte de la future phase 4 CV.
Python 3.11, FastAPI, PostgreSQL, Angular standalone et exécution locale conservés.
Aucun code applicatif, migration, dépendance, secret ou paramètre de compte modifié.

## 1. Inspection de l’existant

| Élément inspecté | Réutilisation et adaptation nécessaire |
| --- | --- |
| `search/service.py`, `schemas.py`, `repository.py` | Profils de recherche déjà dans search, pas de module profiles indépendant. Snapshot des critères conservé. |
| `search/models.py`, `executions.py`, `queue.py` | Queue PostgreSQL, leases, heartbeat, fencing, reprise, annulation, résultats persistants. Pipeline actuellement SCAN/FILTER local, pas d’appels fournisseurs. |
| `app/worker.py` | Même worker et composition par interfaces publiques ; aucun second service ou système de queue. |
| `listings/service.py`, `repository.py`, `catalog.py`, `dedup.py` | Validation, unicité, première découverte, regroupements et provenance ; voie publique d’ingestion fournisseur à ajouter. |
| `sources/service.py`, `policy.py`, connecteurs | Registre manuel uniquement ; automatisation actuellement forcée à false, API refusée par patch. Adaptation ciblée et gardée, pas activation globale des API. |
| Alembic `0001`–`0006` | Migrations déjà livrées, à conserver. Extension additive proposée ci-dessous. |
| Tests search/listings/sources, architecture et E2E | Concurrence, reprise, données immuables et worker séparé déjà testés ; nouveaux cas réseau/facturation à simuler. |
| Angular Sources, Recherche, Profils, Résultats et clients typés | Sources pour la configuration ; suivi et résultats communs, avec périmètre fournisseur clairement affiché. |

Limites actuelles importantes : une tâche dure au plus 3 minutes, une exécution
15 minutes ; les trois tentatives existantes ne doivent pas compter chaque simple
poll comme un échec. `ExecutionView.scope` n’accepte que IMPORTED_OFFERS.
`ListingService.import_jobs` refuse les sources non manuelles ; ne pas contourner
cette protection en faisant passer Apify pour un import manuel.

**CV et matching absents** : seuls auth, sources, listings et search sont implémentés.
Il n’existe pas encore de module cv/profile candidat/matching à réutiliser, ni de
profil CV validé. Le plan ne peut donc pas annoncer le matching CV comme disponible.
Proposition : statut explicite NOT_AVAILABLE et point d’extension public futur.
Si un lancement exige le matching CV, le refuser avant confirmation et facturation.
Un mode collecte seule demande ton accord de périmètre ; le matching réel nécessite
les phases CV/matching séparées. Aucun score fictif ou CV envoyé à Apify.

## 2. Choix d’interface proposé

**Une carte distincte « LinkedIn — Apify » dans la page Sources existante**, avec
un composant dédié à sa configuration/historique. Pas de nouvelle entrée de menu,
pas de remplacement de la carte LinkedIn manuelle. Une page séparée dupliquerait
navigation et état de recherche ; un simple toggle sur LinkedIn confondrait les modes.

- Carte désactivée par défaut, états « non configuré », « autorisation requise »,
  « prêt » et erreurs distincts de la simple connexion au compte Apify.
- Profil existant, mots-clés, une localisation, période, maximum **10 offres par
  défaut**, plafond USD explicite et positif. Pas de montant de dépense accepté
  implicitement, pas de boucle cachée sur les pays/mots-clés du profil.
- « Tester la connexion » vérifie le compte et les métadonnées de l’Actor sans
  exécuter d’Actor ; ce test ne prouve ni permission LinkedIn ni garantie de budget.
- « Rechercher maintenant » ouvre un aperçu : Actor/build, critères transmis et
  filtres locaux, maximum d’offres, plafond/support, limites et statut matching.
  Une seconde action explicite « Confirmer l’exécution facturable » est nécessaire.
- Historique avec état distant/local, nombres reçus/importés/doublons/rejetés,
  coût USD connu ou « indisponible/provisoire », date d’observation et erreurs utiles.
- Résultats et suivi dans les pages existantes, avec périmètre APIFY_LINKEDIN ;
  le bouton de recherche locale existant ne pourra jamais déclencher Apify.
- FR/EN, clavier/mobile, thème Velson conservés ; token absent des formulaires.

## 3. Client backend et autorisations

Client HTTP Apify indépendant dans sources, appelé par le worker via son interface
publique. httpx existe en dépendance dev : le promouvoir au runtime, garder les
versions/hashes maîtrisés. API HTTPS Apify à hôte fixe, IDs validés, pas de suivi
d’URL arbitraire renvoyée dans un résultat, redirections interdites ou contrôlées.

`APIFY_API_TOKEN` optionnel en SecretStr et `APIFY_ACTOR_ID` dans Settings et
`.env.example` **en Phase B**. Absence de configuration sans effet sur l’application
locale. Ne pas lire/modifier/remplacer les secrets existants. Authentification
par en-tête backend, jamais token en query string, input Actor, DTO ou logs.
Réponses publiques par liste blanche ; users/me peut contenir des données privées.

Actor/build et adaptateur de schéma à approuver, pas n’importe quel Actor exécutable
par simple changement de champ. Le changement invalide revue, devis et consentement.
Permissions minimales, aucune réutilisation de session/cookies LinkedIn ou technique
de contournement. La revue officielle est dans [linkedin-apify.md](../sources/linkedin-apify.md).
**Autorisation LinkedIn non établie : conserver UNVERIFIED, aucun lancement réel.**
Apify Store ne constitue pas une preuve de permission. Une autorisation financière
ne remplace pas la vérification de source ; un toggle ne peut attribuer PERMITTED.

## 4. Exécution, reprise et risque de double facturation

1. Préparer un devis local immuable : propriétaire, profil, source, Actor/build,
   critères effectifs, hash d’entrée, revue/tarif/version, max résultats et budget.
   Ajouter explicitement la provenance Apify aux sources effectives du snapshot,
   sans réécrire le profil enregistré. Faire apparaître les critères non transmis.
2. Après confirmation unitaire expirante et consommable une seule fois : créer
   SearchExecution/SearchTask et l’opération fournisseur dans la même transaction.
   Revalider configuration et autorisations au lancement, pas seulement à l’aperçu.
3. Worker avec fencing : enregistrer STARTING **avant** l’unique POST asynchrone.
   Désactiver retry automatique du POST initial et restartOnError. Si réponse connue,
   persister run_id, dataset_id et build effectif dès réception.
4. Réponse perdue/crash après POST avant persistance : START_UNCERTAIN, aucun second
   POST. Réconcilier explicitement ; une liste de runs vide ne prouve pas l’absence
   d’un lancement. Bloquer un nouveau lancement tant que cette ambiguïté persiste.
   La documentation consultée ne fournit pas d’idempotence de création garantie.
5. Run connu : reprendre uniquement statut et dataset de ce run. Pas de run-sync,
   relance, resurrection ou augmentation de budget automatique. Polls courts avec
   next_retry_at ; ne pas monopoliser une lease pendant toute l’exécution distante.
6. Lire un dataset terminal en pages bornées, offset stable, schéma validé. Limiter
   l’import local à la quantité confirmée, indépendamment de la limite fournisseur.
   Reçus d’ingestion idempotents avant avancement du checkpoint : une reprise après
   commit sans checkpoint ne réimporte pas ou ne réenrichit pas une seconde fois.
7. Normaliser, préserver URL/publication/provenance/inconnus, puis déduplication et
   filtrage existants. Matching réel uniquement quand disponible et autorisé.
8. Annulation/délai/désactivation : arrêter la progression locale et demander
   l’arrêt du run distant existant. Suivre l’arrêt jusqu’à confirmation ou statut
   inconnu visible ; un timeout local n’arrête pas à lui seul la facturation distante.
   Garder l’identifiant du run et les résultats acquis, sans promettre remboursement.

401/403 : authentification/droits ; 402 ou erreur fournisseur de limite : crédits/
budget ; 429 : Retry-After borné ; 5xx/timeouts : reprise des lectures seulement,
jamais nouveau lancement ambigu. Messages publics contrôlés, aucun corps brut.
Le `usageTotalUsd` disponible est conservé avec son horodatage ; ne pas le sommer
avec ses composantes ni convertir null en zéro. Le plafond d’un run n’est pas une
garantie des frais globaux du compte. Support exact à valider par Actor/tarification.

## 5. Fichiers et migration proposés pour la Phase B

| Fichiers | Modifications prévues après accord |
| --- | --- |
| `backend/app/modules/sources/connectors/apify/` (`client.py`, `schemas.py`, `adapter.py`, `README.md`) | Client testable, DTO, adaptateur de l’Actor autorisé, capacités et erreurs ; pas de scraping LinkedIn propre à l’application. |
| `sources/{models,schemas,service,api,__init__}.py`, connecteurs registry/contracts/policy | Configuration dédiée, revue/capacités, health/test sans run, activation gardée et contrat asynchrone étendu sans casser le manuel. |
| `search/{models,executions,queue,execution_schemas,api,__init__}.py`, nouveau `apify_workflow.py` | Préparation/confirmation, dispatch via la queue existante, polling/checkpoints/annulation, suivi des coûts. |
| `listings/{models,service,repository,catalog,search_contracts,__init__}.py` | Ingestion fournisseur publique, reçus idempotents et observations supplémentaires par source. |
| `core/settings.py`, `backend/.env.example`, pyproject et deux lockfiles | Variables optionnelles et httpx runtime ; aucun secret réel modifié. |
| `app/main.py`, `app/worker.py`, Alembic env | Composition et enregistrement par interfaces publiques ; pas d’import privé entre modules. |
| `pages/sources/apify-panel.{ts,html,scss}`, Sources TS/HTML | Carte séparée intégrée, confirmation facturable, configuration et historique. |
| `core/apify-api.ts`, clients/translations search/sources, pages search/results | DTO typés, nouveau périmètre, provenance à clés stables et états facturation/matching. |
| Tests modules concernés, Angular et E2E | Fakes HTTP uniquement, plus non-régression des modes locaux/manuels. |

**Migration additive proposée `0007_apify_workflow`** (numéro à revérifier en Phase B) :
seed séparé `linkedin-apify`, intégration API/UNVERIFIED, préférence désactivée ;
configuration Apify détenue par sources ; consentements et opérations fournisseur
détenus par search ; reçus d’ingestion et observations de provenance détenus par
listings. Contraintes owner, unique consentement consommé, unique run connu et
reçu `(owner, source, run, dataset, offset)` ; montants Decimal USD nullables.
Aucune migration existante modifiée ; aucune altération de table existante prévue.

Point critique : l’URL canonique est unique par propriétaire. Une URL LinkedIn
déjà importée manuellement garde sa source originale ; une nouvelle observation
Apify doit être ajoutée, sans écraser l’import. Le scan filtrera aussi ces
observations et le DTO de provenance aura une clé stable pour Angular. Sinon,
l’offre pourrait disparaître des recherches Apify ou perdre sa seconde provenance.

API proposées : configuration/test sous `/api/sources/{id}/apify`, préparation et
confirmation sous `/api/search/apify/...`, progression/résultats via les routes
existantes. Extension additive de scope/capacités ; anciens appels locaux inchangés.
La queue reste unique : adapter le dispatch, les polls non comptés comme retries
et les échéances aux opérations distantes. Les états détaillés et coûts résident
dans les nouvelles tables, pas dans les snapshots de filtrage qui sont supprimés.

## 6. Validation B et préparation C

Tests simulés : token absent/invalide et non-divulgation, Actor/schema/configuration,
permissions expirées/non permises, absence de POST avant consentement, consentement
rejoué/modifié/expiré, limites quantité/coût non prises en charge, schémas incomplets,
normalisation, URL manuelle puis Apify, quota/402/429/5xx, dataset partiel/supprimé,
annulation/abort incertain, reprise de pagination, deux workers et fencing.
Injecter le crash après acceptation distante avant run_id, après stockage run_id,
après ingestion avant checkpoint ; vérifier qu’aucun POST facturable supplémentaire
n’est tenté. Assert zéro accès réseau live dans les tests et zéro token dans logs/DTO.

Ruff/mypy, migrations vierges/upgrade, pytest .env.test, types/build/Karma et E2E
avec API Apify simulée. Les 105/21/9 contrôles de phase 3 sont l’état historique,
**pas des tests Apify exécutés**. Phase A : vérifications documentaires seulement.

Phase C, séparée : après B validée, Actor/méthode autorisés et budget chiffré,
préparer un test limité à 10 offres et demander une autorisation explicite liée au
devis. L’accord B ne vaut pas cet accord C. Aucun appel payant dans les tests.

## Points à valider avant B

- Carte séparée intégrée à Sources et extension additive proposée.
- Actor exact et preuve de méthode autorisée à fournir sans token dans le chat.
  Tant qu’absents : infrastructure générique et simulations uniquement ; pas de
  connecteur spécifique de collecte LinkedIn activable ni test réel.
- Matching CV : attendre ses phases de développement, ou approuver expressément
  un premier périmètre collecte/déduplication/filtrage avec matching indisponible.

Phase A n’autorise aucune implémentation B, activation ou dépense C.
