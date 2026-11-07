# Pré-vérification des sources — phase 2

Date : 2026-11-07. Relecteur : Codex. Étude documentaire, sans collecte d'offres.
Tous les candidats restent UNVERIFIED : aucune checklist complète enregistrée
dans une table JobSource, aucun connecteur automatisé activé ou implémenté.

## Remotive — clarification requise

La documentation officielle d'API présente une réutilisation avec attribution,
lien source, retard et fréquence limitée. Les conditions de mars 2026 demandent
une permission écrite pour l'accès automatisé ; robots interdit `/api/*`.
Ces éléments ne permettent pas de confirmer la méthode envisagée sans clarification.
Décision opérationnelle proposée : lien/import uniquement, sans appeler l'API.

- [Documentation API officielle](https://github.com/remotive-com/remote-jobs-api/blob/main/README.md)
- [Conditions actuelles](https://support.remotive.com/en/article/terms-of-service-u4kbkf/)
- [robots.txt consulté](https://remotive.com/robots.txt)

## Arbeitnow — documentation favorable, conservation à clarifier

L'annonce officielle propose une API gratuite sans clé pour des projets et renvoie
à Postman. Les conditions générales limitent la copie et la conservation à une
consultation personnelle transitoire : ne pas présumer que cela couvre la base
persistante de JobHunter. Le robots n'a pas pu être récupéré par l'outil web ; son
contenu est inconnu, pas interprété comme une permission. Quotas encore à confirmer.

- [Présentation officielle et documentation liée](https://www.arbeitnow.com/blog/job-board-api)
- [Conditions générales](https://www.arbeitnow.com/terms)
- Robots tenté : `https://www.arbeitnow.com/robots.txt` et variante sans www ;
  échec d'accès de l'outil, aucun résultat robots enregistré comme positif.

## JobTech JobSearch — candidat open data à vérifier complètement

Le catalogue d'Arbetsförmedlingen décrit JobSearch et sa licence CC0 ; la page
institutionnelle présente les données ouvertes comme accessibles et réutilisables.
Cela en fait un candidat pertinent pour la Suède, déjà dans les destinations SPEC.
Authentification effective, disponibilité, pagination, quotas et robots restent
à vérifier sur la documentation technique avant de développer le connecteur.

- [Catalogue officiel, section JobSearch](https://data.jobtechdev.se/dataservice)
- [Présentation officielle open data](https://data.jobtechdev.se/)
- [Entrée de documentation API](https://jobsearch.api.jobtechdev.se/) : application
  sans contenu textuel lisible dans l'outil ; ne vaut pas test d'un endpoint search.
- Robots de l'hôte API tenté, non récupérable par l'outil web.

## France Travail — accès non présumé

Les CGU institutionnelles font référence à une licence de réutilisation pour les
partenaires. Aucun compte développeur, contrat, clé ou souscription n'a été vérifié
pour le propriétaire. Vérifier l'API Offres d'emploi courante avant tout adaptateur.

- [CGU France Travail](https://www.francetravail.fr/informations/informations-legales-et-conditio/conditions-generales-dutilisatio.html)

Une fiche data.gouv trouvée durant l'étude correspond à une republication
territoriale (Seine-Saint-Denis) : elle n'est pas utilisée comme preuve de permission
de l'API nationale. Les résultats de tiers ne sont pas des preuves d'autorisation.

## Suite

Compléter une preuve par connecteur selon `docs/sources/README.md`. Un échec de
lecture, une documentation ancienne ou un endpoint public ne suffisent pas pour
passer PERMITTED. Aucun contact fournisseur n'a été envoyé au nom du propriétaire.
