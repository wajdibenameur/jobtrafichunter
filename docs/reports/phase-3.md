# Phase 3 — Recherche locale, profils et résultats

Plan approuvé par « vasi » (D-019), lots 3.1–3.4 livrés.
**Validée par le propriétaire le 2026-11-08 (« ok », D-024).**

## Comportement livré

- Profils de recherche : création, édition, duplication, retrait par archivage,
  exemples explicites et idempotents, paramètres validés et isolés par propriétaire.
  Le module search possède profils/configurations ; profile reste le futur profil CV.
- Critères : sources, domaines/intitulés et valeurs personnalisées, mots-clés
  inclus/exclus, pays/villes, modes de travail, expérience, visa, publication et
  première découverte. Les inconnus sont conservés et signalés ou exclus selon
  le choix explicite ; un titre « Junior » ne remplace pas les années exigées.
- Recherche **dans les offres importées uniquement**, périmètre expliqué dans
  les pages. Aucun appel aux sites, collecte automatique ou score IA simulé.
  Les logs fournisseurs indiquent SKIPPED/MANUAL_ONLY, sans faux compteur collecté.
- Déduplication conservatrice et versionnée : identité normalisée, descriptions
  suffisamment longues, seuils configurables et cohérence de tous les membres
  avant regroupement. Dates différentes : relation de republication séparée ;
  publication inconnue ou ressemblance ambiguë : candidat à vérifier, sans fusion.
- Toutes les lignes originales et traces d’import restent intactes. Provenance
  additive et liens multiples affichés dans un résultat logique. La découverte
  ancienne est conservée même si seul le site plus récent est sélectionné.
- Queue PostgreSQL : claims SKIP LOCKED, token de lease, heartbeat, contrôle du
  verrou avant écriture, reprise après expiration, trois tentatives maximum avec
  backoff/jitter sur erreurs transitoires, une exécution active par profil.
- Annulation durable et coopérative, résultats déjà produits conservés. Snapshots
  des critères, données et résultats ; éditer/réimporter une offre n’altère pas les
  résultats d’une exécution terminée. Checkpoint de filtrage repris sans doublon.
- Progression SSE, récupération de l’état depuis la DB après rechargement,
  reconnexion et repli HTTP côté interface si le flux est interrompu.
- Pages Angular Recherche, Profils et Résultats, FR/EN, clavier et mobile ; filtres,
  pagination, tris découverte/publication/pays/domaine/visa, détail en dialogue
  avec champs inconnus et toutes les provenances. Dashboard : vrais imports et
  dernière exécution locale. CV, score et notifications restent indisponibles.

## Migrations et limites de traitement

0004_search_profiles, 0005_listing_provenance et 0006_search_queue ajoutent des
tables/indexes. Aucun changement des colonnes/contraintes existantes ou migrations
0001–0003. Elles sont appliquées au schéma applicatif local ; Alembic ne détecte
aucune opération manquante. La reprise des imports déjà présents est testée.

Une exécution examine au plus **500 imports récents** des sources choisies ;
chaque identité de déduplication est bornée à **100 candidats**. Au-delà : état
PARTIAL, aucun regroupement supposé, nouveauté non vérifiée signalée. Échéance
globale 15 minutes, traitement d’une tâche 3 minutes, heartbeat de lease 2 minutes.
Les exécutions sans worker restent en attente avec une instruction visible.

« Aujourd’hui » suit Europe/Paris, avec tests été/hiver. Le Windows local ne
fournissait pas ces données à ZoneInfo : [tzdata officiel](https://pypi.org/project/tzdata/)
2026.6 est ajouté, verrouillé et haché, sans autres mises à jour de dépendances (D-020).

## Lancement local

Après mise à jour, redémarrer l’API pour charger les nouvelles routes. Depuis
`backend`, avec `.env`, compte et TLS déjà configurés :

```cmd
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8443 --ssl-keyfile ../local-data/tls/localhost.key --ssl-certfile ../local-data/tls/localhost.crt --no-access-log --no-proxy-headers
```

Dans un **deuxième terminal CMD**, depuis `backend` :

```cmd
.venv\Scripts\python.exe -m app.worker
```

Pour un seul cycle : ajouter `--once`. Le cycle vérifie la DB et traite au plus
une tâche disponible ; ce n’est plus une simple sonde sans handlers.

Dans un **troisième terminal CMD**, depuis `frontEnd\jobhunter` :

```cmd
set "PATH=%CD%\..\..\.tools\node-v22.22.3-win-x64;%PATH%"
npm start
```

Ouvrir https://localhost:4200. Importer des offres dans Sources, enregistrer un
profil avec au moins une source dans Profils de recherche, puis lancer dans
Recherche. Voir sa progression et ouvrir Résultats. Aucun fournisseur n’est visité.

## Vérifications réelles

| Contrôle | Résultat |
| --- | --- |
| pytest complet avec backend/.env.test | **105 passed in 92.30s**, aucun skip |
| Couverture déduplication | **100 %** |
| Couverture filtres/nouveauté | **91 %** |
| Ruff check / format --check | Réussis, 86 fichiers formatés |
| mypy app | Réussi, 71 fichiers |
| Alembic upgrade head / check | Réussis, aucun écart de schéma |
| Angular typecheck et build production | Réussis |
| Karma/Jasmine ChromeHeadless | **21 SUCCESS** |
| Playwright avec vraie API et worker distincts | **9 passed (20.7s)** |
| pip-audit runtime et npm audit runtime | Aucune vulnérabilité connue signalée |

Backend : auth/scoping, profils, filtres, junior exigeant cinq ans, dates Paris,
provenances entre sites, concurrence de deux workers, verrou périmé et ancien
worker bloqué, reprise au checkpoint, annulation conservant les résultats,
tentatives bornées, timeout, API/SSE, données de résultats immuables, upgrade
avec anciennes offres et démarrage du worker dans un processus neuf.

E2E : sept parcours précédents conservés, création/duplication/retrait de profil,
critères sauvegardés, worker réel, deux provenances regroupées, exclusion selon
années exigées, suivi après rechargement, résultats/détail, texte HTML inerte,
FR/EN/mobile, erreur exploitable si aucune source sélectionnée. Captures locales
inspectées dans `.cache/frontend-e2e/screenshots`. Schéma, identifiants, API et
worker de test sont nettoyés après les parcours.

Une première exécution navigateur a révélé un défaut du worker séparé : ses tables
référencées n’étaient pas toutes enregistrées dans son propre processus, bien que
les tests chargent déjà l’API. Corrigé au point de composition par imports publics
auth/sources, puis couvert par un test de processus neuf et les E2E. Les journaux
d’erreur du worker ne contiennent que type et lignes de code, sans valeurs privées.

## Limites et suite proposée

La recherche porte sur les données saisies/importées, sans extraction IA des
descriptions. Une exigence absente d’un champ structuré reste inconnue ; aucune
inférence de niveau/visa n’est faite à partir d’un intitulé. La déduplication ne
garantit pas d’identifier tous les doublons ou toutes les republications ; elle
préfère préserver les occurrences et signaler les ambiguïtés.

Collecte fournisseur, CV/hybride, scores/calibration, notifications et planification
non disponibles. Historique local dans la page Recherche ; module complet de logs
et notifications prévu plus tard. GitHub CI et PostgreSQL 16 non exécutés.
Python 3.11 local conservé ; Docker, images et hébergement hors périmètre.
SPEC inchangé, template et changement analytics:false préexistants préservés.

Après validation : proposer le plan de **phase 4 — CV privés, parsing isolé,
versions et validation du profil**. Ne pas commencer cette phase avant accord.
