# Sources manuelles — périmètre approuvé

Revue : 2026-11-07. Instruction propriétaire : LinkedIn et Indeed en liens/import
manuel, avec sites tunisiens. D-015 remplace les connecteurs automatiques proposés.

Les quatre sources initiales sont LINK_ONLY. Aucun droit de collecte automatique
n'est déclaré, aucun connecteur HTTP n'est installé et le serveur ne visite pas les
offres collées. Les champs d'une offre proviennent uniquement de l'utilisateur.
Les indicateurs de santé indiquent MANUAL_ONLY ; compteurs de collecte et dernière
synchronisation sont inconnus, jamais simulés à zéro ou en succès.

## Liens fournis

- LinkedIn : page de recherche jobs, critères keywords/location encodés.
- Indeed : page jobs, critères q/l encodés.
- [Keejob](https://www.keejob.com/) : formulaire GET `/offres-emploi/`, champ
  keywords ; lieu incorporé aux mots-clés, sans prétendre à un filtre géographique.
- [Tanitjobs](https://www.tanitjobs.com/) : formulaire jobs avec keywords[all_words]
  et GooglePlace[location][value]. Le lieu reste un texte saisi ; aucune géolocalisation
  n'est inventée ou transmise automatiquement à un tiers depuis le backend.

Les formulaires officiels Keejob/Tanitjobs ont été lus pour leurs noms de champs,
sans ingestion des offres affichées. La génération d'une URL ne constitue pas un
test de pertinence du moteur externe ni une autorisation de scraping.

## Choix conservés

Les recherches sont ouvertes dans le navigateur à l'initiative du propriétaire.
L'import demande son URL, les champs connus et le texte ; les informations absentes
restent vides. Une source personnalisée utilise son URL HTTPS publique et reste
en workflow manuel ; les critères ne sont pas annoncés appliqués si le formulaire
du fournisseur est inconnu. Pas de cookie, mot de passe ou session tiers réutilisé.
