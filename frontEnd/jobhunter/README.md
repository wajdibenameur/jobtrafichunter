# JobHunter frontend

Angular 22 standalone, TypeScript strict, RxJS, tests Karma/Jasmine et Playwright.
Connexion propriétaire, compte et page Sources connectés à FastAPI ; interface FR/EN.
Sources : LinkedIn, Indeed, Keejob et Tanitjobs, filtre tunisien, préférences,
sites personnalisés, liens de recherche et import URL/CSV avec confirmation.
Aucune collecte automatique ; recherche, matching et CV arrivent aux phases suivantes.

## Lancement CMD depuis frontEnd\jobhunter

Après configuration TLS et démarrage HTTPS du backend :

```cmd
set "PATH=%CD%\..\..\.tools\node-v22.22.3-win-x64;%PATH%"
npm start
```

Ouvrir **https://localhost:4200**. Si le certificat manque, depuis backend :
`.venv\Scripts\python.exe -m app.setup tls`. Le certificat autosigné doit être
accepté pour le développement local. L’API doit fonctionner sur https://localhost:8443,
avec https://localhost:4200 dans ALLOWED_ORIGINS de backend/.env.
Voir le README racine pour le compte et les commandes backend.

## PowerShell depuis la racine du dépôt

Utiliser Node 22.22.3 ou une version compatible avec package.json. Le helper
sélectionne le Node portable du projet sans modifier Node global.

```powershell
.\scripts\frontend.ps1 install
.\scripts\frontend.ps1 start
```

Le proxy utilise exclusivement une cible HTTPS locale. Cookies Secure/httpOnly/
SameSite=Strict ; seul le choix de langue est conservé dans localStorage.

## Référence Velson et droits

Le dossier ../velson_template reste intact et indépendant. prepare-template.mjs
copie seulement signin.png dans un dossier local ignoré par Git. Aucun bundle
vendor ni page de démonstration repris. Thème SCSS basé sur le rapport Velson
validé. Poppins servi localement sous OFL, licence fournie dans public/assets/fonts.

Sans référence privée, JOBHUNTER_TEMPLATE_OPTIONAL=1 autorise un build avec
illustration CSS de remplacement, comme en CI. Ne pas redistribuer le template
commercial ou son illustration sans les droits correspondants.

## Vérifications

Depuis la racine :

```powershell
.\scripts\frontend.ps1 typecheck
.\scripts\frontend.ps1 build
$env:CHROME_BIN = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
.\scripts\frontend.ps1 test
.\scripts\frontend.ps1 audit
```

CSS critique sans gestionnaire inline pour respecter la CSP. Après build,
avec backend/.env.test configuré (base dédiée finissant par _test) :

```powershell
cd backend
.venv\Scripts\python.exe scripts/frontend_e2e.py
```

Les sept parcours incluent session/connexion/mobile et sources/import. Le helper
crée un schéma, un compte et une API HTTPS jetables, exécute Chrome puis nettoie
ses données. Captures/logs dans .cache/frontend-e2e hors Git ; le PostgreSQL système
est conservé. TEST_DATABASE_URL peut fournir la connexion en CI, sans artefact DB
transmis au navigateur. Résultats réels dans docs/reports/phase-2.md à la racine.

Pour examiner le build : .\scripts\frontend.ps1 preview depuis la racine avec
TLS/API configurés ; arrêter par Ctrl+C. Ce preview reste local.
