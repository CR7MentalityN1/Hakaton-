param([switch]$SkipBuild)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
if ($dockerCommand) {
    $dockerExe = $dockerCommand.Source
} elseif (Test-Path -LiteralPath 'C:\Program Files\Docker\Docker\resources\bin\docker.exe') {
    $dockerExe = 'C:\Program Files\Docker\Docker\resources\bin\docker.exe'
} elseif (Test-Path -LiteralPath "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin\docker.exe") {
    $dockerExe = "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin\docker.exe"
} else {
    throw 'Docker CLI is not installed. Install Docker Desktop with WSL2, then run this script again.'
}
& $dockerExe info --format '{{.OSType}}'
if ($LASTEXITCODE -ne 0) { throw 'Docker Engine is not running. Start Docker Desktop and wait until it is ready.' }
& $dockerExe compose config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Compose configuration failed validation.' }
$arguments = @('compose', 'up', '-d', '--wait', '--wait-timeout', '300')
if (-not $SkipBuild) { $arguments += '--build' }
& $dockerExe @arguments
if ($LASTEXITCODE -ne 0) {
    & $dockerExe compose logs --tail 100 backend keycloak postgres redis frontend
    throw 'Compose startup failed. Inspect the service logs above.'
}
& $dockerExe compose ps
@'
import urllib.request
import json
health = json.load(urllib.request.urlopen("http://localhost:8000/health"))
print(health)
assert health["database"] == "ok" and health["redis"] == "ok"
'@ | & $dockerExe compose exec -T backend python -
if ($LASTEXITCODE -ne 0) { throw 'Database or real Redis health check failed.' }
& $dockerExe compose exec -T redis redis-cli ping
if ($LASTEXITCODE -ne 0) { throw 'Redis PING failed.' }
& $dockerExe compose exec -T backend alembic current
if ($LASTEXITCODE -ne 0) { throw 'Migration check failed.' }
@'
import json
import os
import urllib.request

issuer = os.environ["KEYCLOAK_ISSUER"]
realm = issuer.rsplit("/", 1)[-1]
discovery = json.load(urllib.request.urlopen(
    f"http://keycloak:8080/realms/{realm}/.well-known/openid-configuration"
))
assert discovery["issuer"] == issuer, "Keycloak issuer does not match backend configuration"
keys = json.load(urllib.request.urlopen(os.environ["KEYCLOAK_JWKS_URL"]))
assert keys["keys"], "Keycloak signing keys are missing"
assert urllib.request.urlopen("http://frontend/").status == 200
proxied = json.load(urllib.request.urlopen("http://frontend/api/v1/auth/config"))
assert proxied["realm"] == realm, "Frontend API proxy points at a different realm"
print("Keycloak discovery, signing keys and frontend API proxy: OK")
'@ | & $dockerExe compose exec -T backend python -
if ($LASTEXITCODE -ne 0) { throw 'Cross-service Keycloak or frontend proxy check failed.' }
Write-Host 'Compose verification passed. Default CRM address: http://localhost:3000'
Write-Host 'Port overrides are controlled by .env. Next: node scripts/browser-smoke.mjs'
