# Phase 4 — CV privés et profil candidat validé

2026-11-08. Plan approuvé avec la validation de phase 3 par « ok » (D-024).
Livraison locale Windows/Python 3.11 ; **en attente de validation du propriétaire**.
Apify reste reporté jusqu’au matching (D-023). Aucun appel Apify ou LLM externe.

## Fonctionnement livré

- Mes CV dans Angular standalone, thème Velson, FR/EN, versions et aperçu en texte
  inerte. Upload PDF/DOCX de 5 Mio maximum ; nouveau document ou nouvelle version.
- Original chiffré, immuable et téléchargé après authentification en pièce jointe,
  sans affichage du PDF brut dans l’origine web. Nom et texte extraits également
  chiffrés en PostgreSQL. La clé existante n’a pas été modifiée.
- Inspection dans un vrai AppContainer Windows, sans capacité réseau, avant
  publication. PDF chiffrés, JavaScript/actions actives, pièces jointes et objets
  incorporés refusés. DOCX contrôlé comme paquet Word, XML sans DTD/entités,
  sans macros/objets embarqués, avec tailles, ratios ZIP et nombre de parties bornés.
- Limites : 50 pages PDF, 50 000 caractères extraits, 10 Mio décompressés pour un
  DOCX, 500 parties et 2 Mio par partie XML ; plafond de ratio de compression 100.
  Job Object : 256 Mio, 10 s CPU, un seul processus ; délai parent 20 s et sortie
  256 Kio. Toute incapacité de vérifier l’isolation bloque l’extraction.
- Textes FR/EN et caractères arabes conservés en UTF-8. PDF sans texte signalé
  NEEDS_OCR ; aucun OCR ou convertisseur DOC installé/activé implicitement.
- Profil candidat distinct des profils de recherche : titre/résumé explicitement
  étiquetés, sections de formation/expérience/langues/certifications et mentions
  de compétences. Preuves page/span/texte exact, taxonomie et versions enregistrées.
- Taxonomie initiale de 19 noms/alias de compétences, modifiable par API protégée,
  bornée à 200 termes et 100 par catégorie. Ce sont des noms de technologies,
  jamais des faits de CV, des annonces ou des labels de calibration préfabriqués.
- Édition de tous les champs proposés, années d’expérience si connues et préférences
  personnelles séparées. Les corrections sont marquées USER_EDITED, les préférences
  USER_PREFERENCE ; aucune fausse preuve n’est attribuée à une saisie manuelle.
- Une correction crée un nouveau brouillon. L’original et le profil validé actif
  restent intacts. Préparation idempotente, nouvelle proposition explicite si
  demandée ; différences avec le parent, y compris les préférences.
- Validation explicite après relecture ; activation séparée et transactionnelle
  d’un seul profil/CV par propriétaire. Aucun score, visa ou niveau déduit du titre.
- Export authentifié de la version sélectionnée et de ses profils (original base64)
  et suppression confirmée de toutes les versions du document/données dérivées.
  L’audit conserve uniquement UUID/actions/dates ; pas de nom ou contenu.

## Persistance, reprise et frontières

Migrations **0007_cv_storage** et **0008_candidate_profiles**, additives : tables
CV, versions, audit, intentions, CV actif, profils candidats/versions/activation
et taxonomie. Migrations 0001–0006 et tables existantes conservées. Appliquées au
schéma applicatif local ; `alembic check` ne détecte aucune opération manquante.

Les intentions sont validées en base avant l’écriture chiffrée, puis le fichier
est publié atomiquement sans remplacement. Le worker existant reprend les
intentions de plus de cinq minutes : fichier publié → finalisation idempotente ;
fichier absent → FAILED. Une suppression interrompue reste à reprendre ; un échec
visible n’est pas présenté comme succès. Les temporaires chiffrés résiduels sont
retirés lors de la suppression du document. Aucun deuxième service/queue déployé.

`cv`, `profile` et `ai` exportent leurs interfaces publiques ; composition dans
main/Alembic/worker, inspection par contrat partagé injecté. Les API manuelles de
sources/listings/search et leurs protections restent inchangées. Upload binaire
avec nom UTF-8 encodé dans un en-tête, sans nouvelle dépendance multipart.
Limites de corps ciblées, session/Origin requis, propriété contrôlée sur chaque ID.

La préparation crée un profil Windows propre au projet et un runtime ignoré dans
`.cache`, lisible/exécutable par ce SID seulement en complément des droits du
compte. Les écritures du parseur dans son propre dossier de profil sont aussi
refusées. Aucun accès aux secrets backend transmis à l’enfant ; handles hérités
explicitement limités. Le détail du premier lot est dans
[cv-security-foundation.md](cv-security-foundation.md).

## Vérifications réelles

| Contrôle | Résultat |
| --- | --- |
| pytest complet, PostgreSQL dédié `.env.test` | **131 passed in 132.99s**, aucun skip |
| Ruff check / format | Réussis |
| mypy app | Réussi, 97 fichiers |
| Alembic upgrade head / check | Réussis, schéma sans écart |
| Angular app/spec/E2E typecheck et build | Réussis |
| Karma/Jasmine ChromeHeadless | **24 SUCCESS** |
| Playwright vraie API HTTPS/worker/parseur | **10 passed**, détail final dans PROGRESS.md |
| pip-audit des dépendances runtime hachées | Aucune vulnérabilité connue signalée |

Recontrôle lors de l'audit AI Job Agent du 2026-11-08 : **131 tests backend en
148,13 s**, **24 Angular**, **10 E2E en 30,2 s** ; Ruff/format/mypy, typage/build
et Alembic check réussis, révision courante 0008. Ces résultats complètent les
mesures de livraison ci-dessus. L'accord D-027 concerne la documentation, pas la
validation de cette livraison. Voir [l'audit](ai-job-agent-audit.md) et
[le plan proposé](../PLAN-AI-JOB-AGENT.md).

Sondes natives : réseau local, fichier canari privé, écriture runtime/profil
AppContainer et création d’enfant refusés ; mémoire/sortie/durée réellement
limitées. Tests avec PDF/DOCX synthétiques, Unicode FR/AR, PDF actif/chiffré,
EXE renommé, formats incohérents, macros, objets incorporés, XML dangereux et ZIP
excessif. Concurrence de versions, original différent conservé, crash avant/après
publication, reprise, séparation des propriétaires, chiffrement des données SQL,
validation obligatoire, brouillon sans effet sur l’actif, suppression en cascade.

E2E : upload réel, extraction native, édition/validation/activation séparées,
rechargement, téléchargement identique octet pour octet à l’original, export
conforme, suppression et absence de profil actif ensuite. Les neuf parcours
antérieurs sont conservés. Captures desktop/mobile inspectées dans le cache local.
Schémas, fichiers CV synthétiques, identifiants, API et worker de test nettoyés.

Échecs rencontrés puis corrigés : runtime Windows minimal, fermeture des pipes
en sortie excessive, nom `.rels` DOCX, UTF-8 des pipes et appel de fixture pypdf
retiré en version 7. Une suite complète a aussi subi 13 timeouts PostgreSQL ;
connexion locale revérifiée, puis suites complètes réussies. Les traces de fixture
qui pouvaient révéler des paramètres de connexion sont désormais masquées à
l’initialisation et au nettoyage. Aucun secret n’a été ajouté au dépôt.

## Lancement et limites

Depuis backend, préparer le runtime avec le même compte Windows que l’API,
API arrêtée pendant la préparation :

```cmd
.venv\Scripts\python.exe scripts\setup_cv_sandbox.py
.venv\Scripts\python.exe -m alembic upgrade head
```

Redémarrer l’API HTTPS et le worker suivant le README, lancer le frontend avec
le Node portable déjà configuré, puis ouvrir **Mes CV**. Le runtime est préparé
sur cette machine. `.env`/secrets et certificat existants conservés.

Cette extraction locale est une aide à la saisie, pas un parsing sémantique
calibré : les expériences/formations restent des entrées de section à relire,
les dates ne deviennent pas des années calculées, et une mention de compétence
ne prouve pas sa maîtrise. PDF complexes/non UTF-8 DOCX peuvent être refusés.
DOC historique et OCR restent indisponibles. Aucun CV personnel n’a été utilisé.
Le jeu propriétaire de dix CV anonymisés avec attendus reste nécessaire pour
mesurer la précision/rappel ; les fixtures synthétiques ne le remplacent pas.

Isolation native validée sur Windows uniquement ; les tests correspondants sont
spécifiques Windows. Cela ne prouve pas une résistance absolue à une faille OS.
GitHub CI et PostgreSQL 16 non exécutés. Aucun Docker/hébergement.

Après validation de cette livraison : proposer le plan phase 5 matching et
calibration. Ne pas commencer cette phase ni reprendre Apify implicitement.
