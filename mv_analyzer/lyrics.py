"""하드자막 OCR 결과 → 가사 라인 정리 (일본어/한국어 필터) + 가사 feature."""
import re

PATTERNS = {
    "ko": r"[가-힣]",
    # 히라가나 + 가타카나 + CJK 한자 + 장음부호
    "ja": r"[ぁ-んァ-ヶ一-龯ー]",
}
LATIN_PATTERN = r"[A-Za-z]"
MIN_RATIO = 0.3
MIN_LEN = 2
# OCR 텍스트 검출 프레임 비율이 이 값 미만이면 하드자막 없음으로 판정.
# 판정 시 가사 파생 전체를 비운다 — 환각 노이즈가 가사로 오염되는 것 차단.
HARDSUB_MIN_RATIO = 0.1


def char_ratio(s, lang):
    """문자열 중 해당 언어 문자 비율 (0.0~1.0)."""
    return len(re.findall(PATTERNS[lang], s)) / max(len(s), 1)


# VLM이 붙이는 언어 라벨 접두("일본어: ...") — 가사 아님, 제거
_LANG_LABEL = re.compile(r"^\s*(일본어|한국어|japanese|korean)\s*[:：]\s*", re.I)


def clean_lyrics(ocr_items, lang="ja"):
    """OCR 항목들에서 가사 라인만 추출: 언어비율 필터 + 연속 중복 제거."""
    lines, prev = [], None
    for item in ocr_items:
        for ln in item["text"].splitlines():
            ln = _LANG_LABEL.sub("", ln.strip()).strip()
            if len(ln) < MIN_LEN or char_ratio(ln, lang) < MIN_RATIO:
                continue
            if ln != prev:
                lines.append({"t_s": item["t_s"], "line": ln})
                prev = ln
    return lines


def _native_or_latin_ratio(s, lang):
    """(자국어 문자 + 라틴 문자) 비율. K-pop/보컬로이드 모두 영어 가사가 실가사이므로
    ASR 경로에서는 라틴 문자도 자국어와 동등하게 취급한다 (OCR 경로는 그대로 자국어만)."""
    hits = len(re.findall(PATTERNS[lang], s)) + len(re.findall(LATIN_PATTERN, s))
    return hits / max(len(s), 1)


def asr_to_lines(segments, lang="ja"):
    """ASR 세그먼트 → 가사 라인.

    필터: (자국어+라틴) 문자비율 < MIN_RATIO 이면 제거 — 무성 구간의 기호/의성어만
    아닌 순수 잡음 오인식을 걸러낸다. 언어문자비율 자체로 sung English를 걸러내지
    않는다(과거 버그: 실가사인 영어 라인이 대량 탈락했음).
    연속 중복 세그먼트는 접는다 — 반복 환각(같은 구절 연속 오인식) 방어. 비연속
    반복(후렴 재등장)은 실데이터이므로 보존한다.
    """
    lines, prev = [], None
    for seg in segments:
        t = (seg.get("text") or "").strip()
        if len(t) < MIN_LEN or _native_or_latin_ratio(t, lang) < MIN_RATIO:
            continue
        if t != prev:
            lines.append({"t_s": int(seg["start"]), "line": t})
            prev = t
    return lines


def lyrics_features(lines, duration_s):
    return {
        "n_lyric_lines": len(lines),
        "first_lyric_at_s": lines[0]["t_s"] if lines else None,
        "lyric_lines_per_min": round(len(lines) / (duration_s / 60), 1)
        if duration_s else 0.0,
    }
