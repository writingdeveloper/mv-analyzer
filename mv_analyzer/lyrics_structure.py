"""가사 구조 지표 — 반복성·훅 배치·컷-가사 정렬. 전부 결정론적.

입력은 lyrics_lines.json의 lines: [{"t_s": int, "line": str}].
스펙: docs/superpowers/specs/2026-07-21-paper-dataset-design.md
"""
import re
import zlib

MIN_LINES = 8          # 추출 실패 케이스 제외 (스펙)
_CHORUS_MIN_CHARS = 5  # 후렴 후보 라인의 정규화 최소 길이
_BRACKETS = re.compile(r"[\(\[【「『《〈].*?[\)\]】」』》〉]")
_MARKERS = re.compile(
    r"(official\s*)?(music\s*video|m/?v)|feat\.?\s*\S*|prod\.?\s*\S*",
    re.IGNORECASE)
_SEPARATORS = re.compile(r"[/|\-–—:·]+")


def normalize(text):
    """공백·기호 제거 + 소문자화 — 반복 판정과 부분 문자열 매칭용."""
    return re.sub(r"[\W_]+", "", text, flags=re.UNICODE).lower()


def compression_ratio(lines):
    """zlib(level 9) 압축 후/전 바이트 비율. 낮을수록 반복적."""
    raw = "\n".join(l["line"] for l in lines).encode("utf-8")
    if not raw:
        return None
    return round(len(zlib.compress(raw, 9)) / len(raw), 4)


def song_title_phrase(title, channel):
    """제목에서 괄호 구간·MV/feat 표기·아티스트(채널명) 토큰을 제거한
    곡명 어구를 정규화 문자열로 반환. 후보가 없으면 ""."""
    t = _MARKERS.sub(" ", _BRACKETS.sub(" ", title))
    parts = [p.strip() for p in _SEPARATORS.split(t) if normalize(p)]
    if not parts:
        return ""
    ch = normalize(channel)
    cands = [p for p in parts
             if ch and normalize(p) not in ch and ch not in normalize(p)]
    if cands:
        return normalize(max(cands, key=lambda p: len(normalize(p))))
    # 구분자가 없어 채널명과 곡명이 한 덩어리로 붙어있는 경우: 폴백으로
    # 오염된 어구를 그대로 반환하지 않고, 정규화된 채널명 부분 문자열을
    # 제거한다. 제거 후 2자 미만이면 유효한 후보가 없는 것으로 본다.
    norm = normalize(max(parts, key=lambda p: len(normalize(p))))
    if ch:
        norm = norm.replace(ch, "")
    return norm if len(norm) >= 2 else ""


def title_in_lyrics(phrase, lines):
    """(첫 등장 t_s | None, 등장 라인 수). 어구 2자 미만이면 (None, 0)."""
    if len(phrase) < 2:
        return None, 0
    first, count = None, 0
    for l in lines:
        if phrase in normalize(l["line"]):
            count += 1
            if first is None:
                first = l["t_s"]
    return first, count


def first_chorus_s(lines):
    """정규화 라인(≥5자)이 처음 재등장하는 시각 — 후렴 도달 프록시."""
    seen = set()
    for l in lines:
        key = normalize(l["line"])
        if len(key) < _CHORUS_MIN_CHARS:
            continue
        if key in seen:
            return l["t_s"]
        seen.add(key)
    return None


def cut_on_line_ratio(cut_times, line_times, tol_s=0.5):
    """컷 중 가사 라인 시작 ±tol_s 안에 떨어지는 비율."""
    if not cut_times or not line_times:
        return None
    hit = sum(1 for c in cut_times if any(abs(c - t) <= tol_s for t in line_times))
    return round(hit / len(cut_times), 4)


def structure_features(lines, cut_times, title, channel):
    """가사 구조 feature dict. 라인 수 < MIN_LINES면 None."""
    if len(lines) < MIN_LINES:
        return None
    phrase = song_title_phrase(title, channel)
    t_first, t_count = title_in_lyrics(phrase, lines)
    return {
        "lyrics_compression_ratio": compression_ratio(lines),
        "lyrics_title_first_s": t_first,
        "lyrics_title_count": t_count,
        "lyrics_first_chorus_s": first_chorus_s(lines),
        "sync_cut_on_line_ratio": cut_on_line_ratio(
            cut_times, [l["t_s"] for l in lines]),
    }
