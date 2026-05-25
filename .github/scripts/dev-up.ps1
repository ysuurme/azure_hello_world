<#
.SYNOPSIS
  Launch the local backend + frontend containers with the Service Principal client
  secret fetched from the central platform Key Vault (kv-platformy-dev) at runtime.

.DESCRIPTION
  The SP client secret is never stored on disk (.env keeps AZURE_CLIENT_SECRET blank).
  This script uses your `az login` identity (which holds Key Vault Secrets User/Officer
  on the vault) to read the secret, exports it to the process environment so
  docker-compose interpolates ${AZURE_CLIENT_SECRET} into the backend container, then
  starts compose. The running container authenticates to Foundry as the scoped SP
  (workload identity) — it never depends on your az login. See ADR-017.

  Any extra arguments are passed straight through to `docker compose up`
  (e.g. `-d` for detached, `--build` is always applied).
#>
[CmdletBinding()]
param(
    [string]$VaultName  = 'kv-platformy-dev',
    [string]$SecretName = 'helloarch-sp-client-secret',
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ComposeArgs
)

$ErrorActionPreference = 'Stop'

# 1. Confirm an az login session exists (the human bootstrap identity).
$account = az account show --query user.name -o tsv 2>$null
if (-not $account) {
    Write-Error "No az login session. Run 'az login' first — your identity is the bootstrap that reads the vault."
    exit 1
}
Write-Host "az identity: $account" -ForegroundColor DarkGray

# 2. Fetch the SP secret from the central platform Key Vault.
Write-Host "Fetching $SecretName from $VaultName ..." -ForegroundColor Cyan
$secret = az keyvault secret show --vault-name $VaultName --name $SecretName --query value -o tsv 2>$null
if (-not $secret) {
    Write-Error "Could not read $SecretName from $VaultName. Check the vault exists and you have 'Key Vault Secrets User'."
    exit 1
}

# 3. Inject into the process environment only (never written to disk).
$env:AZURE_CLIENT_SECRET = $secret
Write-Host "SP secret injected into environment (len $($secret.Length))." -ForegroundColor Green

try {
    # 4. Start compose; --build keeps the image deterministic, extra args pass through.
    docker compose up --build @ComposeArgs
}
finally {
    # 5. Scrub the secret from the environment when the script exits.
    Remove-Item Env:\AZURE_CLIENT_SECRET -ErrorAction SilentlyContinue
}
