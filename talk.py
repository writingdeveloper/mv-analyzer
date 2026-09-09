"""MV 대화 CLI — 분석 끝난 영상의 근거를 시간축으로 꺼내온다 (읽기 전용, GPU 불필요).

usage:
  python talk.py list [--query 검색어] [--limit N]
  python talk.py show <URL|id>
  python talk.py timeline <URL|id> [--from 0] [--to 9999]
  python talk.py at <URL|id> <초> [--window 8]
  python talk.py search <검색어> [--limit N]
  python talk.py compare <id> <id> [...]
  python talk.py profile <id> [...] [--list 파일]
  python talk.py export <URL|id> [--out 경로]
  python talk.py sanitize <vision.json> [--out 경로] [--typography abstract]

모든 서브커맨드에 --json 사용 가능. 대화는 호출자가 하고, 여기서는 근거만 낸다.
"""
import argparse
import json
import re
import sys

from mv_analyzer import talk

# YouTube video_id는 '-'로 시작할 수 있어 argparse가 옵션으로 오인한다.
# 파싱 전 마커를 붙여 숨기고, 값을 쓸 때 _vid()로 벗긴다.
# 둘째 글자가 '-'인 토큰은 제외한다 — 그러지 않으면 11자 옵션(--keyframes)까지 삼킨다.
_MARK = "\x00"
VIDEO_ID_ARG = re.compile(r"-[A-Za-z0-9_][A-Za-z0-9_-]{9}")


def _mask_ids(argv):
    return [_MARK + t if VIDEO_ID_ARG.fullmatch(t) else t
            for t in argv]


def _vid(s):
    return talk.extract_video_id(s.lstrip(_MARK))


def _out(obj, as_json, render):
    if as_json:
        print(json.dumps(obj, ensure_ascii=False, indent=2))
    else:
        render(obj)


def _fmt_t(t):
    if t is None:
        return "  --  "
    return f"{int(t) // 60:d}:{int(t) % 60:02d}"


def _fmt_int(v):
    return f"{v:,}" if isinstance(v, (int, float)) else "N/A"


def cmd_list(args):
    rows = talk.catalog(args.data)
    if args.query:
        q = args.query.casefold()
        rows = [r for r in rows
                if q in str(r.get("title", "")).casefold()
                or q in str(r.get("channel", "")).casefold()]
    rows = rows[:args.limit]

    def render(rows):
        print(f"분석 완료 {len(rows)}편 (data/)")
        for r in rows:
            print(f"  {r['video_id']}  {_fmt_t(r['duration_s'])}  "
                  f"컷/분 {r['cuts_per_minute']}  BPM {r['bpm']}  "
                  f"{r['style'] or '-'}/{r['mood'] or '-'}  "
                  f"[{r['channel']}] {r['title']}")
    _out(rows, args.json, render)
    return 0


def cmd_show(args):
    b = talk.load(_vid(args.video), args.data)
    if not b:
        print("분석 결과 없음 — analyze.py를 먼저 실행하세요", file=sys.stderr)
        return 1
    f = b.get("features") or {}
    s = (b.get("scenes") or {}).get("summary") or {}
    a = b.get("audio") or {}
    ly = b.get("lyrics") or {}
    obj = {"video_id": b["video_id"], "features": f, "scene_summary": s,
           "audio": {k: v for k, v in a.items() if not isinstance(v, list)},
           "sync": b.get("sync"), "thumb": b.get("thumb"),
           "n_lyric_lines": len(ly.get("lines") or []),
           "lyrics_lang": ly.get("lang"), "lyrics_source": ly.get("source")}

    def render(o):
        print(f"# {f.get('title')}\n  채널 {f.get('channel')} · 구독 {f.get('subscriber_count'):,} "
              f"· 조회 {f.get('view_count'):,} · vps {f.get('view_per_sub')}")
        print(f"  길이 {_fmt_t(f.get('duration_s'))} · {f.get('upload_date')} "
              f"· {f.get('width')}x{f.get('height')}@{f.get('fps')}")
        print(f"\n[화면] 씬 {s.get('num_scenes')}개 · 컷/분 {s.get('cuts_per_minute')} "
              f"· 샷 중앙값 {s.get('median_shot_len_s')}s "
              f"(최단 {s.get('min_shot_len_s')} / 최장 {s.get('max_shot_len_s')})")
        print(f"  밝기 {s.get('avg_brightness')} · 채도 {s.get('avg_saturation')} "
              f"· 스타일 {f.get('tag_style_top')} · 무드 {f.get('tag_mood_top')} "
              f"· 클로즈업비 {f.get('tag_closeup_ratio')}")
        print(f"\n[소리] BPM {a.get('bpm')} · 키 {a.get('key')}({a.get('key_confidence')}) "
              f"· LUFS {f.get('audio_lufs_i')} · 온셋/초 {a.get('onsets_per_sec')} "
              f"· 최고에너지 {_fmt_t(a.get('peak_energy_at_s'))}")
        sy = b.get("sync") or {}
        print(f"\n[동기] 비트정렬 컷비율 {sy.get('cut_on_beat_ratio')} "
              f"· 컷당 비트 {sy.get('beats_per_cut')} "
              f"· 첫 컷 {_fmt_t(sy.get('first_cut_s'))} "
              f"· 첫 가사 {_fmt_t(sy.get('first_lyric_at_s'))}")
        print(f"\n[가사] {o['n_lyric_lines']}줄 · {o['lyrics_lang']} · 출처 {o['lyrics_source']} "
              f"· 주제 {f.get('lyrics_topic_1')}/{f.get('lyrics_topic_2')} "
              f"· 정서 {f.get('lyrics_sentiment')} · 대상 {f.get('lyrics_addressee')}")
        print(f"\n키프레임: {b['dir']}/keyframes/  (Read 툴로 실제 화면 확인 가능)")
    _out(obj, args.json, render)
    return 0


def cmd_timeline(args):
    b = talk.load(_vid(args.video), args.data)
    if not b:
        print("분석 결과 없음", file=sys.stderr)
        return 1
    ev = [e for e in talk.timeline(b)
          if args.from_s <= (e.get("t_s") or 0) <= args.to_s]

    def render(ev):
        print(f"# 타임라인 — {(b.get('features') or {}).get('title')}")
        for e in ev:
            t = _fmt_t(e.get("t_s"))
            if e["kind"] == "scene":
                vis = ", ".join(e.get("visual_elements") or [])
                print(f"{t} ▮ 씬{e['scene']} ({e['len_s']}s) "
                      f"{e.get('shot_type') or '-'}/{e.get('mood') or '-'} "
                      f"· {e.get('setting') or '-'}"
                      + (f" · {vis}" if vis else "")
                      + f"  [{e.get('keyframe')}]")
            elif e["kind"] == "lyric":
                print(f"{t} ♪ {e['line']}")
            else:
                print(f"{t} ★ {e.get('note')}")
    _out(ev, args.json, render)
    return 0


def cmd_at(args):
    b = talk.load(_vid(args.video), args.data)
    if not b:
        print("분석 결과 없음", file=sys.stderr)
        return 1
    try:
        ctx = talk.at(b, args.t, args.window)
    except ValueError as e:
        print(f"잘못된 시각: {e}", file=sys.stderr)
        return 2

    def render(c):
        print(f"# {c['title']} @ {_fmt_t(c['t_s'])} (전체의 {c['position_ratio']})")
        sc = c.get("scene") or {}
        tg = sc.get("tags") or {}
        print(f"\n[화면] 씬{sc.get('scene')} {sc.get('start_s')}~{sc.get('end_s')}s "
              f"({sc.get('len_s')}s) · 밝기 {sc.get('brightness')} "
              f"· 채도 {sc.get('saturation')} · 색 {sc.get('dominant_color')}")
        if tg:
            print(f"  {tg.get('shot_type')}/{tg.get('style')}/{tg.get('mood')} "
                  f"· {tg.get('setting')} · 인물 {tg.get('num_characters')}명 "
                  f"· {', '.join(tg.get('visual_elements') or [])}")
        print(f"  키프레임: {sc.get('keyframe_path')}")
        ln = c.get("lyrics_near") or []
        print(f"\n[가사 ±{args.window}s] " + ("없음" if not ln else ""))
        for l in ln:
            print(f"  {_fmt_t(l.get('t_s'))} ♪ {l.get('line')}")
        en = c.get("energy") or {}
        bs = en.get("bin_s") or [None, None]
        print(f"\n[리듬] 직전 30초 컷 {c['cuts_last_30s']}개 · "
              f"에너지 {_fmt_t(bs[0])}~{_fmt_t(bs[1])} 구간 {en.get('value')} "
              f"(곡 최고의 {en.get('ratio_to_peak')}배, 최고점 {_fmt_t(en.get('peak_at_s'))})")
    _out(ctx, args.json, render)
    return 0


def cmd_search(args):
    hits = talk.search(args.query, args.data, limit=args.limit)

    def render(hits):
        print(f"'{args.query}' — {len(hits)}건")
        for h in hits:
            print(f"  {h['video_id']} {_fmt_t(h['t_s'])} [{h['where']}] "
                  f"{h['text'][:70]}  ({h['title']})")
    _out(hits, args.json, render)
    return 0


def cmd_compare(args):
    vids = [_vid(v) for v in args.videos]
    res = talk.compare(vids, args.data)
    if not res:
        print("비교할 분석 결과 없음", file=sys.stderr)
        return 1

    def render(r):
        print(f"# {r['n_videos']}편 비교")
        for v in r["videos"]:
            print(f"  - {v['video_id']} {v['title']}")
        print("\n[공통된 형질 — 편차 작은 순]")
        for d in r["numeric"][:8]:
            print(f"  {d['label']:<18} 중앙값 {d['median']:<8} "
                  f"범위 {d['min']}~{d['max']} (퍼짐 {d['spread_ratio']})")
        print("\n[편차 큰 지표]")
        for d in r["numeric"][-4:]:
            print(f"  {d['label']:<18} 중앙값 {d['median']:<8} "
                  f"범위 {d['min']}~{d['max']} (퍼짐 {d['spread_ratio']})")
        print("\n[범주형 — 쏠림 순]")
        for d in r["categorical"]:
            print(f"  {d['label']:<18} {d['top']} ({d['share']:.0%}, n={d['n']})")
    _out(res, args.json, render)
    return 0


def cmd_profile(args):
    vids = talk.read_id_list(args.list) if args.list else []
    vids += [_vid(v) for v in args.videos if _vid(v) not in vids]
    if not vids:
        print("영상 id 또는 --list 파일이 필요합니다", file=sys.stderr)
        return 1
    r = talk.profile(vids, args.data)

    def render(r):
        print(f"# 취향 프로파일 — {r['n_videos']}편 (코퍼스 {r['n_corpus']}편 대비)")
        for v in r["videos"]:
            print(f"  - {v['video_id']} {v['title']}")
        if r["missing"]:
            print(f"  미분석 {len(r['missing'])}편: {' '.join(r['missing'])}  (analyze.py 필요)")
        if not r["n_videos"]:
            return
        print("\n[수치 — 특이점 → 공통 → 관습 → 무관 순]  백분위=코퍼스 내 위치")
        for d in r["numeric"]:
            pts = " ".join(f"{p['pct']:.0f}" for p in d["points"])
            print(f"  {d['verdict']:<9} {d['label']:<16} 중앙값 {d['median']:<8} "
                  f"백분위 중앙 {d['median_pct']:>5.1f} [{pts}]")
        print("\n[범주형]  목록 쏠림 vs 코퍼스 비율")
        for d in r["categorical"]:
            cs = f"{d['corpus_share']:.0%}" if d["corpus_share"] is not None else "-"
            print(f"  {d['verdict']:<6} {d['label']:<12} {d['top']} ({d['share']:.0%} vs 코퍼스 {cs})")
        pal = r.get("palette") or {}
        if pal.get("diff"):
            print("\n[색 팔레트 — 씬 길이 가중, 목록 평균 − 코퍼스 평균]")
            for d in pal["diff"][:4] + [x for x in pal["diff"][-2:] if x["delta"] < 0]:
                print(f"  {d['bucket']:<4} 목록 {d['favorites']:.0%} / 코퍼스 {d['corpus']:.0%} "
                      f"({d['delta']:+.0%})")
    _out(r, args.json, render)
    return 0


def cmd_export(args):
    from mv_analyzer.blueprint_export import export_openmontage
    out, payload = export_openmontage(_vid(args.video), args.data, args.out, args.keyframes)
    if not out:
        print("분석 결과 없음", file=sys.stderr)
        return 1
    meta = payload["_analysis_meta"]
    print(f"OpenMontage 호환 분석 → {out}")
    print(f"  씬 {meta['scene_count']} · 키프레임 {meta['keyframe_count']} · 단계 {', '.join(meta['steps_completed'])}")
    print("  5요소(subject/scene/camera…)는 비어 있음 — reference-lab에서 키프레임을 보고 채울 것")
    return 0


def cmd_sanitize(args):
    from mv_analyzer.prompt_sanitize import sanitize_file
    try:
        out, rep = sanitize_file(args.vision, args.out, args.typography)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f"읽을 수 없음: {e}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0
    print(f"생성용 비전 시맨틱스 → {out}")
    print(f"  샷 {rep['n_shots']}개 중 {rep['n_shots_changed']}개 수정 · "
          + " · ".join(f"{k} {v}" for k, v in sorted(rep["removed_by_rule"].items())))
    if rep["needs_rewrite"]:
        print(f"  ! 필드가 통째로 산물이라 원문 유지(사람이 다시 쓸 것): "
              f"샷 {' '.join(map(str, rep['needs_rewrite']))}")
    if rep["n_typography_abstracted"]:
        print(f"  · 타이포그래피 {rep['n_typography_abstracted']}곳을 형태 서술로 치환")
    if rep["text_dependent"]:
        print(f"  · 글자에 기대는 샷 {len(rep['text_dependent'])}개 / 절 {rep['n_text_clauses']}개 "
              f"— 지우지 않음, 영상 생성 모델은 글자를 못 그리니 확인 필요")
        for a in rep["shots"]:
            for t in (a.get("text_dependent") or [])[:1]:
                print(f"    샷 {a['shot_number']:>2} [{t['field']}] {t['clause'][:78]}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default="data")
    ap.add_argument("--json", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list"); p.add_argument("--query"); \
        p.add_argument("--limit", type=int, default=200); p.set_defaults(fn=cmd_list)
    p = sub.add_parser("show"); p.add_argument("video"); p.set_defaults(fn=cmd_show)
    p = sub.add_parser("timeline"); p.add_argument("video")
    p.add_argument("--from", dest="from_s", type=float, default=0.0)
    p.add_argument("--to", dest="to_s", type=float, default=1e9)
    p.set_defaults(fn=cmd_timeline)
    p = sub.add_parser("at"); p.add_argument("video"); p.add_argument("t", type=float)
    p.add_argument("--window", type=float, default=8.0); p.set_defaults(fn=cmd_at)
    p = sub.add_parser("search"); p.add_argument("query")
    p.add_argument("--limit", type=int, default=50); p.set_defaults(fn=cmd_search)
    p = sub.add_parser("compare"); p.add_argument("videos", nargs="+")
    p.set_defaults(fn=cmd_compare)
    p = sub.add_parser("profile", help="취향 목록의 공통 형질을 코퍼스 백분위와 함께")
    p.add_argument("videos", nargs="*"); p.add_argument("--list", help="id/URL 목록 파일 (# 주석 가능)")
    p.set_defaults(fn=cmd_profile)
    p = sub.add_parser("export", help="OpenMontage 호환 분석 JSON 내보내기 (reference-lab --from-analysis)")
    p.add_argument("video"); p.add_argument("--out")
    p.add_argument("--keyframes", help="키프레임 디렉터리 교체 (mva gen-frames 산출물 등)")
    p.set_defaults(fn=cmd_export)
    p = sub.add_parser("sanitize", help="비전 시맨틱스에서 레퍼런스 고유 요소를 걷어낸 생성용 변형")
    p.add_argument("vision", help="<id>.vision.json"); p.add_argument("--out")
    p.add_argument("--typography", choices=("keep", "abstract"), default="keep",
                   help="abstract: 읽히는 글자 요구를 손글씨 '형태' 요구로 바꿈 (H3는 글자를 못 그림)")
    p.set_defaults(fn=cmd_sanitize)

    args = ap.parse_args(_mask_ids(sys.argv[1:]))
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
