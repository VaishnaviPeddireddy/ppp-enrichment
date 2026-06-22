# Split PPP dataset into 2000-row chunks in data/input/queue/
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$DatasetPath = "data\input\public_up_to_150k_9_240930.csv"
$RowsPerChunk = 2000

if (-not (Test-Path $DatasetPath)) {
    throw "Dataset not found: $DatasetPath"
}

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt -q

$queue = Join-Path $PSScriptRoot "data\input\queue"
$pppRaw = Join-Path $PSScriptRoot "data\input\ppp-war.csv"
New-Item -ItemType Directory -Path $queue -Force | Out-Null
Get-ChildItem $queue -Filter "ppp-war_part*.csv" -ErrorAction SilentlyContinue | Remove-Item -Force

Copy-Item -Path $DatasetPath -Destination $pppRaw -Force

python -m src.ppp_enrichment.run_split_ppp_csv `
    --path $pppRaw `
    --rows $RowsPerChunk `
    --out-dir $queue

$count = (Get-ChildItem $queue -Filter "ppp-war_part*.csv").Count
Write-Host "Done: $count chunk(s) in data/input/queue/ ($RowsPerChunk rows each max)" -ForegroundColor Green
