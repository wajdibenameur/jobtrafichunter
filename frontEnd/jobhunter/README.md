# JobHunter frontend

Angular 22 standalone, TypeScript strict, RxJS, tests Karma/Jasmine et Playwright.
Les ?crans actuels sont la connexion propri?taire, le tableau de bord initial et
le compte connect? ? FastAPI. Les recherches/offres/CV des phases suivantes sont
indiqu?s comme bient?t disponibles, sans statistiques ni r?sultats de d?monstration.

## Lancement local (PowerShell, depuis la racine du d?p?t)

Utiliser Node 22.22.3 ou une version compatible avec `package.json`. Le helper
s?lectionne le Node portable du projet lorsqu'il existe, sans modifier Node global.

```powershell
.\scripts\frontend.ps1 install
.\scripts\frontend.ps1 start
```

L'interface est sur **https://localhost:4200**. Le certificat est celui cr?? depuis
`backend` par `.venv/Scripts/python.exe -m app.setup tls`. Il est autosign? et doit
?tre accept? pour le d?veloppement local. L'API doit fonctionner sur
`https://localhost:8443`, avec `https://localhost:4200` dans `ALLOWED_ORIGINS` de
`backend/.env`. Voir le README racine pour la configuration du propri?taire.

Le proxy de d?veloppement utilise exclusivement une cible HTTPS locale. Les
cookies restent Secure/httpOnly/SameSite=Strict ; aucun jeton n'est stock? dans
localStorage. Seul le choix de langue FR/EN y est conserv?.

## R?f?rence Velson et droits

Le dossier `../velson_template` reste intact et ind?pendant. Le script
`prepare-template.mjs` copie seulement `signin.png` dans un dossier local ignor?
par Git. Aucun bundle vendor ni page de d?mo n'est repris. Le th?me est ?crit en
SCSS ? partir des tokens, dimensions et composants du rapport Velson valid?.
Poppins est servi localement sous la licence OFL incluse dans `public/assets/fonts`.

Sans r?f?rence priv?e, d?finir `JOBHUNTER_TEMPLATE_OPTIONAL=1` autorise le build :
une illustration CSS de remplacement appara?t, et aucun asset commercial n'est
n?cessaire. C'est le mode CI. Ne pas redistribuer l'illustration commerciale ni
le template complet sans disposer des droits correspondants.

## V?rifications

Depuis la racine :

```powershell
.\scripts\frontend.ps1 typecheck
.\scripts\frontend.ps1 build
$env:CHROME_BIN = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
.\scripts\frontend.ps1 test
.\scripts\frontend.ps1 audit
```

Le build de production d?sactive le m?canisme CSS critique ? gestionnaire inline,
pour fonctionner avec la CSP du preview sans autoriser de script inline.

Pour les cinq parcours de bout en bout, apr?s un build r?cent et configuration de
`backend/.env.test` (base d?di?e finissant par `_test`) :

```powershell
cd backend
.venv\Scripts\python.exe scripts/frontend_e2e.py
```

Le helper applique les migrations dans un sch?ma al?atoire, cr?e un propri?taire
jetable, lance FastAPI en HTTPS puis le preview du build, et ex?cute Chrome sans
interface. Il nettoie son sch?ma et ses identifiants ? la fin. Les captures et logs
sont dans `.cache/frontend-e2e`, hors Git. Le serveur PostgreSQL existant est conserv?.
`TEST_DATABASE_URL` peut fournir la connexion en CI ; aucune URL DB n'est ?crite
dans les artefacts navigateur.

Pour examiner manuellement le build : `.\scripts\frontend.ps1 preview` depuis
la racine, apr?s configuration TLS/API. Ce preview local n'est pas un d?ploiement
production. Arr?ter le serveur avec Ctrl+C.
