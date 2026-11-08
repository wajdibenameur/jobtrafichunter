# Scraping Engine — plan détaillé du lot 5

Date : 2026-11-08. Statut : PROPOSED / WAITING_FOR_OWNER_APPROVAL (D-032).
Le propriétaire a validé le lot 4 par « contenue ». Cette étape prépare le plan
d'intégration annoncé ; elle n'autorise pas encore son code ou ses migrations.
[Plan général](PLAN-SCRAPING-ENGINE.md), [lot 4 validé](reports/scraping-lot-4.md).

## Périmètre et résultat attendu

Ajouter un parcours explicite collecte puis filtrage à SearchQueue, dans le même
worker et PostgreSQL. Préserver le parcours IMPORTED_OFFERS et ses profils/résultats.
Réutiliser les contrats paginés, le transport sûr, la normalisation JSON-LD, les
empreintes/groupements et filter_fact. Pas de nouveau moteur, queue ou dépendance.

Livrer l'intégration sur connecteurs simulés injectés uniquement dans les tests.
Aucun fournisseur automatique n'est enregistré aujourd'hui : en installation
normale, une tentative de collecte restera refusée avec une raison exploitable.
Pas de source PERMITTED fabriquée, activation réelle, scraping LinkedIn, Apify,
matching, notifications, ordonnanceur, fréquence persistée ou appel facturable.
Les quatre sources manuelles et les changements CV en cours restent intacts.

## Constat dans le code

- search/queue.py : claim SKIP LOCKED, lease_token, heartbeat toutes les 5 s,
  expiration 2 min, trois tentatives, échéance d'exécution 15 min. _process ne fait
  que SCAN/FILTER ; wait_for limite actuellement tout traitement à 180 s.
- SearchTask.cursor est un entier de filtrage ; ne pas y mettre un curseur réseau.
  _finish efface le workset, les SearchResult conservent leurs snapshots.
- ExecutionService.request vérifie les sources manuelles et crée une tâche unique.
  L'index existant interdit déjà deux exécutions actives du même profil.
- ExecutionView.scope est aujourd'hui littéral IMPORTED_OFFERS et _view ne lit pas
  la colonne scope : il faut étendre le contrat et restituer la valeur réelle.
- ListingService.import_jobs ouvre sa transaction ; import_one enrichit une offre
  déjà importée. Un appel direct serait incompatible avec le commit atomique du
  checkpoint et pourrait écraser du contenu confirmé manuellement.
- sources.__init__ n'exporte que SourceService/router. Autorisation, registre,
  contrats et quotas réseau sont internes ; les budgets actuels sont en mémoire.
- La page Scraping lit les vraies données, mais ses actions de collecte et volume
  sont désactivés. Sa fréquence reste hors lot 5.

## Interfaces publiques proposées

Noms ci-dessous proposés, pas encore implémentés. Chaque module garde ses tables.
search importe uniquement les interfaces exportées par sources et listings.

| Module | Interface | Responsabilité |
| --- | --- | --- |
| sources | CollectionService.describe(owner, source_id) | Éligibilité, limites, capacités, raisons de refus sans réseau |
| sources | CollectionService.fetch_page(owner, source_id, query, context) | Contrat paginé existant, autorisation actuelle et transport contrôlé |
| sources | CollectionService.test(owner, source_id) | Test non facturable via le même garde et les quotas ; refuse sans adaptateur autorisé |
| sources | CollectionService.reserve/settle | Réservations HTTP durables ; transaction courte fournie par l'appelant |
| listings | CollectedJob / CollectionPageInput / CollectionReceipt | DTO propres à listings, sans dépendance vers sources ou search |
| listings | ListingService.ingest_collection_page(session, owner, page) | Participe à la transaction de l'appelant, aucun begin/commit interne |
| search | Orchestration interne collection.py | Traduit NormalizedListing vers CollectedJob ; orchestre sans lire de table étrangère |

Réexporter depuis sources.__init__ CollectionService et les DTO nécessaires du
contrat existant, sans créer de protocole concurrent. Étendre CollectionHttpClient
avec un stockage de budget injectable : en mémoire dans ses tests unitaires actuels,
durable dans le worker. Aucun accès SQL dans le connecteur ou la couche réseau.
Les URL restent choisies par l'adaptateur enregistré et limitées aux domaines et
préfixes revus ; l'API n'accepte pas d'URL de collecte arbitraire.

## API et Angular — changements additifs à approuver

- POST /api/search/executions : conserver profile_id ; ajouter scope optionnel,
  IMPORTED_OFFERS par défaut, ou COLLECTED_OFFERS, et max_results 1–500 (défaut 10)
  pour ce second scope. Refuser les options de collecte avec le scope local.
- En mode collecte, toutes les sources choisies doivent être éligibles ; sinon
  refuser avant création avec raisons par source. Pas de repli silencieux en local.
  Critères, sources et limites sont figés dans le plan de l'exécution.
- GET /api/sources/{id}/collection : capacités/limites/éligibilité calculées.
  POST /api/sources/{id}/collection/test : mêmes gardes ; sans adaptateur,
  réponse indisponible, aucune requête réseau. Pas de route générique d'activation
  ou d'édition des permissions dans ce lot.
- Étendre ExecutionView.scope et SourceLogView par champs optionnels de progression,
  compteurs, dernière erreur typée et limites ; ne jamais renvoyer curseurs privés,
  URL contenant des paramètres sensibles ou contenu brut d'une erreur fournisseur.
- Réutiliser GET exécution/historique/results/events et POST cancel. Aucun endpoint
  resume : une interruption technique reprend la même tâche ; CANCELLED est terminal.
- Scraping : relier Tester/Lancer/Arrêter/volume à ces contrats, état restauré par
  GET/SSE après reload. Actions actives uniquement si capacités réelles disponibles ;
  sans source permise, elles restent désactivées avec leur motif.
- Recherche et historique distinguent les scopes ; lien Résultats réutilisé.
  Fréquence reste désactivée, matching reste explicitement indisponible.

## Modèle PostgreSQL proposé — sept tables nouvelles

Aucune modification de colonne, contrainte ou index existant. Utiliser les colonnes
libres scope/stage déjà présentes et les états terminaux existants. La précision
temporelle reste une observation additive, jamais une heure inventée.

| Propriétaire / table proposée | Colonnes et invariants principaux |
| --- | --- |
| sources / source_collection_configs | source_id PK/FK, adapter_key, version, enabled=false, approved_hosts_paths JSONB, limits JSONB validés ; pas de secrets ; limites ne confèrent pas la permission |
| sources / source_collection_runtime | source_id PK/FK, next_request_at, deferred_until, failures, disabled_reason ; verrou court pour réservations entre profils/processus |
| sources / source_collection_reservations | UUID PK, source_id, execution_id opaque, checkpoint_id opaque, request_key unique par exécution/source, ordinal HTTP durable, réservations octets/requête, état et dates ; aucune URL/token |
| search / search_collection_plans | execution_id PK/FK, version, critères/limites/capacités figés, max_results global, deadline ; absence de ligne signifie parcours historique |
| search / search_collection_checkpoints | UUID PK, execution_id FK, source_id FK, UNIQUE(execution_id,source_id), state, cursor privé borné, page_index, compteurs, source_deadline, query_hash, retry_after, erreur typée ; compteurs non négatifs |
| listings / listing_collection_pages | UUID PK, owner/source/execution/checkpoint ids, request_key, query_hash, payload_hash, receipt JSONB, observed_at ; UNIQUE(owner,execution,source,request_key) |
| listings / listing_collection_observations | page_id FK, position, listing_id FK, DTO normalisé borné/versionné, précision/date/provenance/avertissements ; UNIQUE(page_id,position), isolation propriétaire |

Seules les références déclaratives par identifiant sont permises entre modules,
sans requête vers leurs tables privées. Index sur exécution/source et dates utiles ;
validation JSONB par DTO avant écriture, CHECK pour compteurs/états des nouvelles tables.
Ne pas stocker HTML brut, CV, secrets, réponse HTTP complète ou données personnelles
inutiles. Les observations métier restent privées, absentes des logs et du SSE.

Proposer trois révisions Alembic ordonnées sources → search → listings, numéros
attribués au moment du code après inspection du head réel. 0007/0008 CV présentes
dans l'arbre sont préexistantes : ne pas les réécrire ni les inclure au commit.
Aucune donnée historique à convertir. Downgrade supprime uniquement les nouvelles
tables en ordre inverse et est destructif pour leurs observations : tester seulement
sur schéma jetable. Ne pas exécuter de migration sur la base personnelle ici.

## Pipeline, transactions et reprise

1. À la demande : vérifier propriété/profil et sources via interfaces publiques,
   créer SearchExecution(scope=COLLECTED_OFFERS), SearchTask(stage=COLLECT), plan,
   checkpoints et logs dans la transaction actuelle. L'index actif reste inchangé.
2. Claim/heartbeat/fencing restent ceux de SearchQueue. Dans ce lot, traiter les
   sources séquentiellement avec ordre stable ; conserver une limite de concurrence
   globale et la coordination source entre exécutions. La parallélisation pourra
   être ajoutée après mesure, sans faire croire qu'elle existe déjà.
3. Avant toute page/retry/redirection : relire enabled/archive, preuve PERMITTED
   non expirée et périmètre via sources. Utiliser l'intersection du snapshot de
   limites et des limites actuelles plus strictes. Un snapshot ne vaut pas permission.
4. Transaction courte : vérifier lease et annulation, réserver requête/crédits de
   volume et créneau source. Réseau ensuite, hors transaction/verrou PostgreSQL.
   Autorisation revérifiée au plus près de l'envoi ; un paquet déjà envoyé ne peut
   pas être rappelé par une désactivation simultanée.
5. Après réponse bornée : transaction unique, fence/annulation/permission actuelles,
   ingestion publique listings, reçu, observations, compteurs, next_cursor et logs.
   Ces appels partagent la même session sans commit imbriqué. Si permission retirée
   ou bail perdu, ne pas ingérer ; les réservations consommées restent comptabilisées.
6. request_key = hash(version, exécution, source, query_hash, curseur entrant,
   index de page). Une relecture du même reçu retourne les mêmes compteurs et ne
   modifie pas last_seen_at. Curseurs répétés/cycliques : PARTIAL/PAGINATION_LOOP.
   Cette clé est celle de la page métier. Chaque tentative HTTP, retry ou redirection
   a une réservation distincte dérivée de cette clé et d'un ordinal durable ; rejouer
   une page ne permet jamais de réutiliser gratuitement une réservation réseau.
7. Crash avant commit : page non avancée, réponse GET éventuellement relue ; crash
   après commit : curseur/reçu déjà durables, pas de double ingestion ni comptage.
   Le réseau est au moins une fois, pas exactly-once. Aucun appel payant dans ce lot.
8. Fin de collecte : SCAN/FILTER existants sur les offres des sources sélectionnées,
   y compris celles déjà connues, via ListingCatalog. Pas de matching inventé.
   L'échéance de filtre reste ancrée à execution.created_at, comme le parcours local.
   Une limite ou erreur partielle ne peut pas être écrasée par un succès du filtre.

L'ingestion partage canonicalisation/identités/relations avec le manuel, mais
n'appelle pas import_one avec son enrichissement automatique. Insérer une offre
nouvelle ; pour une identité connue, conserver les champs métier existants,
first_seen_at et imports/batches originaux, n'actualiser que last_seen_at et ajouter
l'observation. Deux identifiants désignant des lignes différentes donnent un conflit
explicite, jamais une fusion arbitraire. Le regroupement conservateur existant reste.
Les mises à jour de contenu depuis une observation sont différées ; un import manuel
confirmé garde son fonctionnement actuel. Une date DATE/LOCAL_DATETIME ne renseigne
pas published_at ; une offre nouvelle ainsi datée échoue aux filtres horaires stricts.

## Budgets, arrêt et états

- max_results est le plafond global d'items acceptés par ingestion avant filtrage,
  partagé entre sources, défaut 10 et maximum 500. Les doublons consomment ce budget
  de lecture ; les compteurs created/existing sont distincts. Les résultats filtrés
  peuvent être moins nombreux. Ne pas demander à chaque source le plafond total.
- Conserver les plafonds existants : 10 pages par source par défaut, requêtes et
  octets bornés, 180 s par source, 15 min par exécution, trois essais maximum.
  Ne pas réinitialiser ces budgets/deadlines à la reprise. Le wait_for global de
  180 s reste pour le parcours local ; collecte utilise le temps restant des 15 min
  et des échéances source, incluant collecte/filtrage dans l'échéance totale.
- Avant chaque envoi/retry/redirection, réserver durablement le coût maximal
  autorisé en octets et une requête, puis rendre l'excédent après mesure. Un crash
  garde la réservation conservatrice ; il peut réduire le volume utile, jamais
  réinitialiser le quota. Respecter séparément octets réseau et décompressés.
- Rate limit/Retry-After sont durables et partagés par source. Si le délai dépasse
  le budget restant, terminer PARTIAL avec motif ; ne pas dormir au-delà du deadline.
- BLOCKED/AUTH : arrêt sans retry et désactivation automatique persistée immédiate,
  affichée avec besoin de revue ; SCHEMA répété (trois échecs consécutifs) idem.
  Succès remet ce compteur à zéro ; timeout/réseau seuls sont transitoires.
- Fin naturelle complète : SUCCEEDED. Limites ou sources partiellement échouées :
  PARTIAL. Échec total sans progression utile : FAILED ; deadline : TIMED_OUT.
  Annulation prioritaire : CANCELLED, offres/résultats déjà commités conservés.
  Si annulation pendant COLLECT, les offres sont dans le catalogue ; des résultats
  filtrés peuvent être absents. Ne pas promettre une page de résultats déjà calculée.
- Une annulation ou perte de bail interdit tout commit tardif. Reprise automatique
  uniquement pour interruption technique ; relancer après CANCELLED est une nouvelle
  exécution explicite, avec nouveaux quotas et déduplication inchangée.

## Fichiers à créer ou modifier après approbation

- sources : models.py, collection.py (nouveau), schemas.py/api.py, __init__.py,
  connectors/http_client.py et contrats internes de budget/autorisation au besoin.
  Pas d'adaptateur fournisseur ni de nouvelle dépendance.
- listings : models.py, collection_contracts.py (nouveau), collection.py (nouveau),
  repository.py pour factoriser les identités sans changer le comportement manuel,
  service.py/__init__.py et tests voisins.
- search : models.py, collection.py (nouveau), queue.py, executions.py,
  execution_schemas.py/api.py et tests voisins. app/worker.py seulement si le câblage
  l'exige, en préservant CvMaintenance et les modifications CV préexistantes.
- Composition : app/main.py/alembic/env.py seulement pour enregistrer modèles et
  services publics ; préserver leurs changements CV. Trois nouvelles migrations.
- Angular : core/search-api.ts, core/source-api.ts, scraping-translations.ts,
  pages/scraping et pages/search/results si affichage du scope/erreurs le nécessite ;
  un seul SSE et client SearchApi. Spécifications Jasmine et E2E existantes étendues.
- Documentation : README backend/frontend, rapport du lot 5, décisions, plans,
  TODO/CHANGELOG, AGENTS/CLAUDE et PROGRESS en dernier. SPEC immuable.

## Risques, alternatives et validation prévue

Choix recommandé : tables annexes et transaction partagée. Alternative colonnes sur
SearchTask/JobListing : moins de tables, mais changement des tables historiques et
confusion curseur réseau/filtre. Alternative ingestion puis checkpoint séparés :
plus simple en apparence, mais fenêtre de crash et doubles compteurs. Écartée.
Alternative deuxième queue : ne réutilise pas les garanties existantes. Écartée.
Sept tables ajoutent du code et du stockage : reçus bornés à la collecte, pas de
réponses brutes ; politique de rétention future à définir sans effacer un run actif.

Vérifications à exécuter après code, jamais présentées comme déjà réussies :

- PostgreSQL dédié .env.test : migrations aller/retour sur schéma jetable, historique
  conservé, concurrence de deux workers, profil actif unique et isolation propriétaire.
- Crash avant/après réservation, ingestion et commit de curseur, bail expiré,
  redémarrage, reçu rejoué : offres/observations/compteurs stables, quotas conservés.
- Autorisation expirée/retirée, source désactivée entre pages/en vol, URL/DNS dangereux,
  curseurs cycliques, source absente : refus avant requête ou commit selon frontière.
- Réseau simulé : retries/redirections consomment les quotas durables, Retry-After
  partagé entre profils, timeout, budget global multisource et octets décompressés.
- Dates imprécises, identité ambiguë, observations conservées, imports manuels
  inchangés et annulation durant COLLECT puis FILTER avec données déjà commitées.
- API/UI : scope par défaut historique, erreurs de validation, actions indisponibles
  en production sans adaptateur, scénario synthétique avec injection test uniquement,
  SSE/reload/annulation, FR/EN/clavier/mobile, absence de secrets dans réponses/logs.
- Ruff, format, mypy, pytest complet, Alembic check, frontières de modules,
  typage/build/Karma et Playwright. Aucun appel réel ni payant dans les tests.

## Accord attendu

Valider les interfaces additives, les sept tables annexes et les trois migrations
proposées, la transaction partagée et le périmètre simulé du lot 5 avant code.
Cet accord n'attribue aucune permission de source et n'approuve pas les autres lots,
la phase 4 CV ou un test réel. Le rapport de livraison sera un nouvel arrêt de phase.
