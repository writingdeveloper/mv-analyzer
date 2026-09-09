"""data/* 산출물을 DuckDB로 인덱싱하는 읽기 최적화 계층."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .extensions import derived_features

VIDEO_ID_RE = re.compile(r"[A-Za-z0-9_-]{11}")


def _load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_index(data_dir="data", db_path="work/mv_analyzer.duckdb"):
    import duckdb
    from .index_freshness import clear_meta, source_signature, write_meta

    source_before = source_signature(data_dir)
    clear_meta(db_path)

    root = Path(data_dir)
    features = []
    lyrics = []
    scenes = []
    for d in sorted(root.iterdir()) if root.exists() else []:
        if not d.is_dir() or not VIDEO_ID_RE.fullmatch(d.name):
            continue
        f = _load(d / "features.json")
        lyr = _load(d / "lyrics_lines.json") or {}
        sc_obj = _load(d / "scenes.json") or {}
        if isinstance(f, dict):
            f.update(derived_features(f, sc_obj, lyr))
            f["_data_dir"] = str(d)
            features.append(f)
        for line in lyr.get("lines") or []:
            lyrics.append({"video_id": d.name, "t_s": line.get("t_s"), "line": line.get("line")})
        tags = _load(d / "scene_tags.json") or []
        for i, sc in enumerate(sc_obj.get("scenes") or []):
            tg = tags[i] if i < len(tags) and isinstance(tags[i], dict) else {}
            scenes.append({
                "video_id": d.name,
                "scene": sc.get("scene"),
                "start_s": sc.get("start_s"),
                "end_s": sc.get("end_s"),
                "setting": tg.get("setting"),
                "mood": tg.get("mood"),
                "style": tg.get("style"),
                "shot_type": tg.get("shot_type"),
                "visual_elements": json.dumps(tg.get("visual_elements") or [], ensure_ascii=False),
            })

    out = Path(db_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    temp_paths = {
        "features": out.with_suffix(".features.index.jsonl"),
        "lyrics": out.with_suffix(".lyrics.index.jsonl"),
        "scenes": out.with_suffix(".scenes.index.jsonl"),
    }
    for key, rows in [("features", features), ("lyrics", lyrics), ("scenes", scenes)]:
        if rows:
            _write_jsonl(temp_paths[key], rows)

    con = duckdb.connect(str(out))
    try:
        con.execute("DROP TABLE IF EXISTS features")
        con.execute("DROP TABLE IF EXISTS lyrics")
        con.execute("DROP TABLE IF EXISTS scenes")
        if features:
            con.execute("CREATE TABLE features AS SELECT * FROM read_json_auto(?)", [str(temp_paths["features"])])
            con.execute("CREATE INDEX idx_video_id ON features(video_id)")
        else:
            con.execute("CREATE TABLE features(video_id VARCHAR, title VARCHAR, channel VARCHAR)")
        if lyrics:
            con.execute("CREATE TABLE lyrics AS SELECT * FROM read_json_auto(?)", [str(temp_paths["lyrics"])])
            con.execute("CREATE INDEX idx_lyrics_video ON lyrics(video_id)")
        else:
            con.execute("CREATE TABLE lyrics(video_id VARCHAR, t_s DOUBLE, line VARCHAR)")
        if scenes:
            con.execute("CREATE TABLE scenes AS SELECT * FROM read_json_auto(?)", [str(temp_paths["scenes"])])
            con.execute("CREATE INDEX idx_scenes_video ON scenes(video_id)")
        else:
            con.execute("""CREATE TABLE scenes(
                video_id VARCHAR, scene INTEGER, start_s DOUBLE, end_s DOUBLE,
                setting VARCHAR, mood VARCHAR, style VARCHAR, shot_type VARCHAR,
                visual_elements VARCHAR)""")
    finally:
        con.close()
        for path in temp_paths.values():
            path.unlink(missing_ok=True)
    source_after = source_signature(data_dir)
    if source_before == source_after:
        write_meta(data_dir, db_path, source_after)
    return {"features": len(features), "lyrics": len(lyrics), "scenes": len(scenes)}


def search_index(query, db_path="work/mv_analyzer.duckdb", limit=50):
    import duckdb

    p = Path(db_path)
    if not p.exists():
        return []
    pat = f"%{query}%"
    con = duckdb.connect(str(p), read_only=True)
    try:
        rows = con.execute(
            """
            SELECT * FROM (
                SELECT f.video_id, f.title, NULL::DOUBLE AS t_s, 'title' AS where_,
                       coalesce(f.title, '') || ' ' || coalesce(f.channel, '') AS text
                FROM features f
                WHERE coalesce(f.title, '') ILIKE ? OR coalesce(f.channel, '') ILIKE ?
                UNION ALL
                SELECT l.video_id, f.title, l.t_s, 'lyric' AS where_, l.line AS text
                FROM lyrics l LEFT JOIN features f USING(video_id)
                WHERE coalesce(l.line, '') ILIKE ?
                UNION ALL
                SELECT s.video_id, f.title, s.start_s, 'scene' AS where_,
                       concat_ws(' ', s.setting, s.mood, s.style, s.shot_type, s.visual_elements) AS text
                FROM scenes s LEFT JOIN features f USING(video_id)
                WHERE concat_ws(' ', s.setting, s.mood, s.style, s.shot_type, s.visual_elements) ILIKE ?
            ) q
            ORDER BY video_id, t_s NULLS FIRST
            LIMIT ?
            """,
            [pat, pat, pat, pat, limit],
        ).fetchall()
    finally:
        con.close()
    return [
        {"video_id": r[0], "title": r[1], "t_s": r[2], "where": r[3], "text": r[4]}
        for r in rows
    ]
