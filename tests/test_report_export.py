import json
import socket
from pathlib import Path

import pytest

from mv_analyzer.cli import main
from mv_analyzer.reference_corpus import load_reference_rows

ROOT=Path(__file__).resolve().parents[1]


def test_report_export_is_offline_and_does_not_touch_source(monkeypatch,tmp_path):
    def forbidden(*args,**kwargs):
        raise AssertionError("network access during offline export")
    monkeypatch.setattr(socket.socket,"connect",forbidden)
    source=tmp_path/"features.json"
    row=dict(load_reference_rows(ROOT)[0])
    source.write_text(json.dumps(row),encoding="utf-8")
    before=source.read_bytes()
    destination=tmp_path/"report.json"
    assert main(["report-export",str(source),"--out",str(destination),"--benchmark-domain","vocaloid"])==0
    report=json.loads(destination.read_text(encoding="utf-8"))
    assert report["schema_version"]==2
    assert report["benchmark"]["domain"]=="vocaloid"
    assert source.read_bytes()==before


def test_report_export_reads_recorded_measurement_sha(tmp_path):
    folder=tmp_path/"mv"
    folder.mkdir()
    (folder/"features.json").write_text(json.dumps(load_reference_rows(ROOT)[0]),encoding="utf-8")
    (folder/"analysis_manifest.json").write_text(json.dumps({"git_commit":"a"*40,"artifacts":{"features.json":{"status":"generated","fingerprint":"original-fingerprint"}}}),encoding="utf-8")
    destination=tmp_path/"report.json"
    assert main(["report-export",str(folder),"--out",str(destination)])==0
    report=json.loads(destination.read_text(encoding="utf-8"))
    assert report["pipeline"]["measurement_git_commit"]=="a"*40


def test_report_export_never_overwrites_measurement(tmp_path):
    source=tmp_path/"features.json"
    source.write_text(json.dumps(load_reference_rows(ROOT)[0]),encoding="utf-8")
    before=source.read_bytes()
    with pytest.raises((ValueError,SystemExit)):
        main(["report-export",str(source),"--out",str(source)])
    assert source.read_bytes()==before
