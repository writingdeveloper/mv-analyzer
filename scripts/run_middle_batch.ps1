# 중간층(Phase 4 단조성 확인) 배치 러너 — Windows 작업 스케줄러용 (세션 독립 실행)
# 야간 실행 원칙(사용자 사용 시간대 회피) — resume_kpop_batch.ps1과 동일 구조.
# Ollama 기동 보장 후 배치 실행. 로그: work/middle/batch.log
$ErrorActionPreference = "Continue"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot
$env:PYTHONUTF8 = "1"

New-Item -ItemType Directory -Force -Path work/middle | Out-Null

try {
    Invoke-RestMethod "http://127.0.0.1:11434/api/tags" -TimeoutSec 5 | Out-Null
} catch {
    Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep 10
}

python batch.py --sample work/middle/sample.csv --lang ja `
    --table work/middle/features_table.jsonl --pause 20 *>> work/middle/batch.log
