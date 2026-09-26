$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$web = Join-Path $root "apps\web"
$npx = (Get-Command npx.cmd -ErrorAction Stop).Source

function Invoke-Checked {
  param(
    [Parameter(Mandatory = $true)][string]$Executable,
    [Parameter(Mandatory = $true)][string[]]$Arguments,
    [Parameter(Mandatory = $true)][string]$WorkingDirectory
  )
  Write-Host "`n> $Executable $($Arguments -join ' ')"
  Push-Location $WorkingDirectory
  try {
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Executable exited with status $LASTEXITCODE" }
  }
  finally { Pop-Location }
}

$oldApiUrl = $env:NEXT_PUBLIC_API_URL
$oldDeploymentLabel = $env:NEXT_PUBLIC_DEPLOYMENT_LABEL
try {
  Invoke-Checked $npx @("wrangler", "d1", "migrations", "apply", "prj-277-media-research", "--remote") $web

  $env:NEXT_PUBLIC_API_URL = "/api"
  $env:NEXT_PUBLIC_DEPLOYMENT_LABEL = "CLOUDFLARE WORKERS"
  Invoke-Checked $npx @("opennextjs-cloudflare", "build") $web
  Invoke-Checked $npx @("wrangler", "deploy") $web
}
finally {
  if ($null -eq $oldApiUrl) { Remove-Item Env:NEXT_PUBLIC_API_URL -ErrorAction SilentlyContinue }
  else { $env:NEXT_PUBLIC_API_URL = $oldApiUrl }
  if ($null -eq $oldDeploymentLabel) { Remove-Item Env:NEXT_PUBLIC_DEPLOYMENT_LABEL -ErrorAction SilentlyContinue }
  else { $env:NEXT_PUBLIC_DEPLOYMENT_LABEL = $oldDeploymentLabel }
}
