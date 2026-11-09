# Phase 5 — matching CV/offres : plan détaillé

Date : 2026-11-09. Statut : PROPOSED / WAITING_FOR_OWNER_APPROVAL (D-036).
Continuation après CI verte : préparation du prochain chantier, pas approbation
implicite des livraisons de phase 4 CV ou Scraping lot 5, ni autorisation de coder.
Ce plan précise le matching commun du lot 3 [AI Job Agent](PLAN-AI-JOB-AGENT.md)
et du lot 6 [Scraping](PLAN-SCRAPING-ENGINE.md), sans dupliquer leurs moteurs.

## Ordre proposé et accord demandé

1. Confirmer les livraisons [CV/profil phase 4](reports/phase-4.md) et
   [collecte/queue lot 5](reports/scraping-lot-5.md), toutes deux testées mais
   encore en attente de validation fonctionnelle du propriétaire.
2. Approuver la phase 5A décrite ici : prévisualisation locale du matching,
   preuves, scores provisoires, versions/cache et reprise, uniquement à la demande.
3. Après livraison/validation 5A : phase 5B de calibration sur annotations réelles
   du propriétaire et seuils convenus, sans fabriquer les jeux manquants.
4. Phase 5C ensuite : recherche CV/HYBRID et exploitation des scores calibrés.
   Ordonnancement/alertes/Telegram feront l'objet du plan commun suivant.

LLM_PROVIDER=none pour 5A, aucune API distante, nouvel SDK, embedding ou pgvector
nécessaire. Ce mode de repli est prévu par SPEC §18 ; sa qualité d'extraction est
limitée et doit rester visible. Apify et connecteurs réels restent séparément bloqués.

## Audit du code actuel

- ProfileService.validated_active existe et fournit une révision validée active,
  son CV, des faits/preuves/préférences et les champs inconnus. Les préférences ne
  constituent pas une preuve de diplôme, niveau, langue ou droit au travail.
- CandidateFields conserve encore éducation/expériences/langues comme listes de
  textes ; certains sous-scores resteront inconnus, sans reconstruction inventée.
- TaxonomyService et SkillDefinition sont publics dans ai : reprendre alias et
  révisions. Il n'existe ni analyse structurée d'offre ni module matching.
- ListingFact offre les compétences obligatoires/facultatives saisies, années,
  description et visa. SearchResult garde le snapshot de l'offre retenue dans son
  groupe ; ne pas le modifier pour y écrire du contenu issu du CV.
- ExecutionService refuse actuellement mode CV/HYBRID, linked_cv_id et min_score.
  Garder ces restrictions en 5A : un aperçu n'est pas une recherche CV calibrée.
- La queue actuelle possède SCAN/FILTER/COLLECT, bail, heartbeat, annulation et
  reprise. _batch termine aujourd'hui l'exécution au dernier lot FILTER : faire
  évoluer cette transition seulement pour les nouvelles demandes d'aperçu.
- Frontières existantes : search peut utiliser profile/matching/listings ; matching
  peut utiliser profile/ai, pas les tables ou services privés de listings/cv/search.
  Aucun de ces contrôles ne doit être contourné pour aller plus vite.

## Phase 5A — fonctionnement concret proposé

L'utilisateur choisit son profil de recherche et demande explicitement un aperçu
avec le candidat validé actif. Les filtres locaux existants sélectionnent les offres,
puis une étape MATCH produit les explications. Le bouton est indisponible sans CV
actif validé et lisible ; le backend effectue les mêmes contrôles.

Une nouvelle demande peut aussi rescorrer les résultats d'une exécution terminée :
créer une nouvelle SearchExecution liée à l'originale, recopier ses snapshots
d'offres dans la nouvelle exécution, commencer à MATCH. Aucun nouvel appel source,
aucune réouverture de l'ancienne tâche ou modification de ses résultats.

5A accepte uniquement le candidat actif, pas un CV secondaire non actif. Un
linked_cv_id différent reste refusé explicitement. La sélection complète de CV
par profil et la génération de critères depuis le CV seront détaillées en 5C.
Le seuil min_score et les notifications restent indisponibles tant que la
calibration n'est pas validée. Aucun tri par défaut présentant le score provisoire
comme une recommandation ; tri exploratoire éventuel explicitement nommé.

## Interfaces et respect des frontières

| Interface proposée | Rôle |
| --- | --- |
| profile.ProfileService.for_matching(owner, expected_revision) | Vérifier profil validé/actif, propriété et disponibilité du CV ; retourner un DTO minimal de faits/preuves/préférences, sans coordonnées inutiles |
| ai.JobAnalysisService.analyze(owner, job_input, taxonomy_snapshot) | Extraction locale bornée ; compétences exigées/préférées, expérience/langues/études/localisation/visa avec spans, négations, incertitudes et versions |
| matching.MatchingService.prepare / score_batch / finish | Figer le candidat/politique, calculer/cacher et enregistrer les résultats ; participer à la transaction de l'appelant sans commit imbriqué |
| matching.MatchJobInput / MatchPreview / ScoringPolicy | DTO indépendants de ListingFact et de SearchResult ; aucun import listings dans matching |
| search orchestration | Lire ses snapshots, convertir vers MatchJobInput, appeler matching publiquement et appliquer bail/annulation/transactions |

Les nouveaux services/DTO sont exportés par __init__.py. matching ne lit jamais
SearchResult, CandidateProfileVersion ou CvVersion directement. Une référence FK
par identifiant ne confère pas un droit de lecture sur la table d'un autre module.
L'analyse d'offre et la taxonomie sont communes au scoring futur, sans second moteur.

## Analyse et score déterministe

- Données explicites du snapshot et leur origine conservées ; distinguer saisie
  manuelle, déclaration fournisseur, extraction locale et préférence utilisateur.
  Description absente/ambiguë : champs inconnus, avertissement et faible confiance.
- Exigences détectées avec preuve textuelle et offsets dans la description figée.
  Bornes de mots/alias, sections obligatoire/préféré, négation et phrases
  contradictoires testées ; pas de compétence obligatoire déduite du seul titre.
- Pas de calcul d'années en additionnant naïvement des expériences qui se
  chevauchent. Utiliser years_experience validé, sinon inconnu. Une préférence
  Junior n'atteste pas une séniorité réelle. Une langue sans niveau ne prouve pas C1.
- Visa : jamais de sponsorship ou de droit au travail inventé. Les restrictions
  géographiques restent distinctes d'une simple préférence de pays/remote.

Poids initiaux de SPEC §18, versionnés et configurables par politiques immuables :

| Composante | Poids sur 100 |
| --- | --- |
| Compétences obligatoires | 35 |
| Compétences facultatives | 10 |
| Expérience/séniorité | 20 |
| Domaine/titre | 10 |
| Langues | 10 |
| Localisation/mode de travail | 5 |
| Études | 5 |
| Visa | 5 |

Chaque composante a un résultat et un état KNOWN/UNKNOWN/CONFLICT. Les composantes
inconnues ne reçoivent pas de points et leurs poids ne sont pas redistribués aux
autres. Afficher séparément la couverture des informations ; ne pas transformer
une absence de donnée en affirmation de compétence manquante.

Proposition à approuver pour 5A : une exigence obligatoire explicite non attestée
plafonne le total à 60 ; l'écart de séniorité de plus d'un an applique aussi le
plafond prévu par SPEC. Conserver le score avant/après plafonds et leur raison.
Les autres plafonds doivent être explicitement versionnés et justifiés, jamais
inventés à partir de labels absents. Ces choix restent expérimentaux jusqu'en 5B.

Tous les résultats 5A portent provisional=true / calibration_status=UNVALIDATED,
confiance globale faible et mention « Score expérimental ». Une valeur numérique
élevée ne doit pas devenir une alerte ou une promesse de pertinence. L'explication
est assemblée depuis les sous-scores/preuves ; aucune génération libre ne change
le nombre. Modèle none, versions d'extraction/taxonomie/scoring conservées.

## Confidentialité — changement technique soumis à accord

Les snapshots candidat, lacunes et explications peuvent contenir des faits privés :
les stocker chiffrés, pas dans SearchResult.payload ou un log/SSE public de progression.
Le SSE porte identifiants, état et compteurs ; les détails authentifiés passent par
l'API matching après contrôle de propriété.

PrivateCvData est aujourd'hui dans cv, qui n'est pas une dépendance autorisée de
matching. Proposition : extraire sa primitive AES-GCM/HKDF vers core/private_payload.py,
sans nouvelle dépendance, conserver PrivateCvData comme façade compatible. Préserver
strictement les contextes, clés dérivées, format et erreurs historiques CV. matching
et ai utilisent des namespaces/contextes distincts liés au propriétaire et à l'objet.
Tests de rétrocompatibilité chiffrée obligatoires ; aucun rechiffrement ou migration
des données CV existantes. Alternative duplication du chiffrement : écartée.

La suppression du CV doit supprimer les dérivés sensibles par relations déclarées
et empêcher un commit tardif. Revalider publiquement l'existence/état attendu avant
chaque batch. Une modification d'un autre profil ne remplace pas silencieusement
la révision figée ; un recalcul est une nouvelle exécution.
Un changement du candidat actif attendu arrête les nouveaux batches avec
PROFILE_CHANGED ; les résultats déjà commis gardent leur ancienne révision affichée.

## Persistance proposée — quatre tables nouvelles, deux migrations

| Propriétaire / table | Contenu et invariants |
| --- | --- |
| ai / job_analyses | owner, listing_id opaque, hash de tous les champs analysés, versions/taxonomie figées, analyse bornée chiffrée ; unicité owner/hash/configuration |
| matching / scoring_policies | owner, version immuable, poids et plafonds validés, statut de calibration ; pas de donnée personnelle |
| matching / matching_runs | owner, execution_id unique/FK, source_execution_id optionnel, CV/candidat/révision attendus, politique/taxonomie figées, snapshot privé chiffré, curseur MATCH, compteurs et état |
| matching / job_matches | run_id + group_id uniques, listing_id retenu, référence d'analyse, score 0–100, confiance/provisional, détails privés chiffrés et clé de cache versionnée |

Deux migrations append-only, ai puis matching, après le head 0011 actuel ; numéros
revérifiés avant code. Aucune colonne/contrainte/index historique modifié. Les
relations de suppression des dérivés CV doivent être testées sur PostgreSQL réel.
Le cache est propriétaire-scopé : CV/révision/hash de faits pertinents, snapshot
d'offre complet, taxonomie, politique, extracteur/provider et versions. Le
fingerprint de déduplication seul est insuffisant. Ne pas exposer un hash de faits
CV dans les réponses publiques ; dérivation de cache privée si nécessaire.
Un hit de cache privé est déchiffré puis rechiffré dans le contexte du nouveau match,
jamais copié aveuglément avec l'AAD lié à l'ancien objet.

## Queue, API et Angular

- Même queue : en mode aperçu, dernier FILTER → MATCH, puis terminalisation.
  Ancien MANUAL sans aperçu inchangé. Nouveau scope additif MATCHING_ONLY pour
  un recalcul à partir de résultats terminés, sans collecte ni nouveau scan.
- Figer les entrées au démarrage. Calcul pur/extraction locale hors transaction,
  puis fence, revalidation CV, écritures des matches/cache et curseur atomiques.
  Batches bornés, contraintes d'unicité et reprise sans double score/comptage.
- Annulation conserve les scores déjà commis ; pas de recalcul après perte de bail.
  Conserver les raisons PARTIAL de collecte/filtrage. Même échéance globale ; un
  matching expiré/partiel ne transforme pas une collecte partielle en succès complet.
- POST /api/search/executions : matching_preview=false par défaut, politique
  optionnelle et source_execution_id seulement pour MATCHING_ONLY. Refus explicite
  des combinaisons incohérentes et des modes calibrés encore indisponibles.
- API matching authentifiée : lire les aperçus d'un run et ses détails ; pas d'URL
  arbitraire à analyser, coordonnées privées dans les erreurs ou accès intercompte.
- Recherche/Résultats Velson : bouton d'aperçu, candidat/révision affichés, étapes
  SSE existantes, sous-scores, preuves, champs inconnus, plafonds et mention provisoire.
  Affichage dans un composant de détail partagé ; pas de deuxième tableau de résultats.
- Le min_score, bouton de recherche CV complet et alertes restent désactivés en 5A
  avec raison visible. FR/EN, mobile, clavier, reload et conservation des anciens runs.

## Fichiers et vérifications après accord

Créer matching/{api,schemas,models,service,scoring,calibration,__init__,tests},
ai/job_analysis.py et contrats/tests ; core/private_payload.py et façade cv compatible.
Étendre profile/service.py, ses DTO/exports et tests ; search/{executions,queue,
execution_schemas,api} et tests ; composition main/worker/Alembic si nécessaire.
Angular : core/search-api, matching-api/traductions, pages/search/results et détail
partagé/tests, sans modifier le template commercial. Mettre les plans/rapports/suivi
à jour, SPEC immuable. Aucun framework, service, SDK ou deuxième worker ajouté.

Vérifications prévues, pas encore exécutées : mathématique des poids/plafonds,
inconnus, titre trompeur, keyword stuffing, FR/EN, obligatoire vs souhaitable,
négation, remote restreint et visa non attesté ; cache invalidé par chaque donnée
pertinente ; chiffrement ancien/nouveau, suppression CV et accès croisés.
PostgreSQL dédié : migrations aller-retour, concurrence, crash aux commits,
reprise/annulation/recalcul sans collecte ni doublon et snapshots immuables.
API/Angular : refus sans candidat validé, détail provisoire, aucun seuil actif,
SSE/reload/erreurs et responsive. Ruff/format/mypy/pytest, Alembic, typage/build,
Karma/Playwright et CI Linux + Windows ; aucune requête LLM ou payante.

## Phase 5B — conditions réelles de calibration

Préparer le format/loader et les métriques, puis obtenir du propriétaire au moins
50 offres réelles anonymisées annotées STRONG/GOOD/WEAK/NO et les dix CV anonymisés
avec extraction attendue prévus par SPEC. Données privées chiffrées/base locale ou
local-data ignoré ; seuls format et fixtures explicitement synthétiques vont dans
le dépôt public. Aucun label réel, nombre d'exemples ou résultat de calibration inventé.

Mesurer Spearman, précision top 10, NO au-dessus du seuil et STRONG sous 60. Cibles
initiales SPEC : Spearman >=0,6 et aucun NO au-dessus de 70 ; les seuils de régression
supplémentaires doivent être convenus avec le propriétaire. Un test mathématique
synthétique ne remplace pas cette validation. Sans corpus/accord, garder UNVALIDATED
et ne pas activer seuils, alertes ou prétendre à une qualité mesurée.

## Point d'arrêt

Accord attendu : validations de livraison CV phase 4 et Scraping lot 5, puis périmètre
5A, primitive de chiffrement commune compatible, tables/migrations et API additives.
Les autres lots AI Job Agent/Scraping, calibration réelle, providers externes et
Apify ne sont pas approuvés par cet accord. Rapport puis nouvel arrêt après 5A.
