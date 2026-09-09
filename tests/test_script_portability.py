from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_powershell_helpers_do_not_hardcode_personal_repo_path():
    for name in ["resume_kpop_batch.ps1", "run_middle_batch.ps1"]:
        text = (ROOT / "scripts" / name).read_text(encoding="utf-8")
        assert r"C:\Users\SIHYEONG" not in text
        assert "$PSScriptRoot" in text
        assert "Resolve-Path" in text
