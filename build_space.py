"""MV Space — 3D feature 공간 시각화 데이터 빌더.

각 영상: 미니 썸네일(base64) + 핵심 3축 좌표 + PCA 3좌표 + 메타.
출력: docs/reports/mv-space.html (three.js 인라인 템플릿에 주입)
usage: python build_space.py
"""
import base64
import csv
import json
import os
import subprocess
import tempfile

import numpy as np

AXIS_FEATURES = ["scene_cuts_per_minute", "tag_avg_characters",
                 "scene_avg_saturation"]
PCA_FEATURES = ["scene_cuts_per_minute", "scene_median_shot_len_s",
                "scene_num_scenes", "sync_beats_per_cut",
                "hook_cuts_first_15s", "scene_min_shot_len_s",
                "tag_avg_characters", "scene_avg_saturation",
                "scene_max_shot_len_s", "scene_avg_shot_len_s",
                "lyrics_compression_ratio"]


def merge_extra(rows, workdir):
    """신규 분석 jsonl(video_id 키)을 features 행에 병합."""
    extra = {}
    for name in ("lyrics_structure", "heatmap_features"):
        p = f"{workdir}/{name}.jsonl"
        if os.path.exists(p):
            for l in open(p, encoding="utf-8"):
                r = json.loads(l)
                extra.setdefault(r["video_id"], {}).update(r)
    for row in rows:
        for k, v in extra.get(row["video_id"], {}).items():
            row.setdefault(k, v)
    return rows


def load_domain(name, table=None, sample=None, workdir=None):
    rows = []
    if table and os.path.exists(table):
        for l in open(table, encoding="utf-8"):
            r = json.loads(l)
            r["domain"] = name
            rows.append(r)
    elif sample and os.path.exists(sample):
        for s in csv.DictReader(open(sample, encoding="utf-8")):
            p = f"data/{s['video_id']}/features.json"
            if os.path.exists(p):
                with open(p, encoding="utf-8") as f:
                    r = json.load(f)
                r["group"] = s["group"]
                r["domain"] = name
                rows.append(r)
    if workdir:
        rows = merge_extra(rows, workdir)
    return rows


def mini_thumb_b64(video_id, tmp):
    src = f"data/{video_id}/thumbnail.jpg"
    if not os.path.exists(src):
        return None
    dst = os.path.join(tmp, f"{video_id}.jpg")
    r = subprocess.run(["ffmpeg", "-y", "-i", src, "-vf", "scale=96:54",
                       "-q:v", "6", dst], capture_output=True)
    if r.returncode != 0 or not os.path.exists(dst):
        return None
    return base64.b64encode(open(dst, "rb").read()).decode()


def main():
    rows = (load_domain("vocaloid", table="work/features_table.jsonl", workdir="work")
            + load_domain("kpop", sample="work/kpop/sample.csv", workdir="work/kpop"))
    # PCA (결합 표준화 공간 — 도메인 간 비교 가능)
    # 결측값은 열 중앙값으로 대치(신규 지표는 일부 표본만 보유)
    mat = np.array([[r.get(f) if r.get(f) is not None else np.nan
                     for f in PCA_FEATURES] for r in rows], dtype=float)
    col_med = np.nanmedian(mat, axis=0)
    idx = np.where(np.isnan(mat))
    mat[idx] = np.take(col_med, idx[1])
    ok = rows
    X = mat
    Xz = (X - X.mean(0)) / (X.std(0) + 1e-9)
    U, S, Vt = np.linalg.svd(Xz, full_matrices=False)
    pcs = U[:, :3] * S[:3]
    pcs = pcs / (np.abs(pcs).max(0) + 1e-9)  # [-1,1] 정규화
    var_ratio = (S ** 2 / (S ** 2).sum())[:3]
    pca_map = {r["video_id"]: pcs[i].tolist() for i, r in enumerate(ok)}

    # 핵심 3축 정규화 좌표
    ax_vals = {f: np.array([r.get(f) for r in rows], dtype=float)
               for f in AXIS_FEATURES}
    lo = {f: np.nanpercentile(v, 2) for f, v in ax_vals.items()}
    hi = {f: np.nanpercentile(v, 98) for f, v in ax_vals.items()}

    items = []
    with tempfile.TemporaryDirectory() as tmp:
        for r in rows:
            axis = []
            for f in AXIS_FEATURES:
                v = r.get(f)
                axis.append(None if v is None else round(
                    float(np.clip((v - lo[f]) / (hi[f] - lo[f] + 1e-9), 0, 1))
                    * 2 - 1, 3))
            items.append({
                "id": r["video_id"], "title": r.get("title"),
                "channel": r.get("channel"), "group": r["group"],
                "domain": r["domain"],
                "views": r.get("view_count"), "ratio": r.get("view_per_sub"),
                "axis": axis,
                "pca": [round(x, 3) for x in pca_map.get(r["video_id"], [])] or None,
                "raw": {f: r.get(f) for f in AXIS_FEATURES},
                "thumb": mini_thumb_b64(r["video_id"], tmp),
            })

    data = {
        "items": items,
        "axisLabels": ["분당 컷 수", "평균 등장인물", "화면 채도"],
        "pcaVar": [round(float(v) * 100, 1) for v in var_ratio],
    }
    with open("docs/reports/mv-space_template.html", encoding="utf-8") as f:
        html = f.read()
    three = open("docs/reports/vendor/three.min.js", encoding="utf-8").read()
    html = html.replace("/*__THREE__*/", three)
    html = html.replace("/*__DATA__*/",
                        "const DATA = " + json.dumps(data, ensure_ascii=False) + ";")
    with open("docs/reports/mv-space.html", "w", encoding="utf-8") as f:
        f.write(html)
    n_thumb = sum(1 for i in items if i["thumb"])
    print(f"items {len(items)} (thumb {n_thumb}) · PCA 설명분산 {data['pcaVar']}"
          f" · {os.path.getsize('docs/reports/mv-space.html') // 1024}KB")


if __name__ == "__main__":
    main()
