# Uses the already prepared portable runtimes. Does not install software or change Windows.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$runtimeRoot = Join-Path $projectRoot '.runtime'
$logRoot = Join-Path $runtimeRoot 'logs'
New-Item -ItemType Directory -Path $logRoot -Force | Out-Null

function Test-Port([int]$Port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try { $client.Connect('127.0.0.1', $Port); return $true }
    catch { return $false }
    finally { $client.Dispose() }
}
function Wait-Http([string]$Url, [int]$Seconds = 120) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    do {
        try { return Invoke-RestMethod -Uri $Url -TimeoutSec 3 }
        catch { Start-Sleep -Seconds 2 }
    } while ((Get-Date) -lt $deadline)
    throw "Service did not become ready: $Url. Inspect .runtime/logs."
}

$python = (Get-Command python -ErrorAction Stop).Source
$node = (Get-Command node -ErrorAction Stop).Source
$env:PYTHONPATH = "$projectRoot\.tools;$projectRoot\backend"
$env:MPLCONFIGDIR = "$projectRoot\data\matplotlib"
# This cluster was initialized for this local demonstration only.
$env:DATABASE_URL = 'postgresql+psycopg://crm@127.0.0.1:5432/crm'
$env:KEYCLOAK_ISSUER = 'http://localhost:8080/realms/rostelecom-it-school'
$env:CORS_ORIGINS = 'http://localhost:3000'
$env:DATA_DIR = "$projectRoot\data\v2"

if (-not (Test-Port 5432)) {
    $pgCtl = Join-Path $runtimeRoot 'pgsql\bin\pg_ctl.exe'
    if (-not (Test-Path -LiteralPath $pgCtl)) {
        throw 'Portable PostgreSQL is missing. Follow the native setup in docs/DEPLOYMENT.md.'
    }
    $pgRoot = $runtimeRoot
    $shortPathFile = Join-Path $runtimeRoot 'shortpath.txt'
    if (Test-Path -LiteralPath $shortPathFile) {
        $savedPath = (Get-Content -LiteralPath $shortPathFile -Raw).Trim()
        if (Test-Path -LiteralPath "$savedPath\pgdata") { $pgRoot = $savedPath }
    }
    & $pgCtl -D "$pgRoot\pgdata" -l "$pgRoot\postgres.log" -w start
    if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL startup failed.' }
}
& $python -m alembic -c backend/alembic.ini upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Database connection or migration failed.' }

if (-not (Test-Port 8080)) {
    $javaDir = Get-ChildItem -LiteralPath $runtimeRoot -Directory -Filter 'jdk-21*' | Select-Object -First 1
    $kcDir = Join-Path $runtimeRoot 'keycloak-26.2.5'
    if (-not $javaDir -or -not (Test-Path -LiteralPath "$kcDir\bin\kc.bat")) {
        throw 'Portable Java/Keycloak is missing. Follow docs/DEPLOYMENT.md.'
    }
    $env:JAVA_HOME = $javaDir.FullName
    $env:KC_DB = 'postgres'
    $env:KC_DB_URL = 'jdbc:postgresql://127.0.0.1:5432/crm'
    $env:KC_DB_USERNAME = 'crm'
    $env:KC_DB_PASSWORD = 'crm-local-demo'
    $env:KC_DB_SCHEMA = 'keycloak'
    $env:KC_HEALTH_ENABLED = 'true'
    $kcCommand = '/d /s /c ""' + $kcDir + '\bin\kc.bat" start-dev --import-realm --hostname=http://localhost:8080"'
    Start-Process -FilePath $env:ComSpec -ArgumentList $kcCommand -WindowStyle Hidden -WorkingDirectory $projectRoot -RedirectStandardOutput "$logRoot\keycloak.log" -RedirectStandardError "$logRoot\keycloak-error.log" | Out-Null
}
$discovery = Wait-Http 'http://localhost:8080/realms/rostelecom-it-school/.well-known/openid-configuration'
if ($discovery.issuer -ne $env:KEYCLOAK_ISSUER) { throw 'Unexpected Keycloak issuer on port 8080.' }

if (-not (Test-Port 8000)) {
    Start-Process -FilePath $python -ArgumentList '-m uvicorn app.main:app --host 127.0.0.1 --port 8000' -WindowStyle Hidden -WorkingDirectory $projectRoot -RedirectStandardOutput "$logRoot\backend.log" -RedirectStandardError "$logRoot\backend-error.log" | Out-Null
}
$health = Wait-Http 'http://localhost:8000/health'
if ($health.database -ne 'ok' -or $health.auth -ne 'keycloak') { throw 'Backend health check failed.' }

if (-not (Test-Port 3000)) {
    if (-not (Test-Path -LiteralPath 'frontend/dist/index.html')) {
        & npm.cmd run build
        if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
    }
    $viteScript = Join-Path $projectRoot 'node_modules\vite\bin\vite.js'
    $viteArgs = '"' + $viteScript + '" preview --host 127.0.0.1 --port 3000 --strictPort'
    Start-Process -FilePath $node -ArgumentList $viteArgs -WindowStyle Hidden -WorkingDirectory "$projectRoot\frontend" -RedirectStandardOutput "$logRoot\frontend.log" -RedirectStandardError "$logRoot\frontend-error.log" | Out-Null
}
$authConfig = Wait-Http 'http://localhost:3000/api/v1/auth/config'
if ($authConfig.realm -ne 'rostelecom-it-school') { throw 'Unexpected application on port 3000.' }
Write-Host 'CRM ready: http://localhost:3000'
Write-Host 'Accounts: admin/admin123, manager/manager123, user/user123'
Write-Host ('Redis: ' + $health.redis + '. The application works without cache when Redis is unavailable.')
Write-Host 'This is the native demonstration, not a Docker Compose verification.'
