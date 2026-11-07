# Analyse Velson — préalable au lot frontend

Date : 2026-11-07. Statut : ACCEPTED_FOR_IMPLEMENTATION.
La continuation demandée par le propriétaire a autorisé le lot frontend ; son
implémentation et ses contrôles sont décrits dans `phase-1.md`.
Analyse des fichiers uniquement : aucun lancement, build ou test visuel du template.
Aucun fichier du template modifié. Audit réalisé après le socle backend, suivant
l'instruction du propriétaire de réserver Velson au début du frontend.

## Nature et pages

`frontEnd/velson_template` est une application Angular 18.2, TypeScript 5.5,
RxJS 7.8, organisée en NgModules et nommée `xsupply-front`. Le titre HTML est AMS.
Les styles identifient **Velzon 2.4.0, Themesbrand**, avec Bootstrap 5.2.3 personnalisé.
Ce n'est ni un export Figma ni un simple ensemble de captures. Le dépôt Git imbriqué
et ses modifications préexistantes restent intacts et exclus du dépôt racine.

| Route (navigation avec hash) | Contenu et état observé |
| --- | --- |
| `/auth/signin` | Connexion en carte, formulaire à gauche, illustration à droite ; redirige vers `/users` sans API |
| `/auth/signup` | Inscription avec rôle, entreprise, pays et téléphone ; ancien métier multi-rôle |
| `/dashboard/admin` | Shell commun ; corps limité au placeholder `admin-dashboard works!` et une icône |
| `/users` | Tableau responsive avec trois utilisateurs codés en dur et état vide |
| `/providers` | Entrée de menu sans module/route correspondant dans les routes examinées |
| `/auth/reset-password` | Lien dans la connexion sans écran correspondant dans les routes examinées |

Les modules auth/dashboard/users sont chargés à la demande ; les routes inconnues
redirigent vers la connexion. Aucun écran JobHunter n'est connecté au backend.

## Layout, composants et états

`layout/sidebar` contient le shell complet : topbar, recherche, notifications,
menu utilisateur, menu vertical et router-outlet. Le document configure une topbar
claire et une sidebar sombre large. La topbar fait 70 px ; les règles CSS prévoient
notamment des ruptures autour de 768 et 992 px. L'illustration de connexion est
masquée sur les petits écrans.

Réutilisables : shell, cartes, boutons, badges, alertes, groupes d'icônes/champs,
tableaux responsive, sélecteurs, dropdowns et menus. États présents : validation
de formulaire, succès/erreur, boutons et menus désactivés, tableau vide. Les états
chargement API, session expirée, source indisponible et recherche en cours manquent.
Le nom/rôle utilisateur et les notifications sont des démos.

## Styles, polices et assets

Références : `src/styles.css`, `assets/css/bootstrap.css`, `app.css`, `custom.css`.
Les variantes minifiées et RTL existent. Conserver les tokens `--vz-*` et les
espacements Bootstrap plutôt que créer un autre langage visuel.

| Usage | Valeur observée |
| --- | --- |
| Primaire / sidebar sombre | `#405189` |
| Secondaire | `#3577f1` |
| Succès / information | `#0ab39c` / `#299cdb` |
| Avertissement / danger | `#f7b84b` / `#f06548` |
| Fond / cartes | `#f3f3f9` / `#ffffff` |
| Titres / bordures | `#495057` / `#e9ebec` |
| Texte de base | 0.8125 rem, graisse 400, interligne 1.5 |
| Rayon des cartes de base | 0.25 rem |
| Padding horizontal topbar | 1.5 rem, réduit sur mobile |

La connexion surcharge localement le bleu avec `#0d6efd`, fond `#f8f9fa`, carte
maximum 800 px et arrondi 15 px. Conserver ces particularités dans cet écran.
Polices : Poppins importée de Google Fonts ; hkgrotesk locale, graisses 300–700.
Icônes disponibles : Remix, Material Design Icons, Boxicons, Line Awesome,
Feather et Font Awesome ; charger seulement les familles nécessaires.

Assets : dossiers css, fonts, images, js, json, lang et libs ; logos, avatars,
illustrations de connexion/logistique. Fichiers de langues en/fr/ar/ch/gr/it/ru/sp
présents, sans preuve d'une intégration i18n effective.

L'index charge Bootstrap JS, Simplebar, Waves, Feather, Lordicon, ApexCharts,
jsVectorMap, Swiper, un init ecommerce et app.js. Font Awesome est aussi chargé
depuis un CDN. Le package contient Quill, jsPDF, html2canvas, signature pad,
SockJS/STOMP, Node `net` et une auto-dépendance `xsupply-front: file:`. Ne reprendre
que les éléments utilisés ; convertir les interactions DOM globales en composants.

## Couverture des dix écrans SPEC §11

| Écran requis | Couverture | Proposition dans le même style |
| --- | --- | --- |
| Connexion / compte | Structure présente ; aucun auth réel | Brancher cookies et erreurs API, supprimer l'inscription multi-rôle |
| Dashboard | Shell et placeholder uniquement | Cartes découvertes, matches, dernière exécution et santé sources |
| Configuration recherche | Absent | Sections/cartes, multi-sélections et panneau de progression |
| Profils de recherche | Absent | Cartes avec édition, duplication et suppression |
| Gestion CV | Absent | Versions, aperçu privé, éditeur, validation et activation |
| Résultats | Absent ; tableau générique réutilisable | Table/cartes d'offres et drawer d'explication |
| Candidatures | Absent | Tableau ou colonnes par statut, avec notes |
| Historique et logs | Absent | Table d'exécutions et détail par source |
| Préférences notifications | Dropdown de démo seulement | Telegram, test, seuils et heures calmes |
| Sources et santé | Absent | Cartes avec intégration, permission, erreurs et synchronisation |

## Risques et suite proposée

- Préserver le design Velzon tout en remplaçant le métier utilisateurs/logistique.
- Le template Angular 18 doit être adapté aux standalone et à une version stable
  officiellement supportée, à vérifier avant le choix de version.
- `environment.ts` référence un ancien endpoint HTTP ; utiliser FastAPI `/api`
  sur HTTPS et des cookies, sans token dans localStorage.
- `angular.json` référence `environment.prod.ts`, absent du dossier examiné :
  risque de build identifié par lecture, sans prétendre avoir exécuté ce build.
- Ajouter labels accessibles, navigation clavier, focus et annonces de chargement.
  La comparaison visuelle et les contrôles responsive restent à réaliser.
- Aucune licence commerciale générale trouvée à la racine. Les licences de libs
  ne prouvent pas le droit de redistribution du template. Garder ses assets
  commerciaux hors d'un dépôt public jusqu'à clarification et préserver les notices.

Premier lot proposé : application distincte `frontEnd/jobhunter`, référence intacte,
reprise limitée du shell/styles utiles/connexion, client API typé, guards, session,
FR/EN et tests. Les écrans métier seront livrés avec leurs API respectives.
Les assets commerciaux non autorisés à la redistribution devront rester hors du
suivi public ; définir ce mode d'assemblage avant de les intégrer à la CI frontend.

Validation de ce rapport requise avant modification/intégration du design selon
SPEC §3. Aucune fonctionnalité frontend n'est déclarée implémentée ou testée.
