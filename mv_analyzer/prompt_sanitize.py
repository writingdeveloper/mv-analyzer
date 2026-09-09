"""레퍼런스 고유 요소를 걷어낸 '생성용' 비전 시맨틱스 변형.

`work/exports/<id>.vision.json`은 레퍼런스 MV의 키프레임을 직접 보고 쓴 서술이라
그 업로드본에만 있는 것들이 섞여 들어온다 — 팬자막 띠, 4:3 필러박스 검은 띠,
채널 워터마크, 화면에 새겨진 가사 텍스트. 레퍼런스를 *기술*할 때는 맞는 말이지만
그대로 H3에 넣으면 생성물에 자막 띠를 그리라는 지시가 된다.

원칙 셋:
- 업로드 산물(자막·필러박스·워터마크)은 절 단위로 걷어낸다. 문장 전체를 지우면
  같은 문장에 붙어 있던 진짜 연출("thick black outlines, flat cel colors …")까지 날아간다.
- 화면에 새겨진 글자도 걷어낸다. 판단 근거는 저작권이 아니라 실용 — 영상 생성 모델은
  글자를 제대로 못 그려서, 텍스트 지시는 대부분 뭉개진 획으로 돌아온다.
- 지운 자리에 "no subtitles" 같은 부정문을 넣지 않는다. 확산 모델에서 부정은 자주
  반대로 작동한다. 지우고 끝낸다.

지웠더니 필드가 비는 샷(예: 타이틀 카드처럼 피사체 자체가 글자인 경우)은 지우지 않고
`needs_rewrite`로 표시해 사람이 다시 쓰게 남긴다. 조용히 빈 필드를 내보내면
reference-lab에서 의미 커버리지만 떨어뜨린다.
"""
from __future__ import annotations

import json
import os
import re

ASPECTS = ("subject", "subject_motion", "scene", "spatial_framing", "camera", "visual_style")

# 절 하나가 통째로 업로드 산물일 때만 지운다. 부분 일치로 문장을 반토막 내지 않는다.
STRIP_RULES = (
    ("subtitle", r"\b(sub-?titles?|hardsubs?|fan-?subs?|caption\s*(band|bar|strip)|subs)\b"),
    ("burned_text", r"\b(lyrics?|karaoke|caption)\b.{0,24}\b(text|line|typography|overlay|type)\b"
                    r"|\b(text|typography|lettering|type)\b.{0,24}\b(overlay|burn(ed|t)-?in|on-?screen)\b"),
    ("pillarbox", r"\b(pillar-?box\w*|letter-?box\w*|black bars?)\b"),
    ("watermark", r"\bwatermark\b|\bchannel (logo|handle|name|tag)\b|(?<!\w)@[A-Za-z0-9_]{2,}"),
)

# 지우지는 않되 "이 샷은 글자에 기대고 있다"고 표시할 어휘 (타이틀 카드·엔드롤 등).
TEXT_DEPENDENT = re.compile(
    r"\b(title (card|logo)|logo|credits?|end-?roll text|lettering|hand-?lettered"
    r"|katakana|hiragana|kanji|hangul)\b", re.I)

MIN_KEPT_CHARS = 8  # 이보다 짧게 남으면 필드가 죽은 것으로 본다

# 글자 '내용'을 요구하는 표현을 글자 '형태'를 요구하는 표현으로 바꾼다 (--typography abstract).
# 지우지 않는 이유: 이 레퍼런스에서 타이포그래피는 장식이 아니라 연출이다 — 49샷 중 18샷이
# 화면 글자에 기대고 있어, 통째로 빼면 MV의 문법이 남지 않는다. 부정문("no text") 대신
# 긍정형 형태 서술로 바꾸는 건 확산 모델이 부정을 자주 뒤집기 때문이다.
TYPO_REWRITES = (
    (r"\bhand-?lettered\s+(Japanese|Korean|English)\s+"
     r"(?:words|text|typography|characters|lettering|type)\b",
     r"hand-lettered \1-style glyph shapes"),
    (r"\b(Japanese|Korean|English)\s+(?:hand-?lettered\s+)?"
     r"(?:words|text|typography|characters|lettering|type)\b",
     r"\1-style glyph shapes"),
    (r"\b(kanji|katakana|hiragana|hangul)\s+(?:characters|text|typography)\b",
     r"\1-like glyph shapes"),
    (r"\bend-?credit\s+(?:text|typography)\b",
     "end-credit-style columns of small glyph shapes"),
    (r"\bthe letters\s+[A-Z]\s+and\s+[A-Z]\b", "letter-like shapes"),
    (r"\b(?:lyric|caption)\s+(?:text|typography)\b", "glyph shapes"),
)


def abstract_typography(text):
    """읽히는 글자 요구 → 손글씨 '형태' 요구. 바뀐 문자열과 치환 횟수를 돌려준다."""
    if not isinstance(text, str) or not text.strip():
        return text, 0
    n = 0
    for pat, rep in TYPO_REWRITES:
        text, k = re.subn(pat, rep, text, flags=re.I)
        n += k
    return text, n


def _clauses(text):
    """절 단위 분해. 구분자를 절 끝에 붙여 두어 재조립 때 원문 리듬을 잃지 않는다."""
    out, buf = [], ""
    for ch in text:
        buf += ch
        if ch in ".;,":
            out.append(buf)
            buf = ""
    if buf.strip():
        out.append(buf)
    return out


def strip_field(text, rules=STRIP_RULES):
    """절 단위로 걷어낸 문자열과 (규칙명, 지운 절) 목록을 돌려준다."""
    if not isinstance(text, str) or not text.strip():
        return text, []
    kept, removed = [], []
    for cl in _clauses(text):
        hit = next((name for name, pat in rules if re.search(pat, cl, re.I)), None)
        if hit:
            removed.append((hit, cl.strip()))
        else:
            kept.append(cl)
    if not removed:
        return text, []
    s = "".join(kept).strip()
    s = re.sub(r"\s{2,}", " ", s)
    s = re.sub(r"^[\s,;.]+", "", s)
    s = re.sub(r"[\s,;]+$", "", s)
    if s and s[-1] not in ".!?":
        s += "."
    return s, removed


def sanitize_shot(shot, rules=STRIP_RULES, typography="keep"):
    out = dict(shot)
    removed, dead = [], []
    for key in ASPECTS:
        original = shot.get(key)
        cleaned, gone = strip_field(original, rules)
        if not gone:
            continue
        if len(cleaned.strip()) < MIN_KEPT_CHARS:
            # 필드가 통째로 산물이었다 — 지우면 샷이 사라지므로 원문을 남기고 표시만 한다
            dead.append(key)
            removed.extend({"field": key, "rule": r, "clause": c, "applied": False} for r, c in gone)
            continue
        out[key] = cleaned
        removed.extend({"field": key, "rule": r, "clause": c, "applied": True} for r, c in gone)
    audit = {"shot_number": shot.get("shot_number"), "removed": removed}
    if dead:
        audit["needs_rewrite"] = dead
    if typography == "abstract":
        n_typo = 0
        for key in ASPECTS:
            new_v, k = abstract_typography(out.get(key))
            if k:
                out[key] = new_v
                n_typo += k
        if n_typo:
            audit["typography_abstracted"] = n_typo

    text_clauses = []
    for key in ("subject", "scene", "visual_style"):
        for cl in _clauses(str(out.get(key) or "")):
            if TEXT_DEPENDENT.search(cl):
                text_clauses.append({"field": key, "clause": cl.strip()})
    if text_clauses:
        # 지우지 않는다 — 타이포그래피가 연출인 샷이 있어서다. 대신 "여기는 글자에
        # 기대고 있고 H3는 글자를 못 그린다"고 표시해 사람이 판단하게 남긴다.
        audit["text_dependent"] = text_clauses
    return out, audit


def sanitize(payload, rules=STRIP_RULES, typography="keep"):
    """비전 시맨틱스 payload → (생성용 payload, 감사 리포트)."""
    shots, audits = [], []
    for shot in payload.get("shots") or []:
        s, a = sanitize_shot(shot, rules, typography)
        shots.append(s)
        if a["removed"] or a.get("text_dependent") or a.get("typography_abstracted"):
            audits.append(a)
    by_rule = {}
    for a in audits:
        for r in a["removed"]:
            key = r["rule"]
            by_rule[key] = by_rule.get(key, 0) + (1 if r["applied"] else 0)
    report = {
        "n_shots": len(shots),
        "n_shots_changed": sum(1 for a in audits if any(r["applied"] for r in a["removed"])),
        "removed_by_rule": by_rule,
        "needs_rewrite": [a["shot_number"] for a in audits if a.get("needs_rewrite")],
        "text_dependent": [a["shot_number"] for a in audits if a.get("text_dependent")],
        "n_text_clauses": sum(len(a.get("text_dependent") or []) for a in audits),
        "typography": typography,
        "n_typography_abstracted": sum(a.get("typography_abstracted") or 0 for a in audits),
        "shots": audits,
    }
    out = {k: v for k, v in payload.items() if k != "shots"}
    out["shots"] = shots
    out["_sanitize"] = {k: v for k, v in report.items() if k != "shots"}
    return out, report


def sanitize_file(src, out_path=None, typography="keep"):
    with open(src, encoding="utf-8") as fh:
        payload = json.load(fh)
    if not isinstance(payload, dict) or not isinstance(payload.get("shots"), list):
        raise ValueError("비전 시맨틱스 JSON은 shots 배열을 가진 객체여야 합니다")
    clean, report = sanitize(payload, typography=typography)
    if out_path is None:
        base = re.sub(r"\.vision\.json$|\.json$", "", src)
        out_path = f"{base}.gen.json"
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(clean, fh, ensure_ascii=False, indent=2)
    return out_path, report
