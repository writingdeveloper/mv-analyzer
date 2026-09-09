# K-pop 배치 재개 러너 — Windows 작업 스케줄러용 (세션 독립 실행)
# Ollama 기동 보장 후 배치 실행. 로그: work/kpop/batch3.log
$ErrorActionPreference = "Continue"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot
$env:PYTHONUTF8 = "1"

try {
    Invoke-RestMethod "http://127.0.0.1:11434/api/tags" -TimeoutSec 5 | Out-Null
} catch {
    Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep 10
}

python batch.py --sample work/kpop/sample.csv --lang ko `
    --table work/kpop/features_table.jsonl --pause 30 *>> work/kpop/batch3.log
