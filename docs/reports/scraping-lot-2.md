# Scraping Engine — lot 2 : infrastructure des connecteurs

Date : 2026-11-08. Statut : VALIDATED (continuation propriétaire D-030).
Autorisation : continuation propriétaire « contenue » (D-029),
limitée au lot 2 du [plan](../PLAN-SCRAPING-ENGINE.md). Livraison depuis validée
pour continuer le lot 3 ; la fin du rapport conserve la proposition historique.
Ce document décrit l'infrastructure, pas une collecte fournisseur fonctionnelle.

## Périmètre

- Contrat existant étendu : limite par requête, fenêtre temporelle optionnelle,
  page typée avec cursor/truncation, capacités et états de santé. fetch reste
  disponible ; ManualConnector refuse aussi explicitement fetch_page.
- Registre interne extensible, sans adaptateur automatique enregistré. Les chemins
  manuels et connector_for historiques restent inchangés. Une factory future exige
  une autorisation complète pour être résolue ; aucun simple toggle n'y suffit.
- Autorisation fournie par un callback backend, propriétaire/source stables,
  enabled + PERMITTED + checklist actuelle via verified_automation. Endpoint de
  preuve lié aux domaines/chemins approuvés. Routes HTTPS explicites ; pas de
  sous-domaine implicite ni chemin voisin accepté. Chemins encodés refusés par
  prudence dans ce lot ; ce n'est pas un crawler universel.
- Transport GET uniquement, sans session/cookies/identifiants, sans proxy implicite,
  ni journal de requêtes HTTPX contenant URL/paramètres. Réponses et erreurs privées
  non copiées dans les messages d'erreur ; body/URL exclus du repr de réponse.
- Résolution IPv4/IPv6 contrôlée ; réponse DNS mixte publique/privée entièrement
  refusée. IP validée épinglée à connect_tcp, puis adresse effective du pair
  vérifiée. Nom original conservé pour Host/SNI et vérification TLS normale.
- Autorisation rechargée avant requête et après attente de quota, puis avant/après
  DNS et après connexion. Redirections validées individuellement, sans suivi
  automatique ni transfert de cookies. Identité compte/source ne peut changer
  au milieu d'un client de collecte.
- Budget d'exécution partagé entre redirections et tentatives : requêtes/pages,
  octets réseau/décodés et durée globale. record_results fournit le plafond de
  résultats que les futurs adaptateurs devront appeler avant de produire une page.
- Coordonnateur partagé au sein du worker : concurrence maximale 4, espacement
  par source, cooldown Retry-After commun, délais/backoff et trois tentatives max.
  Réveil précoce du timer Windows revérifié. Les 401/403 ne sont pas réessayés.
- Téléchargement en streaming ; identity et gzip acceptés, expansion gzip bornée
  pendant la décompression. Autres encodages, gzip tronqué ou multi-membres refusés.
  Fermeture du flux lors d'annulation, timeout et erreur.

## Fichiers et dépendances

Sous backend/app/modules/sources/connectors : contracts.py, registry.py,
manual_import/__init__.py, __init__.py et nouveaux access.py, network.py,
http_client.py. Tests synthétiques dans sources/tests/test_collection.py.

httpx 0.28.1 et httpcore 1.0.9 déclarés en runtime ; certifi rejoint le verrou
runtime, tous déjà présents dans l'environnement de développement. Versions
existantes conservées, verrous hachés régénérés hors ligne. Aucune bibliothèque
HTML installée : beautifulsoup4 attend le lot 3. Aucun service ou migration.
La dépendance pypdf et les autres changements CV préexistants restent dans leur
lot distinct ; ne pas les inclure par erreur dans le commit d'infrastructure.

Références d'extension officielles revues :
[HTTPCore network backends](https://www.encode.io/httpcore/network-backends/),
[pools](https://www.encode.io/httpcore/connection-pools/),
[HTTPX transports](https://www.python-httpx.org/advanced/transports/) et
[timeouts](https://www.python-httpx.org/advanced/timeouts/).

## Vérifications

| Contrôle | Résultat réel |
| --- | --- |
| pytest complet avec .env.test, --tb=short | 181 passed in 138.22s, aucun skip |
| Nouveaux tests ciblés | 50 passed in 3.32s |
| Ruff check / format --check | Réussis, 120 fichiers conformes |
| mypy app | Réussi, 101 fichiers |
| alembic check | No new upgrade operations detected |
| pip-audit requirements.lock | No known vulnerabilities found |

Tests Angular/build/E2E non relancés : aucun frontend, route API, worker ou table
modifié par ce lot. Dernière preuve frontend : 24 Angular / 10 E2E dans l'audit
AI Job Agent ; elle ne constitue pas une validation navigateur du futur Scraping.
Aucune source réelle testée et aucune négociation TLS réelle revendiquée.

Les fixtures couvrent permission absente/périmée/révoquée, DNS privé/mixte,
rebinding évité par connexion IP, pair incorrect, Host/SNI et vérification TLS,
redirects, URLs dangereuses, budgets, retries/quota, concurrence, confidentialité,
gzip excessif et interruption avec fermeture du flux. Le faux réseau traverse
le transport HTTPCore et son codec HTTP ; cela n'est pas une négociation TLS réelle.

Deux défauts révélés puis corrigés : Retry-After plafonné renvoyait parfois un int
non reconnu par le planificateur de retry, et asyncio.sleep pouvait se réveiller
légèrement avant le quota sous Windows. Les tests correspondants sont conservés.

## Limites et suite

Aucun parseur JSON-LD, adaptateur de site, endpoint de collecte, page Scraping,
planification ou matching ajouté. Les critères de recherche existants restent
inchangés ; le nouveau champ de requête interne ne livre pas les radios 2 h/6 h.
Le worker actuel n'appelle pas encore ce transport. L'intégration DB/queue relève
du lot 5 ; le callback devra alors charger l'état courant réel, sans cache permissif.

Le coordonnateur et les budgets sont en mémoire pour un processus/une exécution ;
ils ne promettent pas de quotas durables entre redémarrages ou plusieurs workers.
Cette persistance et la désactivation durable après blocage relèvent de l'intégration.
La vérification des permissions humaines/robots reste obligatoire ; le callback
ne la remplace pas. Aucun PERMITTED attribué, aucun appel fournisseur ou Apify.
Phase 4 et autres plans non validés implicitement par cette livraison.

Après validation : préparer le lot 3 d'extraction sur fixtures, puis ne choisir
un adaptateur réel qu'avec permissions établies et documentées.
