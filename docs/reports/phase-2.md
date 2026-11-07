# Phase 2 — Sources et import manuel

Livrée le 2026-11-07, **en attente de validation du propriétaire**.
Plan approuvé D-014 puis périmètre manuel choisi D-015 : LinkedIn, Indeed et
sites tunisiens Keejob/Tanitjobs. Python 3.11, Angular et PostgreSQL locaux.

## Livraison

- Registre des quatre sites, préférences par propriétaire, mots-clés/lieu,
  sélection globale et individuelle, ajout/retrait de sites personnalisés.
- Page Sources FR/EN dans le thème Velson, filtres dont « Sites tunisiens »,
  navigation mobile et vrais états de chargement/erreur. Template original conservé.
- Liens HTTPS avec critères encodés ; aucune ouverture ou collecte côté serveur.
  Keejob incorpore le lieu aux mots-clés. Les sites personnalisés ouvrent leur
  accueil et indiquent que les critères sont à saisir sur le site.
- Contrat et registre de connecteurs manuels : capacités, normalisation bornée,
  statut MANUAL_ONLY, erreurs PARSE_ERROR/MANUAL_ONLY/UNAVAILABLE explicites.
  Aucun connecteur API fournisseur enregistré, aucune source PERMITTED déclarée.
- Import URL et champs connus, aperçu local puis confirmation. CSV UTF-8 jusqu’à
  200 lignes/512 Ko, aperçu serveur, erreurs par ligne et confirmation bloquée si
  une ligne est invalide. Aucun LLM ou parsing automatique d’une page distante.
- Offres et traces d’import persistantes, liste paginée des imports réels.
  Champs absents inconnus, publication distincte de la première découverte,
  provenance et URL originale conservées. Pas de score inventé.
- Import atomique, unicité propriétaire/URL normalisée et source/identifiant.
  Réimport sans doublon, enrichissement explicite sans effacer les champs absents,
  conservation de first_seen_at ; conflits ambigus annulent tout le lot.
- Endpoints protégés, principal de requête partagé et sessions métier séparées.
  Frontières des modules contrôlées ; URL HTTPS sans identifiants, IP littérale
  ni port arbitraire ; limites de corps, champs et URL normalisée pour PostgreSQL.
- Migrations append-only 0002_sources et 0003_listings_import appliquées dans
  le schéma applicatif local. Aucune modification des tables auth existantes.

## Utilisation locale

Redémarrer le backend si son ancien processus tourne encore. Depuis `backend`,
avec `.env` et TLS déjà configurés :

```cmd
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8443 --ssl-keyfile ../local-data/tls/localhost.key --ssl-certfile ../local-data/tls/localhost.crt --no-access-log --no-proxy-headers
```

Dans un second CMD, depuis `frontEnd\jobhunter` :

```cmd
set "PATH=%CD%\..\..\.tools\node-v22.22.3-win-x64;%PATH%"
npm start
```

Ouvrir https://localhost:4200 puis **Sources**. Sélectionner un site, enregistrer
ses critères et ouvrir sa recherche. Coller une URL et, si disponibles, le titre,
l’entreprise, le lieu et la description. Vérifier l’aperçu avant de confirmer.

CSV minimal d’exemple **synthétique**, sans vraie offre :

```csv
url;title;company;city;description
https://example.test/jobs/fixture;Exemple fictif;Entreprise fictive;Tunis;Texte de test
```

## Vérifications exécutées

| Contrôle | Résultat réel |
| --- | --- |
| `python -m pytest -q --tb=short` avec backend/.env.test | **81 passed in 48.86s**, aucun skip |
| Ruff check + format --check | Réussis, 63 fichiers formatés |
| `python -m mypy app` | Réussi, 51 fichiers |
| `alembic upgrade head` puis `alembic check` | Réussis, aucune opération manquante |
| `scripts/frontend.ps1 typecheck` | Réussi, app/spec/E2E |
| `scripts/frontend.ps1 build` | Réussi, budget respecté sans avertissement |
| Karma/Jasmine ChromeHeadless | **18 SUCCESS** |
| `python scripts/frontend_e2e.py` | **7 passed (12.4s)**, schéma et identifiants jetables nettoyés |
| npm audit runtime + pip-audit requirements.lock | Aucune vulnérabilité connue signalée |

E2E : connexion/session expirée/mobile existants, sites tunisiens, préférences
après rechargement, lien encodé, site personnalisé, aperçu sans écriture,
confirmation, texte HTML rendu inerte, réimport sans doublon, erreurs puis succès
CSV, affichage des preuves de visa et dates explicitement fournies avant confirmation.
Captures desktop 1440 px et mobile 390 px inspectées dans `.cache/frontend-e2e`.

Un test E2E intermédiaire attendait un changement immédiat du checkbox alors que
la sélection attend la confirmation serveur ; corrigé pour attendre la réponse.
Un avertissement de budget CSS a été supprimé en réduisant des styles redondants.
Le build final et les sept parcours ont ensuite réussi. Le sandbox Windows exige
l’exécution autorisée des sous-processus Angular/Chrome ; aucun réglage global
de Node ou de Chrome n’a été modifié.

## Limites et suite

Cette livraison ne comprend aucun connecteur automatisé fournisseur, transport,
retry/cache/quota HTTP ou tests de contrats réseau : retirés du périmètre courant
par D-015. Les liens sont générés/testés sans naviguer vers de vraies offres ;
la pertinence des moteurs externes et leur couverture ne sont pas garanties.
Une URL seule reste une offre incomplète. Détection de visa, extraction IA,
matching, recherche orchestrée, queue et Telegram ne sont pas disponibles.
La déduplication floue et les republications restent à la phase suivante.

GitHub CI/PostgreSQL 16 non exécutés ; pas de remote configuré. Docker et
hébergement hors périmètre. SPEC immuable ; angular.json préexistant préservé et
exclu des commits. Aucun secret, fichier .env, offre réelle ou asset privé ajouté.

Prochaine étape proposée après validation : plan de phase 3 pour critères/profils,
queue PostgreSQL, orchestrateur, déduplication et page Résultats. Ne pas commencer
cette phase avant l’accord du propriétaire.
