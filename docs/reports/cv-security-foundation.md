# Phase 4 — Fondations du coffre et de l’isolation Windows

2026-11-08. Lot technique en cours de phase 4 approuvée (D-024).
Ce rapport ne constitue pas la livraison complète de la phase.
Suite du lot initial : voir [phase-4.md](phase-4.md) pour les API, profils et UI
livrés ensuite, et les derniers résultats de validation.

## Coffre des originaux

`backend/app/modules/cv/vault.py` conserve des octets opaques, sans les déclarer
validés comme documents. Aucun endpoint n’accepte encore de CV. Les contrôles de
format et l’ingestion métier seront raccordés après l’extraction isolée.

AES-256-GCM avec la clé existante, HKDF-SHA256 et sel aléatoire de 32 octets pour
séparer chaque clé de fichier ; nonce aléatoire de 12 octets. Propriétaire,
document et version sont liés à l’authentification. Nom original et contenu sont
dans l’enveloppe chiffrée ; chemins uniquement UUID. Aucune copie en clair sur
disque. Taille originale bornée à 5 MiB, lecture d’enveloppe bornée.

Publication atomique par hard link sans remplacement après écriture/fsync ;
versions existantes immuables même sous quatre écritures concurrentes. Refus des
symlinks/junctions dans les chemins. Ces vérifications ne protègent pas contre
un administrateur ou propriétaire système hostile, capable de remplacer le code
ou lire la clé du processus. Les permissions du dossier privé restent nécessaires.

Le coffre ne remplace pas les futures transactions métier : intentions persistées
avant écriture, audit, suppression et récupération des orphelins restent à relier
à PostgreSQL. Ne pas exposer cette primitive directement à une route d’upload.

## Isolation réellement sondée

Le lanceur `ai/sandbox/Runner.cs` utilise AppContainer sans capacité réseau,
une liste explicite de handles stdin/stdout/stderr et un Job Object. Création
suspendue, affectation au job et vérification du token AppContainer avant reprise.
Un seul processus, mémoire 256 MiB, temps CPU 10 s et attente 15 s ; kill-on-close.
Le parent Python borne la sortie à 256 KiB et la durée murale à 20 s, avec arrêt
du job et drainage des pipes même en cas de sortie excessive ou de timeout.

`backend/scripts/setup_cv_sandbox.py` prépare une copie de Python 3.11 et de sa
bibliothèque standard dans `.cache/cv-sandbox`, sans site-packages ni paramètres
applicatifs. Compilation avec le compilateur .NET Windows existant. Création
d’un profil AppContainer lié à cette installation et ACL lecture/exécution
uniquement pour son SID sur la copie du runtime, pas sur le projet ou Python
original. Le profil Windows est local au compte, hors du dépôt. Pas de service
ni règle pare-feu globale, pas de Docker. Les binaires restent ignorés.

L’environnement du parseur contient uniquement les chemins Windows requis
(SYSTEMROOT, USERPROFILE, LOCALAPPDATA, TEMP, TMP, PATH), aucun secret applicatif.
Python démarre avec `-I -S` et un `_pth` dédié. Aucun chemin de document utilisateur
sur la ligne de commande ; communication par pipes. Les sondes n’utilisent que
des canaris synthétiques, pas de `.env` ni de CV personnel.

Premiers essais : compilation sans TEMP refusée ; corrigée avec un répertoire de
build local. Lancement sans variables de profil Windows refusé (code OS 203) ;
liste minimale de chemins ajoutée. Le test de sortie excessive a révélé une
attente de fin de pipe Proactor ; drainage borné après arrêt ajouté et retesté.
Les premières tentatives échouées ne sont pas présentées comme des succès.

## Vérification du lot

- 14 tests coffre : intégrité, changement de clé, échange de fichiers/identités,
  concurrence, taille, Unicode, chemins, nettoyage d’échec et suppression répétée.
- 3 tests isolation : vrai AppContainer avec fichier privé/réseau local/écriture/
  enfant refusés, limites mémoire/sortie/temps, échec fermé sans runtime ou pour
  un script hors liste. **17 passed in 3.63s** pour les nouveaux tests ciblés.
- Ruff et format réussis, mypy réussi sur 78 fichiers. Suite backend complète
  contrôlée séparément ; voir PROGRESS.md pour son dernier résultat réel.
- Tests Windows natifs nécessitant le runtime préparé ; deux tests AppContainer
  sont spécifiques Windows et ne constituent pas une validation Linux.

Depuis `backend`, une seule préparation locale puis les contrôles :

```cmd
.venv\Scripts\python.exe scripts\setup_cv_sandbox.py
.venv\Scripts\python.exe -m pytest app/modules/ai/tests app/modules/cv/tests -q
```

Le bac à sable de l’agent peut refuser les créations de profil/processus Windows ;
les sondes natives ont été exécutées hors de ce bac à sable après autorisation
automatique. Cela ne donne aucun privilège administrateur au parseur isolé.

## Suite du plan autorisé

Raccorder inspection PDF/DOCX et preuves dans ce runtime, puis tables/intentions
et API CV, profil candidat versionné/validé et interface Angular. DOC/OCR restent
des capacités à établir ; ne pas annoncer leur disponibilité. Matching en phase 5,
Apify reporté. Les contrôles ci-dessus ne prouvent ni extraction correcte de CV,
ni résistance absolue à une faille Windows, ni qualité calibrée des profils.

Références officielles consultées : [cryptography AESGCM](https://cryptography.io/en/latest/hazmat/primitives/aead/),
[AppContainer](https://learn.microsoft.com/en-us/windows/win32/secauthz/implementing-an-appcontainer).
