# Plan proposé — Phase 2 : sources et connecteurs

Date : 2026-11-07. Statut : DELIVERED / WAITING_FOR_VALIDATION (D-014, D-015).
Livraison et contrôles réels : `reports/phase-2.md`.
La continuation du propriétaire valide le socle local de phase 1 et ce plan.
Python 3.11, Angular et PostgreSQL locaux ; aucun Docker ou hébergement.

**Modification approuvée D-015 :** la livraison utilise LinkedIn, Indeed, Keejob
et Tanitjobs en liens/import manuel, plus sources personnalisées. Aucun connecteur
automatisé fournisseur n'est attendu pour cette phase. Les objectifs automatisés
ci-dessous décrivent le plan initial et restent différés, sans bloquer la livraison
manuelle expressément choisie par le propriétaire.

## Résultat attendu

Une page Sources permettant de consulter, activer/désactiver et configurer les
sources réellement disponibles, voir leur intégration et les erreurs de santé,
ouvrir un lien de recherche ou importer manuellement une offre. Aucun bouton
de synchronisation ne doit faire croire que l'orchestrateur existe déjà.

Le framework permettra d'ajouter un connecteur dans son dossier et de l'enregistrer
sans changer son orchestrateur futur. Objectif : deux connecteurs automatisés
utilisables après vérification complète, un troisième seulement si les conditions
et accès sont confirmés. Le nombre de connecteurs autorisés ne sera pas inventé
pour déclarer la phase terminée.

## 2.1 Registre et vérifications

- Module `backend/app/modules/sources/` : `api.py`, `service.py`, `repository.py`,
  `models.py`, `schemas.py`, `events.py`, `__init__.py` et `tests/`.
- Modèle `JobSource` : identité, propriétaire, type d'intégration, état souhaité,
  état effectif, paramètres validés, fréquence, santé et compteurs disponibles.
- Checklist de vérification stockée : méthode/URL officielle, accès nécessaire,
  conditions et date de revue, robots et résultat, stockage/attribution/limites,
  preuves, relecteur et échéance. Distinguer problème d'accès et absence de résultat.
- Sources initiales du SPEC en migration ; aucune source non vérifiée n'est
  activée automatiquement. Une source personnalisée commence en lien/import,
  jamais avec une URL arbitraire à récupérer depuis le serveur.
- Revue expirée à 90 jours : statut effectif UNVERIFIED et collecte interdite,
  même si un ancien indicateur enabled est resté vrai en base.
- UI ne peut pas transformer un simple toggle en autorisation PERMITTED.

## 2.2 Contrat des connecteurs et clients

- Sous `sources/connectors/` : contrat `JobSourceConnector`, registre, erreurs
  typées, DTO de requête/résultat, capacités et contexte de vérification.
- Interface Python commune : `fetch`, `normalize`, `health_check`, `capabilities`.
- Transport httpx (prévu au SPEC, à déplacer des dépendances dev vers runtime),
  timeouts, tailles maximales, User-Agent explicite, cache, Retry-After, limites
  persistées et retries bornés. Aucun retry pour AUTH/BLOCKED.
- Hôtes/endpoints autorisés par connecteur ; redirections/pagination validées
  contre la liste autorisée pour éviter accès localhost, métadonnées ou URL injectée.
- Normalisation sans score, sans inférence de visa, sans invention de dates.
  Une erreur de transport ou de parsing n'est jamais retournée comme liste vide.
- Cache partagé par source : plusieurs futurs profils ne doivent pas multiplier
  les appels au-delà des restrictions du fournisseur.
- Dossiers et README propres aux seuls connecteurs dont la méthode autorisée
  aura été confirmée. Les candidats ambigus conservent leur dossier de preuves,
  sans code de collecte automatisée écrit tant que l'ambiguïté subsiste.

## 2.3 Liens et import manuel

- Génération de liens HTTPS de recherche par source avec encodage des critères.
  Aucun suivi automatique du lien, aucune session navigateur utilisée.
- Formulaire URL/description et CSV explicite ; une URL seule n'autorise pas
  la récupération de la page distante. Confirmer les champs extraits avant import.
- Pour rendre l'import réellement persistant dès cette phase, introduire le
  **socle minimal du module listings** : même structure de module, `JobListing`
  conforme au SPEC, import structuré sans LLM et endpoint `POST /api/jobs/import`.
- Les tables sont détenues par listings ; les sources sont référencées par id,
  sans import de leur repository/modèle. Le point de composition assemble les
  services publics pour l'import et l'authentification ; tests de frontières maintenus.
- Conserver URL originale et normalisée, source, contenu utilisateur et première
  découverte ; import idempotent d'une URL normalisée. Déduplication floue,
  reposts, fusion cross-source et recherche restent à la phase 3.
- URL seule et description inconnue : conserver les inconnus, demander le texte
  manuellement ; ne pas afficher une offre complète ou un score prétendument calculé.
- Pas d'exécution complète de recherche ni de matching/Telegram dans cette phase.

## 2.4 Migrations et sécurité

- Ajouter `0002_sources` : registre/checklist/santé et sources initiales.
- Ajouter `0003_listings_import` : socle d'offres et traces d'import nécessaires.
  **Ne pas modifier `0001_auth` ni les tables auth déjà appliquées.**
- Prévoir contraintes/indexes et références par id sans importer les modèles
  internes des autres modules. Identité d'offre, liens sources et occurrences de
  republication seront précisés avec le plan de phase 3 avant toute évolution.
- Enregistrer les modèles via interfaces publiques dans Alembic ; vérifier
  cohérence modèles/migrations et mises à niveau depuis la phase 1.
- Endpoints protégés et scoping propriétaire, via principal de requête partagé
  défini par l'auth et raccordé au point de composition. Aucune dépendance auth
  cachée dans les repositories métier, aucun accès transversal aux tables.
- Politique de taille adaptée pour le CSV avec validations explicites, erreurs
  sans contenu sensible, textes rendus comme texte et liens sans schéma dangereux.
- Toute configuration de source est validée ; aucun secret dans ses réponses API.

## 2.5 Frontend

- `src/app/pages/sources/` : cartes de sources, filtres, sélection globale pour les
  sources éligibles, badges API/FEED/LINK_ONLY/MANUAL_IMPORT/DISABLED, santé et détail
  des restrictions. Actions réelles seulement ; bouton disabled expliqué si absent.
- Activer la route Sources et le lien existant du shell. Garder Velson et FR/EN.
- Formulaire d'import manuel et confirmation des données, erreurs par ligne CSV,
  retour de succès réel depuis l'API. Pas de description HTML injectée dans la page.
- Étendre `core/api.ts` avec DTO typés, états chargement/erreur/vide et accès clavier.
- Ne pas modifier les réglages préexistants de `angular.json` ni le template.

## 2.6 Tests et livraison

- Unitaires : politique d'activation, expiration à 90 jours, génération des liens,
  mapping, limites, URL dangereuses, parsing CSV et idempotence d'import.
- Contrats sur fixtures/respx (outil prévu par SPEC, dépendance dev à verrouiller) :
  succès, vrai résultat vide, timeout, 401/403/429, Retry-After, schéma invalide,
  pagination et redirections hors hôte ; attribution et champs inconnus.
- Intégration PostgreSQL `.env.test` : migration vierge et upgrade auth → sources
  → import, persistance des toggles, scoping propriétaire, rejet non authentifié,
  impossibilité d'activer une source non permise et import répété sans doublon.
- Tests Angular cartes/formulaires et E2E source activable/non permise, lien de
  recherche, erreur de santé visible et import manuel. Tests sans accès live aux
  fournisseurs en CI ; smoke live seulement sur API autorisée et budget respecté.
- Ruff, mypy, build/typecheck Angular, audits et vérifications d'architecture.
- Après chaque tâche : CHANGELOG et PROGRESS, commit du lot testé. En fin de phase :
  `docs/reports/phase-2.md`, bilan des sources effectivement permises et pause.

## Candidats après pré-vérification du 2026-11-07

Voir `docs/sources/preverification-phase-2.md` pour les liens et limites.

| Candidat | État actuel | Conséquence proposée |
| --- | --- | --- |
| JobTech JobSearch (Suède) | Catalogue officiel CC0 favorable ; accès/quota/robots restant à vérifier | Priorité d'étude, pas encore PERMITTED |
| Arbeitnow | API officielle gratuite ; restrictions générales de copie/stockage à clarifier et robots non récupéré | UNVERIFIED, pas de collecte pour l'instant |
| Remotive | Documentation API et conditions/robots actuels en tension | Lien/import seulement jusqu'à clarification |
| France Travail | Licence et accès fournisseur à vérifier, aucun accès utilisateur présumé | Préparer seulement si accès autorisé réellement disponible |
| LinkedIn/Indeed/Keejob/Tanitjobs | Aucun accès automatisé vérifié dans ce projet | Liens/import, sans scraping |

Ce plan ne déclare aucune source PERMITTED et n'autorise pas à ignorer une
restriction pour atteindre le quota de connecteurs du SPEC. Si deux intégrations
ne peuvent pas être confirmées, exposer le blocage et faire approuver des sources
de remplacement ; conserver le reste du travail générique utilisable.
