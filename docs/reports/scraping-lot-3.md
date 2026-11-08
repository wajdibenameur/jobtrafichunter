# Scraping Engine — lot 3 : extraction JSON-LD

Date : 2026-11-08. Statut : VALIDATED_GENERIC_EXTRACTION (continuation D-031).
Les propositions de suite ci-dessous décrivent la livraison historique.
Continuation propriétaire « contenue » : lot 2 validé, extraction lot 3 autorisée
(D-030). [Plan](../PLAN-SCRAPING-ENGINE.md), [sources](../sources/scraping-review.md).
La partie adaptateurs fournisseurs reste conditionnée à des permissions établies.
Aucune source automatique enregistrée ou activée, aucune collecte réelle.

## Livraison

- sources/connectors/jsonld.py : extraction hors ligne à partir d'une réponse
  CollectedResponse. Aucune requête, exécution JS, lecture de fichier, résolution
  d'un @context ou téléchargement d'image/lien n'est effectuée par cet extracteur.
- HTML/XHTML et document application/ld+json en UTF-8 ; scripts JSON-LD avec
  listes, @graph, mainEntity, ListItem.item, types simples/multiples et URI Schema.org.
  Définitions @context non traitées comme annonces, scripts externes ignorés avec
  avertissement. Références @id locales non ambiguës résolues sans requête externe.
- Normalisation : titre, entreprise, description en texte, identifiant explicite,
  plusieurs lieux, régions/pays déclarés, emploi/type de contrat, compétences
  mentionnées et exigences d'expérience textuelles. Pas de visa, séniorité ou
  distinction obligatoire/optionnel inventés. TELECOMMUTE devient remote uniquement
  lorsqu'il est explicitement présent ; les restrictions de lieux candidats
  restent distinctes du visa.
- URL réelle/relative résolue sur le document reçu, sans respecter un <base>
  arbitraire. Repli sur URL du document seulement pour un unique JobPosting.
  Pas d'URL inventée sur une liste d'annonces. URL de candidature explicite ou
  ApplyAction réel ; directApply=true seul ne crée aucune destination supplémentaire.
- HTML descriptif débarrassé de scripts/styles/frames/templates/objets/SVG,
  puis converti en texte. L'interface devra toujours rendre ce texte comme texte,
  jamais interpréter sa sortie comme HTML réputé sûr.
- published_at uniquement si le fuseau est explicite, normalisé UTC. Date seule
  stockée en published_date/DATE ; horaire sans fuseau en LOCAL_DATETIME avec
  published_at null. Valeur originale et avertissements conservés, aucun minuit
  ou horaire d'import fabriqué. Cohérence précision/valeur contrôlée par le DTO.
- source_document_url, hash du JSON d'origine et extractor_version permettent
  une traçabilité de l'extraction, sans modifier les imports existants.
- Bilan explicite OK/PARTIAL/EMPTY/FAILED et erreurs à codes fixes. Un script
  invalide ne supprime pas les autres résultats ; une page inutilisable ne
  devient pas un succès vide dans normalize_jsonld_page.
- Préparation de page sous CollectionAuthorization, réutilisant CollectionBudget :
  comptage des objets rencontrés/rejetés, plafond d'offres, avertissements et
  liens rel=next contrôlés par les routes approuvées. Si la page courante est
  tronquée, aucun cursor vers la suivante n'est annoncé pour masquer une perte.

## Bornes

Document 2 Mio, 20 000 balises, 32 scripts, 256 Kio par script/512 Kio de JSON,
10 000 noeuds et profondeur 32. JSON à clés dupliquées, nombres non finis ou
complexité excessive rejeté avec diagnostic fixe. Descriptions : 150 000 caractères
en entrée, 2 000 balises et 50 000 caractères de texte ; champs/listes bornés.
500 résultats maximum avant le plafond plus restrictif du budget et de la requête.
Gros fichiers/encodages non supportés refusés ; aucun parseur universel n'est revendiqué.

## Dépendances et compatibilité

Beautiful Soup 4.15.0 et SoupSieve 4.0.1, licences MIT ; environnement Python
3.11.9 testé. Aucun upgrade des versions de paquets déjà verrouillées. Verrous
runtime/dev hachés, audit runtime exécuté. html.parser standard, pas de lxml,
navigateur runtime, service ni migration. Les métadonnées nouvelles sont des DTO
internes ; leur persistance demandera une proposition additive au lot 5.

Références officielles revues : [Beautiful Soup/PyPI](https://pypi.org/project/beautifulsoup4/),
[documentation](https://www.crummy.com/software/BeautifulSoup/bs4/doc/),
[JobPosting](https://schema.org/JobPosting).
L'[aide LinkedIn](https://www.linkedin.com/help/linkedin/answer/a507441) documente
24 h/semaine/mois mais pas le contrat exact f_TPR/2 h/6 h ; aucun paramètre
non vérifié ajouté au générateur de liens existant, aucun accès aux annonces.

## Vérification

| Contrôle | Résultat réel |
| --- | --- |
| pytest complet avec .env.test, --tb=short | 219 passed in 132.68s, aucun skip |
| Tests ciblés transport/extraction | 88 passed in 3.51s, dont 38 nouveaux JSON-LD |
| Ruff check / format --check | Réussis, 122 fichiers conformes |
| mypy app | Réussi, 103 fichiers |
| alembic check | No new upgrade operations detected |
| pip-audit requirements.lock | No known vulnerabilities found |

Frontend/build/E2E non relancés : aucun frontend, route API, worker ou modèle SQL
modifié par ce lot. Dernières preuves navigateur dans l'audit AI Job Agent ;
elles ne prouvent pas un écran Scraping qui n'existe pas encore.
Fixtures synthétiques uniquement, sans CV personnel, vraie annonce ou label réel.

## Limites et suite

Pas de collecte fournisseur, API de collecte, UI Scraping, matching, notification
ou persistance nouvelle. Le worker n'appelle pas encore cet extracteur. La page
préparée transmet ses avertissements/métadonnées ; le lot 5 devra les persister et
les refléter fidèlement dans les états PARTIAL/erreurs. Aucune fusion floue ajoutée :
la déduplication existante reste le seul mécanisme de rapprochement.

Ce n'est pas un processeur JSON-LD complet : pas de contexte distant, vocabulaire
arbitraire, inférence ou expansion de graphe réseau. Références ambiguës signalées.
Les déclarations de l'annonce ne sont pas vérifiées indépendamment auprès de l'employeur.
Les dates à précision insuffisante ne peuvent alimenter un filtre strict horaire.

La sélection d'un adaptateur Keejob/Tanitjobs/Indeed/API carrières attend toujours
la vérification d'un périmètre source concret. LinkedIn reste sans scraping.
Pas d'activation PERMITTED attribuée au nom des fixtures autorisées des tests.
Phase 4 CV, plan AI Job Agent et lots Scraping suivants ne sont pas validés
implicitement. Après validation de cette livraison, préparer la page du lot 4
en réutilisant les critères et les vues existantes, avec capacités honnêtes.
