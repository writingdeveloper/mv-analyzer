import json
import socket
from pathlib import Path

from mv_analyzer.cli import main
from mv_analyzer.reference_corpus import load_reference_rows

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads((ROOT / "web/e2e/fixtures/analyze-report.json").read_text(encoding="utf-8"))


def write_source(folder):
    folder.mkdir(parents=True, exist_ok=True)
    row = dict(load_reference_rows(ROOT)[0])
    (folder / "features.json").write_text(json.dumps(row, ensure_ascii=False), encoding="utf-8")
    return row


def test_reason_export_is_offline_atomic_and_does_not_touch_source(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        raise AssertionError("network access during offline reason export")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    source = tmp_path / "mv"
    row = write_source(source)
    before = (source / "features.json").read_bytes()
    out = tmp_path / "reason.json"
    assert main(["reason-export", str(source), "--out", str(out), "--benchmark-domain", "vocaloid"]) == 0
    reason = json.loads(out.read_text(encoding="utf-8"))
    assert reason["kind"] == "mv-analyzer-reason"
    assert reason["video"]["video_id"] == row["video_id"]
    assert (source / "features.json").read_bytes() == before
    assert not (tmp_path / "reason.json.tmp").exists()


def test_reason_export_can_attach_existing_favorite_profile(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        raise AssertionError("network access during offline reason export")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    data = tmp_path / "data"
    target = data / "target00001"
    write_source(target)
    # Four minimal analyzed favorites are enough to enable the taste adapter.
    fav_ids = []
    for i in range(4):
        vid = f"fav{i:08d}"[:11]
        fav_ids.append(vid)
        folder = data / vid
        folder.mkdir(parents=True)
        row = dict(load_reference_rows(ROOT)[i])
        row["video_id"] = vid
        (folder / "features.json").write_text(json.dumps(row, ensure_ascii=False), encoding="utf-8")
    favorites = tmp_path / "favorites.txt"
    favorites.write_text("\n".join(fav_ids), encoding="utf-8")
    out = tmp_path / "reason.json"
    assert main(["reason-export", str(target), "--out", str(out), "--favorites", str(favorites),
                 "--data", str(data)]) == 0
    reason = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(reason["summary"]["taste"], list)


def test_explain_delegates_to_existing_analyzer_and_writes_reason(monkeypatch, tmp_path):
    data = tmp_path / "data"
    vid = FIXTURE["video"]["video_id"]
    folder = data / vid
    folder.mkdir(parents=True)
    # target features must exist after the delegated analyzer finishes.
    row = dict(load_reference_rows(ROOT)[0])
    row["video_id"] = vid
    row["title"] = FIXTURE["video"]["title"]
    row["channel"] = FIXTURE["video"]["channel"]
    (folder / "features.json").write_text(json.dumps(row, ensure_ascii=False), encoding="utf-8")
    seen = {}
    def fake_call(cmd, cwd=None, env=None):
        seen["cmd"] = cmd
        report_path = Path(cmd[cmd.index("--web-report") + 1])
        report_path.write_text(json.dumps(FIXTURE, ensure_ascii=False), encoding="utf-8")
        return 0
    monkeypatch.setattr("mv_analyzer.cli.subprocess.call", fake_call)
    out = tmp_path / "reason.json"
    assert main(["explain", "https://youtu.be/abcdefghijk", "--lang", "ko",
                 "--benchmark-domain", "all", "--data", str(data), "--out", str(out)]) == 0
    assert Path(seen["cmd"][1]).name == "analyze.py"
    assert "--web-report" in seen["cmd"] and "--out" in seen["cmd"]
    assert json.loads(out.read_text(encoding="utf-8"))["kind"] == "mv-analyzer-reason"


def test_explain_propagates_analyzer_failure(monkeypatch, tmp_path):
    monkeypatch.setattr("mv_analyzer.cli.subprocess.call", lambda *args, **kwargs: 7)
    out = tmp_path / "reason.json"
    assert main(["explain", "https://youtu.be/abcdefghijk", "--out", str(out),
                 "--data", str(tmp_path / "data")]) == 7
    assert not out.exists()


def test_reason_from_report_refuses_mismatched_source_fingerprint(tmp_path):
    from mv_analyzer.reason_export import reason_from_report_file
    source=tmp_path/'mv'; source.mkdir()
    row=dict(load_reference_rows(ROOT)[0]); (source/'features.json').write_text(json.dumps(row),encoding='utf-8')
    bad=json.loads(json.dumps(FIXTURE)); bad['pipeline']['source_features_sha256']='0'*64
    report=tmp_path/'report.json'; report.write_text(json.dumps(bad),encoding='utf-8')
    out=tmp_path/'reason.json'
    import pytest
    with pytest.raises(ValueError,match='fingerprint'):
        reason_from_report_file(report,source,out)
    assert not out.exists()
