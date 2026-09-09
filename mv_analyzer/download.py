"""yt-dlp/ffmpeg 래퍼: 메타·영상·오디오·자막프레임·썸네일 확보."""
import datetime
import json
import os
import re
import shutil
import subprocess


def ytdlp_cmd():
    """yt-dlp 기본 커맨드. deno가 있으면 JS 런타임으로 지정 —
    런타임 없이 YouTube 추출 시 봇 판정 위험이 높아진다(배치 실측).
    YTDLP_EXTRA_ARGS 환경변수로 추가 인자 주입 가능 (예: 주간 배치 시
    "--limit-rate 4M" — 사용자 스트리밍 시청과 대역폭 공존)."""
    base = ["yt-dlp"]
    deno = shutil.which("deno") or os.path.expanduser(
        os.path.join("~", ".deno", "bin", "deno.exe"))
    if deno and os.path.exists(deno):
        base += ["--js-runtimes", f"deno:{deno}"]
    extra = os.environ.get("YTDLP_EXTRA_ARGS")
    if extra:
        base += extra.split()
    return base


def _run(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(f"{cmd[0]} 실패(rc={proc.returncode}): {proc.stderr[-500:]}")
    return proc.stdout


def fetch_meta(url):
    return json.loads(_run(ytdlp_cmd() + ["--dump-json", "--no-download", "--", url]))


def slim_meta(meta):
    """스펙 §6 기록 전용 컬럼 — 모집단 테이블/features 공용 스키마."""
    subs = meta.get("channel_follower_count")
    views_raw = meta.get("view_count")
    upload = meta.get("upload_date")  # "YYYYMMDD"
    weekday = (datetime.datetime.strptime(upload, "%Y%m%d").weekday()
               if upload else None)
    w, h = meta.get("width"), meta.get("height")
    ts = meta.get("timestamp")
    return {
        "video_id": meta["id"],
        "title": meta.get("title"),
        "channel": meta.get("channel"),
        "channel_id": meta.get("channel_id"),
        "subscriber_count": subs,
        "view_count": views_raw,
        "like_count": meta.get("like_count"),
        "comment_count": meta.get("comment_count"),
        "view_per_sub": round(views_raw / subs, 4)
        if subs and views_raw is not None else None,
        "like_per_view": round((meta.get("like_count") or 0) / views_raw, 4)
        if views_raw else None,
        "upload_date": upload,
        "upload_weekday": weekday,
        "duration_s": meta.get("duration"),
        "width": w, "height": h,
        "fps": meta.get("fps"),
        "aspect_ratio": round(w / h, 3) if w and h else None,
        "tags": meta.get("tags") or [],
        "categories": meta.get("categories") or [],
        "has_chapters": bool(meta.get("chapters")),
        "chapters": meta.get("chapters") or [],
        "has_nico_link": bool(re.search(r"nicovideo\.jp|nico\.ms",
                                        meta.get("description") or "")),
        "has_heatmap": bool(meta.get("heatmap")),
        "heatmap": meta.get("heatmap") or [],
        "was_premiere": meta.get("live_status") == "was_live"
        or bool(meta.get("release_timestamp")),
        "collected_at": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "upload_hour": datetime.datetime.fromtimestamp(ts).hour if ts else None,
    }


def download_video(url, out_path):
    _run(ytdlp_cmd() + ["-f", "bv*[height<=1080]+ba/b", "--remux-video", "mp4",
          "-o", out_path, "--", url])


def extract_audio(video_path, out_path):
    _run(["ffmpeg", "-y", "-i", video_path, "-vn", "-ac", "1", "-ar", "22050",
          out_path])


def extract_subframes(video_path, out_dir):
    """하단 30% 크롭 0.5fps → sub_%03d.jpg (파일럿 검증 파라미터)."""
    os.makedirs(out_dir, exist_ok=True)
    _run(["ffmpeg", "-y", "-i", video_path,
          "-vf", "fps=0.5,crop=iw:ih*0.3:0:ih*0.7",
          "-q:v", "3", os.path.join(out_dir, "sub_%03d.jpg")])
    return len([f for f in os.listdir(out_dir) if f.endswith(".jpg")])


def download_thumbnail(meta, out_path):
    """yt-dlp로 썸네일만 내려받아 jpg로 변환 저장 (--convert-thumbnails는 ffmpeg 사용)."""
    base, _ = os.path.splitext(out_path)
    _run(ytdlp_cmd() + ["--write-thumbnail", "--skip-download",
          "--convert-thumbnails", "jpg", "-o", base,
          "--", meta["webpage_url"]])
    if not os.path.exists(out_path):
        raise RuntimeError(f"썸네일 다운로드 실패: {out_path}")
