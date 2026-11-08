# Plan proposé — Phase 4 : CV privés et profil candidat validé

Date : 2026-11-08. Statut : **DELIVERED / WAITING_FOR_VALIDATION — D-026**.
Livraison et limites : [rapport de phase 4](reports/phase-4.md).
Le propriétaire a validé la phase 3 et ce plan par « ok » (D-024).
Le code est désormais livré ; la validation de cette livraison reste attendue.
Le propriétaire choisit d’attendre les modules CV et matching avant Apify (D-023).
La phase 3 est validée : [rapport](reports/phase-3.md).

## Résultat attendu

Ajouter ses CV, conserver leurs originaux privés et immuables, consulter les
versions, analyser le document, corriger les informations proposées et valider
explicitement un profil candidat avant de l’activer. Une réanalyse propose une
nouvelle version et un diff ; elle ne remplace jamais une validation existante.

La phase 4 fournit les données validées nécessaires au futur matching. Le score,
les recherches CV/hybrides et leur raccordement au moteur de recherche relèvent
de la phase 5, dont le plan sera présenté après validation de la phase 4.
Apify reste reporté jusque-là, désactivé et sans appel réel. Les imports et
recherches manuels continuent de fonctionner. Python 3.11, PostgreSQL local et
Angular/Velson sont conservés ; aucun service, Docker ou hébergement ajouté.

## Lots proposés

### 4.1 Stockage privé et cycle de vie

- Module `backend/app/modules/cv/` : modèles, schémas, service, repository,
  stockage et API ; exports publics exclusivement dans `__init__.py`.
- Fichiers chiffrés AES-256-GCM sous un dossier privé de `local-data/`, hors
  assets Angular et racine web, avec noms UUID générés par le serveur. Réutiliser
  la clé `CV_ENCRYPTION_KEY` existante sans la lire dans les sorties ni la remplacer.
  Nonces uniques, métadonnées liées au propriétaire et au document authentifiées.
- Limite de fichier de 5 Mo par défaut, contrôle de taille réelle même sans
  Content-Length, extension/type/signature/conteneur cohérents. Borne multipart
  distincte pour le surcoût du formulaire ; limites actuelles des autres routes
  conservées. Noms fournis par le client jamais utilisés comme chemins.
- Analyse des conteneurs DOCX/OLE et refus des macros, fichiers embarqués et
  archives excessives. Un en-tête PDF/ZIP/OLE seul ne suffit pas à accepter un CV.
- Upload et écritures atomiques, compensation et récupération des fichiers
  orphelins : le système de fichiers et PostgreSQL ne partagent pas de transaction.
- Liste, téléchargement authentifié, remplacement par nouvelle version, retrait,
  export et suppression des données dérivées ; audit sans contenu ni nom personnel.
  Un seul CV actif par propriétaire, activation concurrente testée.

### 4.2 Extraction locale et isolation

- Module `ai` pour l’extraction PDF/DOCX et le contrat d’analyse structuré ;
  module `profile` consomme les interfaces publiques de `cv` et `ai`.
- Avant d’introduire des bibliothèques : revue des documents officiels, licences,
  compatibilité Python 3.11, surface de risque et versions/hashes des dépendances.
  Aucun nouveau framework ni service d’IA requis dans cette phase proposée.
- Extraction en processus enfant à durée, mémoire et sortie bornées, environnement
  minimal sans secrets. Vérifier l’isolation réseau et système effective sous
  Windows : un subprocess Python seul n’est pas une sandbox. Si les protections
  nécessaires ne sont pas réalisables dans le périmètre local approuvé, arrêter
  l’analyse et présenter les options avant de proposer un fonctionnement dégradé.
- PDF textuel et DOCX : texte et preuves localisées (page/paragraphe/span), sans
  exécuter d’éléments actifs ni suivre de liens externes. Conserver les inconnus.
- PDF scanné et DOC historique : établir les outils locaux et leur isolation
  requis pour OCR/conversion. Pas d’installation ou de conversion implicite ;
  afficher un état exploitable si une capacité manque. Ne pas annoncer ces
  formats analysés avant vérification de leur chaîne complète.
- Première stratégie proposée : extraction locale et règles FR/EN avec provenance,
  validation humaine obligatoire, qualité limitée explicitement. Aucun CV envoyé
  à un fournisseur externe ; toute extension LLM fera l’objet d’un choix séparé.
- Taxonomie versionnée et alias de compétences ; aucune compétence, expérience,
  langue ou besoin de visa inventé. Les préférences saisies sont distinguées des
  faits du document et ne sont pas présentées comme des faits extraits.

### 4.3 Profil candidat et validation

- Module `profile` distinct des profils de recherche déjà détenus par `search`.
- Brouillons et versions : titre, résumé, formations, expériences, langues,
  certifications, compétences catégorisées et préférences. Faits avec preuves,
  champs absents signalés ; corrections utilisateur identifiées comme telles.
- Relecture, édition, validation et activation explicites. Éditer un profil
  validé crée un brouillon ; le profil actif validé ne change pas silencieusement.
- Réanalyse idempotente d’une version, erreurs visibles, diff avant acceptation.
  Suppression/activation concurrentes et références de versions contrôlées.
- Exporter une interface publique de lecture du profil validé pour la phase 5.
  Les champs `linked_cv_id` existants restent réservés ; ne pas activer un mode
  CV/hybride ou un filtre de score avant que le matching réel existe.

### 4.4 Angular et vérification complète

- Page `pages/cvs/`, éditeur de profil candidat, client typé et traductions FR/EN.
  Activer « Mes CV » dans le shell en conservant les profils de recherche existants.
- Upload, progression/erreurs, versions, téléchargement, état d’analyse, relecture,
  diff, validation, activation et suppression confirmée ; mobile et clavier.
- Aperçu textuel sûr en premier lieu ; pas d’URL publique de fichier ni insertion
  de HTML extrait. Toute prévisualisation du document brut nécessite un traitement
  isolé adapté, sans exécuter le contenu du document dans l’origine applicative.
- Afficher le matching et la collecte Apify comme indisponibles tant que leurs
  phases ne sont pas livrées ; ne pas proposer de scores ou recherches simulés.

## Fichiers et migrations proposés

| Zone | Changements après accord |
| --- | --- |
| `backend/app/modules/cv/` | Stockage privé, cycle de vie, accès, audit et tests. |
| `backend/app/modules/ai/` | Extraction locale, isolation, preuves, taxonomie et tests. |
| `backend/app/modules/profile/` | Brouillons/versions/diff/validation, API et tests. |
| `backend/app/core/body_limit.py`, Settings, `.env.example` | Limites ciblées et paramètres locaux optionnels ; aucun secret existant modifié. |
| `backend/app/main.py`, Alembic env, dépendances/lockfiles | Composition publique, enregistrement des tables et bibliothèques revues. |
| `frontEnd/jobhunter/src/app/` | Route Mes CV, shell, page/éditeur, client et traductions. |
| Tests backend, Angular, E2E | Fixtures synthétiques, sécurité, parcours et non-régression. |

Migrations additives proposées : tables CV/versions/audit/analyse, puis profils
candidats/versions/validation et taxonomie. Le numéro libre actuel est 0007, à
revérifier au démarrage ; aucune migration Apify n’existe encore. Tables et
migrations actuelles non modifiées. Contraintes d’unicité et de propriété définies
dans les nouvelles tables. Tout besoin imprévu de modification d’une table existante
sera présenté avant implémentation, conformément à AGENTS.md.

## Contrôles et limites de validation

- Tests de fichiers valides et invalides, EXE renommé, taille et ZIP bomb, macros,
  éléments embarqués, corruption, PDF chiffré, scan et capacité indisponible.
- Chiffrement/authenticité, chemins, accès sans session et autre propriétaire,
  immutabilité de l’original, logs sans texte/secret, export et suppression complète.
- Arrêt/timeout du parseur, absence de réseau/secrets, crash entre fichier/DB,
  analyse répétée, activation concurrente, versions et diff conservés.
- Ruff/format/mypy, pytest sur `.env.test`, migrations depuis 0006 et base vierge,
  architecture ; types/build/Karma et E2E avec vraie API et documents synthétiques.
- Parcours E2E : connexion → upload → extraction → correction → validation →
  activation → nouvelle version/diff → téléchargement/suppression. Les recherches
  manuelles existantes restent couvertes ; aucun fournisseur externe appelé.
- Les dix CV anonymisés avec résultats attendus requis par SPEC doivent venir
  du propriétaire avant toute affirmation de qualité calibrée. Les fixtures
  synthétiques ne remplacent pas ce jeu de référence et ne seront pas des CV réels.
- Rapport de phase avec résultats effectivement exécutés, capacités manquantes
  et commandes ; validation du propriétaire avant le plan matching de phase 5.

## Accord et clôture

Le propriétaire a validé la phase 3 et ce plan par « ok » (D-024). La livraison
de phase 4 attend maintenant sa validation ; matching en phase 5 et Apify ne sont
pas autorisés implicitement. Les capacités DOC/OCR manquantes restent explicites.
