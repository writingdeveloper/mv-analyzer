"""통합 mv CLI."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORWARD = {
    "analyze": "analyze.py",
    "batch": "batch.py",
    "collect": "collect.py",
    "diagnose": "diagnose.py",
    "talk": "talk.py",
    "report": "p5_report.py",
    "dashboard": "build_dashboard.py",
    "trend": "trend_snapshot.py",
    "compare-domains": "compare_domains.py",
    "feature-structure": "feature_structure.py",
    "monotonicity": "monotonicity_report.py",
    "lyrics-structure": "lyrics_structure.py",
    "gate": "gate_report.py",
}


VIDEO_ID_ARG = re.compile(r"-[A-Za-z0-9_][A-Za-z0-9_-]{9}")
MARK = "__MVVID__"  # '-'로 시작하는 video_id를 argparse 옵션 오인에서 보호하는 접두 마커


def _unmark(x):
    """마커 제거. str.lstrip은 문자 집합을 떼어내 'D…'/'M…' id의 첫 글자를 잘라먹으므로 쓰지 않는다."""
    return x[len(MARK):] if x.startswith(MARK) else x


def _child_env():
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    return env


def _forward(cmd, rest):
    return subprocess.call(
        [sys.executable, str(ROOT / FORWARD[cmd]), *rest], cwd=ROOT, env=_child_env())


def _status(data_dir, db_path="work/mv_analyzer.duckdb"):
    from .index_freshness import index_status
    from .qa import scan_data
    s = scan_data(data_dir)
    idx = index_status(data_dir, db_path)
    print(f"data: {s['complete']} complete / {s['partial']} partial / {s['directories']} dirs")
    print(f"manifests: {s['manifest_count']} · stale: {len(s['stale_artifacts'])} · "
          f"feature widths: {s['feature_widths']} · schemas: {len(s['feature_schema_variants'])}")
    print(f"index: {'fresh' if idx['fresh'] else idx['reason']} · {db_path}")
    return 0


def _qa(args):
    from .qa import ok, scan_data
    s = scan_data(args.data)
    if args.json:
        print(json.dumps(s, ensure_ascii=False, indent=2))
    else:
        print(
            f"QA: complete={s['complete']} partial={s['partial']} "
            f"json_errors={len(s['json_errors'])} semantic_errors={len(s['semantic_errors'])} "
            f"warnings={len(s['warnings'])} tmp={len(s['tmp_files'])} "
            f"schemas={len(s['feature_schema_variants'])} manifests={s['manifest_count']} "
            f"stale={len(s['stale_artifacts'])}"
        )
    rc = 0 if ok(s) else 1
    if args.tests:
        test_rc = subprocess.call([sys.executable, "-m", "pytest", "-q"], cwd=ROOT, env=_child_env())
        rc = max(rc, test_rc)
    return rc


def _doctor(args):
    from .doctor import inspect_environment
    rows = inspect_environment(check_services=args.services)
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        for r in rows:
            print(f"{'OK ' if r['ok'] else 'ERR'} {r['name']:<14} {r['detail']}")
    optional = {"deno", "ollama", "ollama-api"}
    return 0 if all(r["ok"] for r in rows if r["name"] not in optional) else 1


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    argv = list(sys.argv[1:] if argv is None else argv)
    mark = MARK
    # 둘째 글자가 '-'인 토큰은 제외 — 11자 옵션(--keyframes 등)까지 마스킹하면 안 된다
    argv = [mark + x if VIDEO_ID_ARG.fullmatch(x) else x for x in argv]
    if argv and argv[0] in FORWARD:
        return _forward(argv[0], argv[1:])

    ap = argparse.ArgumentParser(prog="mva", description="mv-analyzer unified CLI (local-first)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in FORWARD:
        sub.add_parser(c, add_help=False, help=f"forward to {FORWARD[c]}")
    p = sub.add_parser("status"); p.add_argument("--data", default="data"); p.add_argument("--db", default="work/mv_analyzer.duckdb")
    p = sub.add_parser("doctor"); p.add_argument("--json", action="store_true"); p.add_argument("--services", action="store_true", help="로컬 서비스 health endpoint까지 확인 (추론 없음)")
    sub.add_parser("config")
    p = sub.add_parser("gpu-status"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("experiments"); p.add_argument("--work", default="work/experiments"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("qa"); p.add_argument("--data", default="data"); p.add_argument("--tests", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("stats-qa"); p.add_argument("--table", default="work/features_table.jsonl"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("dataset-qa"); p.add_argument("--dir", default="dataset"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("web-export"); p.add_argument("--out", default="web/public/data")
    p = sub.add_parser("report-export", help="offline CPU-only export from existing features.json")
    p.add_argument("source", help="features.json or its containing analysis directory")
    p.add_argument("--out", required=True)
    p.add_argument("--benchmark-domain", choices=["all", "vocaloid", "kpop"], default="all")
    p = sub.add_parser("reason-export", help="offline evidence-backed explanation from existing analysis")
    p.add_argument("source", help="features.json or its containing analysis directory")
    p.add_argument("--out", required=True)
    p.add_argument("--benchmark-domain", choices=["all", "vocaloid", "kpop"], default="all")
    p.add_argument("--favorites", help="favorite MV id/URL list for optional taste reasoning")
    p.add_argument("--data", default="data", help="local analyzed-video corpus used by favorites profile")
    p.add_argument("--output-lang", choices=["ko", "en"], default="ko")
    p = sub.add_parser("explain", help="run the existing local analyzer, then produce an evidence-backed reason document")
    p.add_argument("url")
    p.add_argument("--lang", choices=["ja", "ko"], default="ja")
    p.add_argument("--benchmark-domain", choices=["all", "vocaloid", "kpop"], default="all")
    p.add_argument("--favorites", help="favorite MV id/URL list for optional taste reasoning")
    p.add_argument("--data", default="data", help="analysis output directory")
    p.add_argument("--out", default="reason.json")
    p.add_argument("--force-gpu-busy", action="store_true")
    p.add_argument("--output-lang", choices=["ko", "en"], default="ko")
    p = sub.add_parser("index"); p.add_argument("--data", default="data"); p.add_argument("--db", default="work/mv_analyzer.duckdb"); p.add_argument("--check", action="store_true")
    p = sub.add_parser("search"); p.add_argument("query"); p.add_argument("--data", default="data"); p.add_argument("--db", default="work/mv_analyzer.duckdb"); p.add_argument("--limit", type=int, default=50)
    p = sub.add_parser("similar"); p.add_argument("video_id"); p.add_argument("--data", default="data"); p.add_argument("--limit", type=int, default=10)
    p = sub.add_parser("benchmark"); p.add_argument("video_id"); p.add_argument("--data", default="data")
    p = sub.add_parser("outliers"); p.add_argument("--data", default="data"); p.add_argument("--limit", type=int, default=10)
    p = sub.add_parser("motion"); p.add_argument("video"); p.add_argument("--sample-fps", type=float, default=2.0); p.add_argument("--json", action="store_true")
    p = sub.add_parser("music-structure"); p.add_argument("audio"); p.add_argument("--out", required=True); p.add_argument("--json", action="store_true")
    p = sub.add_parser("evaluate-motion"); p.add_argument("rows"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("motion-batch"); p.add_argument("--data", default="data"); p.add_argument("--out", default="work/experiments/motion/corpus.jsonl"); p.add_argument("--sample-fps", type=float, default=2.0); p.add_argument("--static-threshold", type=float, default=0.35); p.add_argument("--json", action="store_true")
    p = sub.add_parser("motion-scenes", help="씬별 움직임 3분류 (static_image/animated_still/motion_clip, CPU 실험 측정기)"); p.add_argument("video", help="video_id 또는 data/<id> 디렉터리"); p.add_argument("--data", default="data"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("motion-scenes-batch"); p.add_argument("--data", default="data"); p.add_argument("--out", default="work/experiments/motion/scenes_corpus.jsonl"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("gen-frames", help="생성용 레퍼런스 프레임 (무자막 판본에서 뽑고 필러박스 제거)"); p.add_argument("video"); p.add_argument("--data", default="data"); p.add_argument("--clean-source", help="같은 곡의 무자막 판본 video_id"); p.add_argument("--out"); p.add_argument("--no-crop", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("motion-label", help="모션 3분류 사람 라벨 게이트용 층화 표본·스트립 생성 (블라인드)"); p.add_argument("--data", default="data"); p.add_argument("--n", type=int, default=45); p.add_argument("--seed", type=int, default=20260903); p.add_argument("--out", default="work/experiments/motion/label"); p.add_argument("--protocol", choices=("burst", "stills"), default="burst"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("motion-label-score", help="채워진 라벨 시트를 정답키와 대조 (일치율·Cohen's kappa)"); p.add_argument("--dir", default="work/experiments/motion/label"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("caption-scan", help="YouTube 자막 트랙 가용성 스캔 (네트워크만, 가사 본문 미수집)"); p.add_argument("--data", default="data"); p.add_argument("--out", default="work/caption_scan.jsonl"); p.add_argument("--limit", type=int, default=None); p.add_argument("--sleep", type=float, default=1.0); p.add_argument("--summary-only", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("evaluate-vlm"); p.add_argument("predictions", nargs="?"); p.add_argument("--baseline", action="store_true"); p.add_argument("--sample", default="work/reliability_sample.json"); p.add_argument("--labels", nargs="+", default=["work/reliability_labels_A.json", "work/reliability_labels_B.json"]); p.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.cmd == "status":
        return _status(args.data, args.db)
    if args.cmd == "doctor":
        return _doctor(args)
    if args.cmd == "config":
        from .config import as_dict
        print(json.dumps(as_dict(), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "gpu-status":
        from .experiments import gpu_snapshot_summary
        result = gpu_snapshot_summary()
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            state = "busy" if result["busy"] else ("idle" if result["available"] else "unavailable")
            print(f"GPU: {state} · memory={result['max_memory_used_mb']} MiB · util={result['max_utilization_pct']}%")
        return 1 if result["busy"] else 0
    if args.cmd == "experiments":
        from .experiments import experiment_status
        result = experiment_status(args.work)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            gpu = result["gpu"]
            print(f"GPU: {'busy' if gpu['busy'] else ('idle' if gpu['available'] else 'unavailable')} · "
                  f"{gpu['max_memory_used_mb']} MiB · {gpu['max_utilization_pct']}%")
            for row in result["experiments"]:
                print(f"{row['state']:<15} {row['id']:<26} {row['output']}")
                print(f"  next: {row['next']}")
        return 0
    if args.cmd == "qa":
        return _qa(args)
    if args.cmd == "report-export":
        from .report_export import export_existing_report
        report = export_existing_report(ROOT, Path(args.source), Path(args.out), domain=args.benchmark_domain)
        print(f"Offline Web report: {len(report['features'])} features; PCA {report['pca']['status']} → {args.out}")
        return 0
    if args.cmd == "reason-export":
        from .reason_export import export_existing_reason
        reason = export_existing_reason(
            ROOT, Path(args.source), Path(args.out), domain=args.benchmark_domain,
            favorites=Path(args.favorites) if args.favorites else None, data_dir=Path(args.data),
        )
        from .reason import render_reason_summary
        print(f"Offline reason: {len(reason['claims'])} claims → {args.out}")
        for row in render_reason_summary(reason, args.output_lang):
            print(f"- {row['text']}")
        return 0
    if args.cmd == "explain":
        from .reason_export import reason_from_report_file
        with tempfile.TemporaryDirectory(prefix="mva-explain-") as temp_dir:
            report_path = Path(temp_dir) / "report.json"
            cmd = [
                sys.executable, str(ROOT / "analyze.py"), args.url, "--out", args.data, "--lang", args.lang,
                "--web-report", str(report_path), "--benchmark-domain", args.benchmark_domain,
            ]
            if args.force_gpu_busy:
                cmd.append("--force-gpu-busy")
            rc = subprocess.call(cmd, cwd=ROOT, env=_child_env())
            if rc:
                return rc
            report = json.loads(report_path.read_text(encoding="utf-8-sig"))
            source = Path(args.data) / report["video"]["video_id"]
            reason = reason_from_report_file(
                report_path, source, Path(args.out), favorites=Path(args.favorites) if args.favorites else None,
                data_dir=Path(args.data),
            )
        from .reason import render_reason_summary
        print(f"Reason: {len(reason['claims'])} claims → {args.out}")
        for row in render_reason_summary(reason, args.output_lang):
            print(f"- {row['text']}")
        return 0
    if args.cmd == "web-export":
        from .web_export import build_public_snapshot
        paths = build_public_snapshot(ROOT, Path(args.out))
        print(f"web snapshot: {len(paths)} files → {args.out}")
        return 0
    if args.cmd == "dataset-qa":
        from .dataset_qa import audit_all
        result = audit_all(args.dir)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            for row in result["datasets"]:
                print(f"{row['path']}: {row['rows']} rows × {row['cols']} cols · "
                      f"groups={row['groups']} domains={row['domains']} errors={len(row['errors'])}")
                for error in row["errors"]:
                    print(f"  ERR {error}")
        return 0 if result["ok"] else 1
    if args.cmd == "stats-qa":
        from .feature_policy import audit_ok, audit_rows
        rows = [json.loads(line) for line in Path(args.table).read_text(encoding="utf-8").splitlines() if line.strip()]
        audit = audit_rows(rows)
        if args.json:
            print(json.dumps(audit, ensure_ascii=False, indent=2))
        else:
            print(f"rows={audit['n_rows']} groups={audit['groups']} errors={len(audit['errors'])} warnings={len(audit['warnings'])}")
            print(f"formal_missing={len(audit['missing_formal_columns'])} constant={len(audit['constant_numeric'])} low_coverage={len(audit['low_coverage_numeric'])} experimental={audit['experimental_columns']}")
            for msg in audit["errors"]:
                print(f"ERR {msg}")
            for msg in audit["warnings"]:
                print(f"WARN {msg}")
        return 0 if audit_ok(audit) else 1
    if args.cmd == "index":
        from .index import build_index
        from .index_freshness import index_status
        if args.check:
            idx = index_status(args.data, args.db)
            print(json.dumps(idx, ensure_ascii=False, indent=2))
            return 0 if idx["fresh"] else 1
        counts = build_index(args.data, args.db)
        print(f"indexed features={counts['features']} lyrics={counts['lyrics']} scenes={counts['scenes']} → {args.db}")
        return 0
    if args.cmd == "search":
        from .index import search_index
        from .index_freshness import ensure_index
        idx = ensure_index(args.data, args.db)
        if idx["rebuilt"]:
            counts = idx["counts"] or {}
            print(f"[index] stale/missing → rebuilt features={counts.get('features', 0)} "
                  f"lyrics={counts.get('lyrics', 0)} scenes={counts.get('scenes', 0)}", file=sys.stderr)
        rows = search_index(args.query, args.db, args.limit)
        for i, r in enumerate(rows, 1):
            print(f"{i:2d}. {r}")
        return 0
    if args.cmd == "evaluate-vlm":
        from .reliability import load_baseline, load_reference_labels, score_predictions
        if not args.baseline and not args.predictions:
            ap.error("evaluate-vlm requires <predictions.json> or --baseline")
        predictions = load_baseline(args.sample) if args.baseline else json.loads(Path(args.predictions).read_text(encoding="utf-8"))
        labels = load_reference_labels(args.labels)
        result = score_predictions(predictions, labels)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"n={result['n']}")
            for field, row in result["categorical"].items():
                print(f"{field}: accuracy={row['accuracy']:.1%} kappa={row['kappa']:.3f}")
            chars = result["num_characters"]
            if chars:
                print(f"num_characters: exact={chars.get('exact', 0):.1%} ±1={chars.get('within1', 0):.1%} rho={chars.get('spearman_rho')}")
        return 0
    if args.cmd == "motion-batch":
        from .motion_validation import measure_corpus_motion
        result = measure_corpus_motion(args.data, args.out, sample_fps=args.sample_fps,
                                       static_threshold=args.static_threshold)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"motion batch → {args.out} · measured={result['measured']} "
                  f"skipped={result['skipped']} missing={result['missing_video']}")
        return 0
    if args.cmd == "motion-scenes":
        from .motion import measure_scene_motion
        target = Path(_unmark(args.video))
        if not target.is_dir():
            target = Path(args.data) / _unmark(args.video)
        payload = measure_scene_motion(target)
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            for k, v in payload["summary"].items():
                print(f"{k}: {v}")
            print(f"→ {target / 'motion_scenes.json'}")
        return 0
    if args.cmd == "motion-scenes-batch":
        from .motion import measure_corpus_scene_motion
        result = measure_corpus_scene_motion(args.data, args.out, log=lambda m: print(m, flush=True))
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"scene motion batch → {result['out']} · measured={result['measured']} "
                  f"skipped={result['skipped']} missing={result['missing']}")
        return 0
    if args.cmd == "gen-frames":
        from .gen_frames import build as build_gen_frames
        try:
            r = build_gen_frames(_unmark(args.video), args.data, args.clean_source,
                                 args.out, crop=not args.no_crop)
        except ValueError as e:
            print(e, file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(r, ensure_ascii=False, indent=2))
        else:
            sizes = {}
            for f in r["frames"]:
                sizes[tuple(f["size"])] = sizes.get(tuple(f["size"]), 0) + 1
            print(f"생성용 프레임 {r['n']}장 → {r['out_dir']}  (소스 {r['source']})")
            print(f"  필러박스 제거 {r['n_cropped']}장 · " +
                  " · ".join(f"{w}x{h} {n}장" for (w, h), n in sorted(sizes.items(), reverse=True)))
            if r["failed"]:
                print(f"  프레임 추출 실패 씬: {' '.join(map(str, r['failed']))}")
            print("  talk export --keyframes 로 꽂아 쓸 것 (I2VA 첫 프레임이 여기서 나온다)")
        return 0
    if args.cmd == "motion-label":
        from .motion_label import build
        r = build(args.data, n=args.n, seed=args.seed, out_dir=args.out, protocol=args.protocol)
        if args.json:
            print(json.dumps(r, ensure_ascii=False, indent=2))
        else:
            print(f"라벨 표본 {r['n_items']}개 → {args.out}  (seed {r['seed']} · 프로토콜 {r['protocol']})")
            print("  예측 분포: " + " · ".join(f"{k} {v}" for k, v in r["by_class"].items()))
            if r["failed"]:
                print(f"  스트립 생성 실패 {len(r['failed'])}개: {' '.join(r['failed'])}")
            print(f"  시트(라벨 비어 있음): {r['sheet']}")
            print(f"  정답키(라벨링 전 열지 말 것): {r['key']}")
            print("  어휘: " + " / ".join(f"{k}={v.split(' — ')[0]}" for k, v in r["vocab"].items()))
            print(f"  사전 등록 게이트: 일치율 >= {r['gate']['min_agreement']} 그리고 kappa >= {r['gate']['min_kappa']}")
        return 0
    if args.cmd == "motion-label-score":
        from .motion_label import score
        d = Path(args.dir)
        r = score(str(d / "sheet.jsonl"), str(d / "key.jsonl"))
        if args.json:
            print(json.dumps(r, ensure_ascii=False, indent=2))
        elif r.get("error"):
            print(r["error"])
            return 1
        else:
            print(f"라벨 {r['n_labeled']}/{r['n_items']} · 일치율 {r['agreement']} · kappa {r['kappa']} "
                  f"→ 게이트 {'통과' if r['passed'] else '미통과'}")
            for c, d2 in r["per_class"].items():
                print(f"  {c:<16} 정밀도 {d2['precision']} · 재현율 {d2['recall']} "
                      f"(예측 {d2['n_pred']} / 사람 {d2['n_human']})")
        return 0
    if args.cmd == "caption-scan":
        from .captions import scan_corpus, summarize_scan
        if not args.summary_only:
            scan_corpus(args.data, args.out, limit=args.limit, sleep_s=args.sleep,
                        log=lambda m: print(m, flush=True))
        rows = [json.loads(l) for l in Path(args.out).read_text(encoding="utf-8").splitlines() if l.strip()] if Path(args.out).exists() else []
        summary = summarize_scan(rows)
        if args.json:
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        else:
            print(f"caption scan: n={summary['n']} manual={summary['with_manual_track']} "
                  f"original-lang={summary['with_original_lang_track']}")
            for src, d in summary["by_lyrics_source"].items():
                print(f"  lyrics_source={src}: {d['with_original_track']}/{d['n']} have original-language track")
            print(f"  missing-lyrics recoverable: {len(summary['missing_lyrics_recoverable'])} "
                  f"· asr upgradable: {len(summary['asr_upgradable'])}")
        return 0
    if args.cmd == "evaluate-motion":
        from .motion_validation import score_motion_validation
        path = Path(args.rows)
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        result = score_motion_validation(rows)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"motion validation: n={result['n']} passes_ordering={result['passes_ordering']}")
            for label, row in result["classes"].items():
                print(f"  {label}: n={row['n']} median={row['median']} mean={row['mean']}")
            print(result["interpretation"])
        return 0 if result["passes_ordering"] else 1
    if args.cmd == "music-structure":
        from .music_structure import run_music_structure
        result = run_music_structure(args.audio, args.out)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"music structure → {args.out} · chorus={result['chorus_count']} "
                  f"first={result['first_chorus_s']}")
        return 0
    if args.cmd == "motion":
        from .motion import analyze_motion
        path = Path(args.video)
        if not path.exists() and len(_unmark(args.video)) == 11:
            path = ROOT / "data" / _unmark(args.video) / "video.mp4"
        result = analyze_motion(path, sample_fps=args.sample_fps)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            for k, v in result.items():
                print(f"{k}: {v}")
        return 0
    if args.cmd in {"similar", "benchmark", "outliers"}:
        from .similarity import benchmark, outliers, similar
        if args.cmd == "similar":
            rows = similar(_unmark(args.video_id), args.data, args.limit)
        elif args.cmd == "benchmark":
            rows = benchmark(_unmark(args.video_id), args.data)
        else:
            rows = outliers(args.data, args.limit)
        for i, r in enumerate(rows, 1):
            print(f"{i:2d}. {r}")
        return 0
    return 2
