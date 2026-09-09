from mv_analyzer.cli import main


def test_status_empty(tmp_path, capsys):
    assert main(["status", "--data", str(tmp_path)]) == 0
    assert "data:" in capsys.readouterr().out


def test_web_export_builds_public_snapshot(tmp_path, capsys):
    out = tmp_path / "web-data"
    assert main(["web-export", "--out", str(out)]) == 0
    assert (out / "manifest.json").exists()
    assert (out / "space.json").exists()
    assert "web snapshot" in capsys.readouterr().out.lower()


def test_analyze_parser_accepts_web_report_and_benchmark_domain():
    import analyze as analyze_script

    args = analyze_script.build_parser().parse_args([
        "https://youtu.be/abcdefghijk",
        "--web-report", "result.json",
        "--benchmark-domain", "kpop",
    ])

    assert args.web_report == "result.json"
    assert args.benchmark_domain == "kpop"


def test_analyze_web_report_helper_is_noop_without_flag(monkeypatch):
    import analyze as analyze_script

    called = False

    def fail_if_called(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("report builder should not be called")

    monkeypatch.setattr(analyze_script, "build_analyze_report", fail_if_called)
    args = analyze_script.build_parser().parse_args(["https://youtu.be/abcdefghijk"])

    analyze_script.write_web_report_if_requested(args, {"video_id": "abcdefghijk"})

    assert called is False


def test_analyze_web_report_helper_builds_and_writes(monkeypatch, tmp_path):
    import analyze as analyze_script

    captured = {}
    output = tmp_path / "result.json"
    args = analyze_script.build_parser().parse_args([
        "https://youtu.be/abcdefghijk",
        "--web-report", str(output),
        "--benchmark-domain", "vocaloid",
    ])
    row = {"video_id": "abcdefghijk", "title": "Example", "channel": "Channel"}

    def fake_build(root, target, *, domain):
        captured["root"] = root
        captured["target"] = target
        captured["domain"] = domain
        return {"schema_version": 1, "kind": "mv-analyzer-report"}

    def fake_write(path, report):
        captured["path"] = path
        captured["report"] = report

    monkeypatch.setattr(analyze_script, "build_analyze_report", fake_build)
    monkeypatch.setattr(analyze_script, "write_analyze_report", fake_write)

    analyze_script.write_web_report_if_requested(args, row)

    assert captured["target"] is row
    assert captured["domain"] == "vocaloid"
    assert captured["path"] == output
    assert captured["report"]["kind"] == "mv-analyzer-report"


def test_skip_vlm_web_report_requires_completed_features(tmp_path):
    import analyze as analyze_script

    args = analyze_script.build_parser().parse_args([
        "https://youtu.be/abcdefghijk",
        "--skip-vlm",
        "--web-report", str(tmp_path / "report.json"),
    ])

    with __import__("pytest").raises(SystemExit, match="complete features.json"):
        analyze_script.write_existing_web_report_or_fail(args, tmp_path)
