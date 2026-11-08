# Scraping Engine — lot 4 : interface Angular et filtres partagés

Date : 2026-11-08. Statut : DELIVERED / WAITING_FOR_OWNER_VALIDATION.
Continuation propriétaire « contenue » : lot 3 générique validé, lot 4 autorisé
(D-031). [Plan](../PLAN-SCRAPING-ENGINE.md). Aucun connecteur ni collecte réelle activé.

## Page Scraping

- Route protégée /scraping, navigation/shell Velson existants, FR/EN et responsive.
  Template commercial et changements utilisateur conservés.
- Sources, profils et 50 dernières exécutions lus par SourceApi/SearchApi existants.
  Sélection du profil restaurée par paramètre d'URL ; critères sauvegardés par le
  PUT de profil existant, avec confirmation serveur, états de chargement/erreur,
  validation du formulaire et confirmation avant abandon d'un brouillon lors
  du changement de profil ou d'une actualisation. Pas de stockage local de critères.
- CriteriaEditor réutilisé, sans formulaire métier concurrent : sources choisies,
  mots-clés, lieux, expérience, visa, nouveautés et informations manquantes.
  La sélection d'une source dans un profil n'active jamais sa collecte.
- Statuts manuels et données réelles ; compteurs/dernière collecte inconnus affichés
  Non mesuré, pas 0 ou fausse synchronisation. Erreurs de chargement/sauvegarde visibles.
- Lancer/Arrêter/Tester la source indisponibles avec explication : pas d'endpoint
  ou d'adaptateur de collecte opérationnel. Volume 10 et fréquence 30 minutes
  affichés désactivés, explicitement non enregistrables à ce stade.
- Historique filtré par profil et scope IMPORTED_OFFERS, clairement nommé local.
  Liens vers Recherche pour suivi SSE/annulation et vers Résultats existants.
  Aucun nouveau service de progression, faux run ou historique de collecte inventé.

## Filtres fonctionnels, communs aux deux plans

SearchCriteria reçoit publication_minutes optionnel (120/360/1440), exclusif avec
publication_days non nul. Défaut backend historique null et anciens JSONB conservés.
Aucune migration, aucune modification de table ou de snapshot d'exécution existant.
filter_fact est étendu ; pas de seconde implémentation du filtrage.

- Radios 2 h/6 h/24 h/7 j/30 j dans l'éditeur partagé de Profils et Scraping,
  fieldset/legend, sélection unique et navigation clavier native.
- Nouveau profil créé dans Angular : défaut 24 h. Profil enregistré : préférence
  antérieure restaurée ; pas de conversion silencieuse d'un ancien filtre 24 h.
- 2/6/24 h : cutoff strictement exclu, instant courant inclus, futur et publication
  inconnue exclus, même si unknown_policy=include pour les autres champs.
- 7/30 j : publication_days, fenêtre glissante/cutoff inclus et politique des
  inconnus historiques préservés. Calcul des durées sur dates avec fuseau, pas
  sur première découverte. Tests Paris/Tunis et transitions été/hiver.
- Choix Dates avancées : toutes dates, 3 j et ancien 24 h restent disponibles
  avec leurs règles d'origine et un texte explicite.
- Publication inconnue dans Résultats : Date non vérifiée, sans attribuer à une
  date importée connue une vérification indépendante auprès d'un fournisseur.

Le lot 2 du plan AI Job Agent est ainsi réalisé dans le périmètre commun ;
matching, alertes et documents de ce plan restent proposés et non implémentés.
La page Recherche conserve son parcours par profil ; les radios se règlent dans
les éditeurs de profil partagés, pas dans une seconde recherche ad hoc.

## Vérification

| Contrôle | Résultat réel |
| --- | --- |
| pytest complet avec .env.test | 248 passed in 155.31s, aucun skip |
| Nouveaux tests backend de fenêtres | 29 passed in 0.58s |
| Ruff check / format --check | Réussis, 123 fichiers conformes |
| mypy app | Réussi, 104 fichiers |
| alembic check | No new upgrade operations detected |
| Typage app/spec/E2E et build production | Réussis, budget respecté |
| Karma/Jasmine ChromeHeadless | 33 SUCCESS, dont 9 nouveaux tests |
| Playwright API HTTPS/worker réel | 11 passed (31.2s), dont un nouveau parcours |

Pas de nouvelle dépendance, aucun audit de dépendances supplémentaire requis pour ce lot.

Le nouveau parcours utilise API HTTPS, PostgreSQL dédié et worker réel, avec
annonces/profil/source personnalisée synthétiques : préférence historique,
radios/clavier, PUT réel/reload, recherche locale strictement filtrée, liens vers
historique/résultats, mobile/FR-EN et absence de collecte. Fixtures/schéma/identifiants
sont jetables ; les captures restent dans .cache/frontend-e2e/screenshots.

Échecs rencontrés : association/ciblage du sélecteur après chargement asynchrone,
pollution des assertions d'import d'un autre scénario par de nouvelles fixtures,
libellés de navigation mobile et assertion Playwright inadaptés. Sélecteur réactif
et label explicite, scénario ajouté après les assertions historiques et diagnostics
de nettoyage corrigés. Radios initialement trop contraintes par le style des champs
texte : règle partagée corrigée, trois captures desktop/mobile inspectées en fin de run.
Les 10 parcours historiques restent verts ; aucune assertion de conservation
des imports n'est supprimée pour masquer les données ajoutées.

## Lancement et limites

Redémarrer le backend HTTPS pour charger le nouveau champ de critères, puis le
frontend selon le README racine. Ouvrir https://localhost:4200/scraping avec la
session propriétaire. Aucun alembic upgrade supplémentaire nécessaire pour ce lot.
Le worker existant reste nécessaire pour les recherches locales depuis Recherche.

La page prépare et enregistre les profils, elle ne collecte pas encore de sites.
Le volume/fréquence attendent l'intégration correspondante. Quotas durables,
checkpoints par source et persistance des métadonnées JSON-LD restent au lot 5,
ordonnanceur/notifications au lot 6. Aucun score ou consentement fabriqué.
L'historique est borné aux 50 dernières exécutions ; actualisation manuelle sur
Scraping, progression active dans la page Recherche réutilisée.

Après validation : proposer le détail des interfaces et migrations additives du
lot 5 avant code. Permissions de source à établir séparément ; aucune activation
automatique possible sur la seule base d'un accord au plan. CV phase 4 et autres
lots AI Job Agent ne sont pas validés implicitement.
