param(
    [ValidateSet('install', 'start', 'build', 'preview', 'test', 'typecheck', 'e2e', 'audit')]
    [string]$Command = 'start'
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$portableNode = Join-Path $projectRoot '.tools\node-v22.22.3-win-x64'
if (Test-Path (Join-Path $portableNode 'node.exe')) {
    $env:PATH = $portableNode + ';' + $env:PATH
}
$env:npm_config_cache = Join-Path $projectRoot '.cache\npm'
$env:npm_config_offline = 'false'
$env:NG_CLI_ANALYTICS = 'false'
Push-Location (Join-Path $projectRoot 'frontEnd\jobhunter')
try {
    if ($Command -eq 'install') { & npm.cmd ci }
    elseif ($Command -eq 'audit') { & npm.cmd audit --omit=dev }
    else { & npm.cmd run $Command }
    exit $LASTEXITCODE
} finally { Pop-Location }
