# Évaluation locale du matching

Cet outil mesure un corpus **fourni et annoté par le propriétaire**. Il ne collecte
aucune offre, ne se connecte ni à PostgreSQL ni à un fournisseur, et ne modifie aucun
score, CV, cache ou barème de l'application. Ses rapports gardent
`calibration_status: UNVALIDATED`, même lorsque les cibles numériques sont atteintes.

## Préparer les fichiers privés

Créer `calibration/private/`, exclu de Git, puis copier `template.json` dans ce dossier.
Le modèle est volontairement vide : il valide le format mais ne constitue aucun jeu
de calibration. `schema.json` décrit le format JSON versionné. Ne jamais ajouter de
CV réel, coordonnées, notes personnelles ou labels propriétaire dans les fichiers
publics de ce dossier. L'exclusion Git ne chiffre pas les fichiers sur disque ;
anonymiser les données et conserver ce dossier dans un emplacement local protégé.

Le corpus contient :

- `schema_version: 1` ; `purpose` parmi `SYNTHETIC`, `TUNING` et `VALIDATION`.
- `owner_reviewed` : booléen explicite, uniquement après relecture effective.
- `snapshots` : dictionnaire de 20 profils au maximum, identifiés par une clé
  pseudonyme (lettres, chiffres, `_` ou `-`, 64 caractères maximum).
- `cases` : jusqu'à 1 000 jugements, chacun ayant un `case_id` unique,
  `candidate_key`, `job`, `label`, `domain` et des `mandatory_gap_notes` facultatives.

Chaque snapshot reprend `MatchingSnapshot` : `candidate`, `taxonomy`, `policy`,
plus `candidate_reviewed: true`. Le candidat conserve ses identifiants UUID de
version, sa `revision`, ses `fields` et ses `preferences`, après anonymisation.
Les champs utiles sont titre professionnel, compétences, années validées, langues,
formation et préférences ; `summary`, `experiences` et `certifications` restent vides.
Les UUID relient des snapshots ; ils ne prouvent pas que le fichier est authentique.

L'offre `job` reprend `MatchJobInput`, notamment `id` et `group_id` UUID, les faits,
la description figée, les exigences déclarées, les années et le visa explicitement
connu. Réutiliser le `group_id` existant pour une même offre ; ne pas créer plusieurs
identifiants pour augmenter artificiellement le volume. Aucune URL n'est ouverte.

Les labels sont `NO`, `WEAK`, `GOOD` ou `STRONG`, choisis par le propriétaire contre
le profil figé. Les notes décrivent les prérequis non attestés (2 000 caractères max).
`domain` est une annotation parmi `JAVA_SPRING_ANGULAR`, `DEVOPS`, `DATA_ENGINEERING`,
`AI`, `BUSINESS_ANALYSIS`, `OTHER`. Cette annotation ne remplace pas les faits de l'offre.
Les références manquantes, doublons de jugement, snapshots contradictoires d'un même
groupe et champs inconnus sont refusés. Taille totale maximale : 20 Mio.

Préparer les snapshots explicitement avec les DTO et le schéma ; cet outil n'exporte
pas automatiquement la base ou le contenu de Mes CV. Aucun jeu réel n'est livré.
Les tests sous `backend/app/modules/matching/tests` sont exclusivement synthétiques.

## Commandes depuis backend

Sous Windows, Python 3.11 :

```cmd
.venv\Scripts\python.exe -m app.modules.matching.calibration_cli --input ..\calibration\private\corpus.json --validate-only
.venv\Scripts\python.exe -m app.modules.matching.calibration_cli --input ..\calibration\private\corpus.json --output ..\calibration\private\rapport.json
.venv\Scripts\python.exe -m app.modules.matching.calibration_cli --input ..\calibration\private\corpus.json --alternative-policy ..\calibration\private\policy.json --check-targets
```

Sur les autres plateformes, remplacer `.venv\Scripts\python.exe` par `python` et
adapter les séparateurs. Aucun `.env` ni secret n'est requis pour ces commandes.
Le fichier alternatif est une `ScoringPolicy`, avec les huit poids totalisant 100 et
un `mandatory_cap` de 0 à 60. Il ne remplace pas une politique enregistrée en base.

La console et le rapport contiennent uniquement des statistiques agrégées, politiques
et versions du moteur. Ils ne contiennent pas de texte de CV/offre, notes, URLs,
identifiants de candidat ou scores individuels. Les erreurs utilisent des codes
stables sans afficher l'entrée brute ou un chemin privé.

Le dossier parent de `--output` doit exister. Publication atomique du fichier complet,
sans écrasement par défaut ; `--overwrite` autorise explicitement le remplacement
d'un rapport. L'entrée et le barème alternatif ne peuvent pas être écrasés.
Les chemins URL/UNC et fichiers non réguliers sont refusés. Un système de fichiers
sans lien physique peut refuser la publication sans écrasement ; aucun rapport
partiel n'est alors publié.

Codes de sortie :

| Code | Sens |
| --- | --- |
| 0 | Format ou évaluation calculée ; ne signifie pas calibration validée |
| 2 | Arguments, fichier, format, écriture ou traitement en erreur |
| 3 | `--check-targets` : volume/prérequis insuffisants ou cibles non atteintes |
| 130 | Interruption demandée |

Avec `--alternative-policy --check-targets`, le contrôle porte sur le barème
alternatif ; sans alternative, il porte sur le barème initial. Toutes les cohortes
présentes doivent satisfaire les conditions ; un corpus vide échoue au contrôle.

## Lire les métriques

Les cohortes sont séparées par snapshot candidat/taxonomie/barème. Les profils
différents ne sont pas mélangés dans une corrélation globale trompeuse.

- Spearman : NO=0, WEAK=1, GOOD=2, STRONG=3, corrélation des rangs moyens.
  Moins de deux cas ou variance nulle donne `null` avec une raison explicite.
- Précision@k : GOOD et STRONG sont pertinents, `k=min(10, nombre de cas)`.
  Les ex æquo à la frontière contribuent fractionnellement, sans tri favorable.
- `no_above_60` et `no_above_70` : compte/taux parmi les NO, strictement au-dessus
  du seuil. `strong_below_60` : compte/taux parmi les STRONG strictement sous 60.
  Une catégorie absente a un taux `null` et un dénominateur zéro.
- `capped_count` compte les scores effectivement réduits par rapport au score brut.
  La comparaison alternative affiche les métriques avant/après, hausses/baisses et
  variation moyenne, sur les mêmes cas, sans réécrire l'historique.

Pour évaluer les cibles initiales, une cohorte doit avoir au moins 50 offres distinctes,
aucune copie exacte de contenu, les cinq domaines cibles et les quatre catégories
de labels, un but `VALIDATION` et la relecture déclarée. Les contenus exactement
répétés sont signalés hors identifiants/URLs ; cela ne remplace pas la déduplication
du catalogue. Les seuils sont Spearman ≥0,6 et zéro NO au-dessus de 70.

Les états `INCOMPLETE`, `TARGETS_NOT_MET` et `TARGETS_MET` décrivent uniquement ces
contrôles numériques. Un fichier auto-déclaré réel ne prouve pas sa provenance.
Un corpus de réglage doit être séparé d'une validation indépendante, selon un
protocole approuvé par le propriétaire. Les dix CV anonymisés avec extraction attendue
constituent une validation distincte ; ils ne sont pas remplacés par 50 paires notées.
La qualité réelle et toute activation de seuils/alertes exigent une revue humaine
séparée. Le statut de production reste expérimental.
