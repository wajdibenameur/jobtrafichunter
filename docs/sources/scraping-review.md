# Scraping Engine — revue documentaire des sources

Revue : 2026-11-08, Codex. Statut : DOCUMENTARY_REVIEW / NO_ACTIVATION.
Preuves consultées lors de l'audit, enregistrées avec l'accord documentaire D-028.
Aucune checklist complète validée en base et aucune source déclarée PERMITTED.
Constats de projet, pas un avis juridique ni une autorisation fournie par le site.

## LinkedIn

- [Conditions officielles](https://www.linkedin.com/legal/user-agreement), section 8.2 :
  restrictions sur le scraping/copie par logiciels et moyens automatisés.
- [robots.txt](https://www.linkedin.com/robots.txt) : l'en-tête exige une permission
  expresse pour l'accès automatisé ; accès de certains moteurs soumis à conditions.
- Conclusion : aucun scraping LinkedIn à implémenter/activer dans ce projet.
  Garder les liens/import manuel ; alertes e-mail seulement après revue propre
  et consentement boîte mail. Aucun mot de passe ou cookie de session récupéré.

## Indeed

- [Conditions officielles](https://www.indeed.com/legal?co=US&hl=en), règles du site :
  automatisation soumise à permission écrite avec exception conditionnelle de crawl
  selon robots.txt ; autres restrictions concernant les usages liés à l'IA.
- [robots.txt](https://www.indeed.com/robots.txt) consulté : règles selon chemins/agents.
  Des chemins accessibles ne valident pas l'ensemble collecte/stockage/matching.
- Conclusion : garder liens/import manuel ; permission pour l'usage précis non établie.

## Keejob

- [Guide officiel llms.txt](https://www.keejob.com/llms.txt) : annonce liens Markdown,
  recherche HTML et flux RSS /rss/jobs/. Indice technique favorable, pas une licence
  générale de stockage ou réutilisation des annonces.
- [Conditions](https://www.keejob.com/terms-of-use/) : propriété intellectuelle du
  site et droits des auteurs sur les annonces ; portée de la réutilisation à préciser.
- [robots.txt](https://www.keejob.com/robots.txt) : plusieurs chemins interdits,
  dont API, espaces privés et actions de candidature. Respecter les chemins exacts.
- Conclusion : candidat à examiner en priorité via le flux documenté ; préciser
  permissions, attribution, conservation et fréquence avant tout connecteur actif.
  Aucun téléchargement du flux ou test de collecte revendiqué dans cette revue.

## Tanitjobs

- [Conditions officielles](https://www.tanitjobs.com/terms-of-use) : copie personnelle
  non commerciale prévue, limitations de sécurité et de surcharge ; aucune permission
  complète de collecte périodique démontrée par la lecture effectuée.
- https://www.tanitjobs.com/robots.txt inaccessible via l'outil de consultation lors
  de la revue ; absence de résultat ne signifie pas autorisation. Accueil en timeout.
- Conclusion : conserver le manuel ; clarification nécessaire avant automatisation.

## Sites carrières et autres domaines

- [Greenhouse Job Board API](https://docs.greenhouse.io/job-board) : endpoints GET
  documentés sans authentification pour les postes publics ; cibler un board précis.
- [Lever Postings API](https://github.com/lever/postings-api) : postes publiés par
  entreprise, pagination documentée ; ne pas confondre avec un moteur multientreprises.
- Ces API sont des candidats techniques. Vérifier les conditions applicables au
  fournisseur et à chaque entreprise, attribution, stockage, accès et quotas ;
  ne pas attribuer une permission universelle à tous les sites carrières.
- [Schema.org JobPosting](https://schema.org/JobPosting) décrit datePosted en Date
  ou DateTime : préserver cette précision. Les données structurées n'accordent
  aucune permission de téléchargement à elles seules.

## À compléter avant une activation

Source/domaine/chemins exacts, méthode, conditions actuelles, résultat robots,
preuve d'accès et d'usage autorisé, stockage/attribution, quotas, relecteur et dates.
Revue périmée ou interdiction : rester/revenir en UNVERIFIED et désactiver la collecte.
Tester uniquement des fixtures avant approbation ; aucune requête de collecte
réelle sous prétexte de « Tester la source » quand les permissions manquent.
