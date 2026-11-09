# Scraping Engine — lot 5 : queue, worker et persistance

Livraison locale : 2026-11-09. Statut : LOCAL_DELIVERED / WAITING_FOR_OWNER_VALIDATION.
Décision D-033 ; base CV versionnée pour publication GitHub (D-034).
[Plan approuvé](../PLAN-SCRAPING-LOT-5.md), [plan général](../PLAN-SCRAPING-ENGINE.md).
Le propriétaire a approuvé les interfaces et migrations par continuation après
le commit documentaire 5b7201a. Validation de livraison distincte attendue.

## Fonctionnement livré dans l'arbre local

- Même SearchQueue, worker, heartbeat, bail/fencing et index de profil actif.
  Scope explicite COLLECTED_OFFERS, pipeline COLLECT → SCAN → FILTER ; défaut
  IMPORTED_OFFERS conservé. Les critères enregistrés et snapshots restent immuables.
- CollectionPlan et checkpoints par source : critères/limites figés, curseur opaque,
  pages, compteurs, source_deadline, query_hash, motifs typés. L'état se relit en base.
- Sources séquentielles, maximum global de lecture 10 par défaut / 500 au plus,
  doublons compris, partagé entre sources. Filtrage sur le catalogue des sources
  sélectionnées, y compris leurs offres déjà connues ; ce maximum n'est pas une
  promesse de résultats retenus ni un effacement du catalogue historique.
- Autorisation actuelle et limites plus strictes revérifiées avant requête,
  reprise et ingestion. Configuration, préférence, archivage, statut et preuves
  expirées ne deviennent jamais des permissions par copie du snapshot.
- Réservations HTTP durables : tentatives/retry/redirections, octets réseau et
  décompressés réservés avant envoi ; décompte réel après réponse connue. Une
  interruption incertaine garde sa réservation conservatrice, même après reprise.
- Créneau source durable : requête en cours bornée, délai minimal après réponse,
  Retry-After partagé entre profils. Un créneau abandonné expire ; son ancien
  règlement ne peut pas effacer le créneau d'une réservation plus récente.
- BLOCKED/AUTH désactivent la collecte avec besoin de revue ; trois erreurs SCHEMA
  consécutives aussi. Aucun retry sur ces erreurs permanentes. Pas de faux succès vide.
- Transaction courte commune : fence, annulation, permission actuelle, ingestion,
  reçu, observations, compteurs et avancement du curseur. Aucun verrou tenu pendant
  le réseau, aucun commit imbriqué dans l'ingestion publique listings.
- Canonicalisation, identités et groupements existants réutilisés. Collecte d'une
  identité déjà connue : conserver les champs métier, imports et first_seen_at ;
  actualiser last_seen_at et ajouter une observation. Aucun enrichissement silencieux
  du contenu confirmé manuellement. Conflit d'identités explicite, pas de fusion forcée.
- Reçu par page idempotent : relecture sans double ingestion ni double compteur.
  Reprise technique sur la même exécution et le dernier checkpoint ; réseau au
  moins une fois. Annulation terminale, données déjà commitées conservées ; une
  relance volontaire après annulation crée une nouvelle exécution.
- Les dates DATE/LOCAL_DATETIME et métadonnées JSON-LD restent des observations
  privées/versionnées ; pas d'heure inventée dans published_at. Les règles horaires
  strictes et le filtrage local restent ceux du lot 4.

## API et interface

- POST /api/search/executions accepte scope et max_results optionnels ; scope local
  par défaut, paramètres de collecte refusés en mode local. Les sources choisies
  doivent toutes être éligibles avant création de la tâche.
- GET /api/sources/{id}/collection et POST /collection/test : capacités/raisons,
  isolation propriétaire et mêmes gardes. Aucune URL de téléchargement libre ni
  route permettant de transformer une permission en simple préférence utilisateur.
- Interfaces intermodules exportées par __init__.py. DTO d'ingestion propres à
  listings ; traduction dans search, sans dépendance sources ↔ listings.
- Angular : Tester/Lancer/Arrêter/maximum raccordés aux contrats, seulement avec
  capacités réelles. Maximum par exécution, pas de nouvelle préférence persistée.
  Un brouillon de critères doit être enregistré avant lancement.
- Le lancement ouvre Recherche avec l'identifiant d'exécution : suivi SSE,
  reconnexion, annulation et résultats existants réutilisés. Pas de second client SSE.
  Scraping recharge ses statuts/historique par GET et actualisation manuelle.
- Scopes, progression et erreurs source distingués de l'historique local. La
  fréquence reste désactivée ; CV/matching/notifications ne sont pas simulés en produit.
- Association explicite label/select de Recherche corrigée après un échec E2E
  intermittent ; assertions historiques conservées. Design Velson, FR/EN et mobile.

## Migrations et prérequis de versionnement

Trois migrations additives : 0009_collection_sources, 0010_collection_search,
0011_collection_listings. Sept tables annexes, contraintes et index propres ;
aucune modification des tables historiques ni réécriture des migrations CV.
La migration sources inclut l'identifiant de réservation active du créneau durable.

**Dépendance résolue pour publication (D-034) :** 0009 dépend de 0008_candidate_profiles.
Les fichiers CV 0007/0008 et leur code préexistants sont versionnés séparément dans
2b34645, sur demande de mise du projet sur GitHub. Le lot 5 peut désormais être
versionné à sa suite avec une chaîne Alembic complète. Ce versionnement ne valide
pas implicitement la livraison de phase 4 CV ni celle du lot 5.

Les migrations de ce lot sont exécutées uniquement dans des schémas jetables de la
base dédiée .env.test. Aucune migration sur la base personnelle. Pour déployer la
version locale après revue des migrations : appliquer alembic upgrade head puis
redémarrer API et worker. Sans les tables annexes, ne pas utiliser cette version
de l'API contre un ancien schéma. Le downgrade du lot supprime ses observations,
à réserver aux tests jetables ; les imports historiques restent conservés.

## Vérification réelle

| Contrôle | Résultat |
| --- | --- |
| Ruff check / format --check / mypy | Réussis, 131 fichiers formatés / 109 fichiers typés |
| Suite backend complète avec .env.test et parseur Windows natif | 272 passed in 259.13s, aucun skip |
| Tests ciblés de collecte/migrations | 24 passed in 107.95s après correction de concurrence |
| Alembic aller-retour et check sans dérive | Réussis dans le test de schéma jetable, imports préservés |
| Typage Angular app/spec/E2E et build production | Réussis, budget respecté |
| Karma ChromeHeadless | 37 SUCCESS, dont 4 nouveaux cas |
| Playwright HTTPS/worker et scénario simulé | 12 passed in 40.9s, dont un nouveau parcours |

Captures `collection-simulated-desktop.png` et `collection-simulated-mobile.png`
inspectées dans `.cache/frontend-e2e/screenshots` : page lisible, tiroir mobile fermé,
aucun débordement horizontal. Le scénario attend la fin du déplacement de la sidebar
avant la capture, sans attente arbitraire. Les schémas, identifiants et CV synthétiques
du harness E2E sont nettoyés. Captures privées de test non ajoutées à Git.

Tests nouveaux : pipeline réel avec transport simulé, protection du manuel, reprise
après page commitée, crash entre ingestion et checkpoint, reçu rejoué, annulation
et perte de bail, révocation en vol, permission expirée, quotas HTTP/pages/octets,
plafond multisource, curseur cyclique, erreurs 401/403/429/500 et auto-désactivation,
concurrence de profils, migrations aller-retour, isolation/API et absence de secret.
Angular : refus sans capacité, critères non enregistrés, lancement limité,
test de source refusé, restauration d'historique et annulation.

Échecs rencontrés et traités : fixture HTTP initialement préchargée incompatible
avec le lecteur de flux brut ; premier essai complet en bac à sable interrompu
après erreurs des tests natifs, suite relancée avec accès Windows requis ; libellé
du sélecteur de Recherche instable après chargement ; test de concurrence révélant
un délai entre réservations insuffisant pour espacer les envois réels. Correction
du créneau durable, sans abaisser l'assertion de délai ni ajouter de retries de test.

## Limites et prochain arrêt

Aucun adaptateur réel enregistré, aucune source éligible en installation normale.
Les champs PERMITTED des fixtures sont synthétiques dans les tests jetables,
jamais des preuves d'autorisation pour un site. Aucun appel fournisseur/payant,
aucune activation LinkedIn, Indeed, Keejob ou Tanitjobs. Imports manuels conservés.
Pas de scheduler, matching, notifications ou génération de candidature dans ce lot.
Pas de nouvelle dépendance, Docker, hébergement ou CI distante exécutée.

Les offres déjà commitées restent dans le catalogue lors d'une annulation COLLECT ;
des résultats filtrés peuvent alors ne pas exister encore. Les observations ne
mettent pas à jour le contenu métier connu ; la politique de rétention est future.
Les plafonds de lecture sont des limites techniques, pas une garantie de coût réseau
global ; un créneau/réservation conservateur après crash peut réduire le volume utile.

Attendre validation du lot 5 ; sa base CV est versionnée pour publication D-034. Préparer
ensuite le plan commun matching/alertes selon les prérequis de phase 4 et données
labellisées, sans déduire leur approbation de cette livraison.
