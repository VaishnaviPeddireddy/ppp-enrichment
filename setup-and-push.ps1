# One-time: split dataset, init git, push to VaishnaviPeddireddy/ppp-enrichment
param(
    [string] $DatasetPath = "data\input\public_up_to_150k_9_240930.csv",
    [string] $GitHubUsername = "VaishnaviPeddireddy",
    [string] $RepoName = "ppp-enrichment"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$GhExe = Join-Path ${env:ProgramFiles} "GitHub CLI\gh.exe"
if (-not (Test-Path $GhExe)) { throw "Install GitHub CLI: winget install GitHub.cli" }

Write-Host "=== GitHub login ===" -ForegroundColor Cyan
& $GhExe auth status 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { & $GhExe auth login -h github.com -p https -w }

Write-Host "=== Python deps ===" -ForegroundColor Cyan
if (-not (Test-Path ".venv")) { python -m venv .venv }
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt -q

Write-Host "=== Split dataset into queue chunks ===" -ForegroundColor Cyan
$src = Resolve-Path $DatasetPath
$inputDir = Join-Path $PSScriptRoot "data\input"
$queue = Join-Path $inputDir "queue"
$pppRaw = Join-Path $inputDir "ppp-war.csv"
New-Item -ItemType Directory -Path $queue -Force | Out-Null
Get-ChildItem $queue -Filter "ppp-war_part*.csv" -ErrorAction SilentlyContinue | Remove-Item -Force

# Pipeline reads data/input/queue/ppp-war_part*.csv — split from ppp-war.csv stem
Copy-Item -Path $src -Destination $pppRaw -Force

python -m src.ppp_enrichment.run_split_ppp_csv `
    --path $pppRaw `
    --rows 2000 `
    --out-dir $queue

$count = (Get-ChildItem $queue -Filter "ppp-war_part*.csv").Count
Write-Host "Created $count chunk file(s) in data/input/queue/"

Write-Host "=== Git init & push ===" -ForegroundColor Cyan
if (-not (Test-Path ".git")) { git init -b main }
git add .
git commit -m "Setup: PPP dataset split into queue chunks for scheduled enrichment" -ErrorAction SilentlyContinue

git remote remove origin 2>$null
& $GhExe repo create $RepoName --public --source=. --remote=origin --push `
    --description "PPP enrichment pipeline + chunk inputs"

Write-Host @"

DONE
Repo: https://github.com/$GitHubUsername/$RepoName
Schedule: every 3 hours UTC (.github/workflows/pipeline.yml)

Last step in GitHub UI:
  Settings -> Actions -> General -> Workflow permissions -> Read and write permissions

"@ -ForegroundColor Green
