import json

from mv_analyzer.captions import scan_corpus, summarize_scan, summarize_tracks


def test_summarize_tracks_filters_live_chat_and_detects_original_language():
    info = {"subtitles": {"ko": [], "en-US": [], "live_chat": []},
            "automatic_captions": {"ja": [], "live_chat": []}}
    out = summarize_tracks(info, lyrics_lang="ja")
    assert out["manual_langs"] == ["en-US", "ko"]
    assert out["n_manual"] == 2
    assert out["has_original_lang_track"] is False   # ja는 자동 자막에만 있음
    assert out["auto_has_original_lang"] is True
    assert summarize_tracks(info, lyrics_lang="ko")["has_original_lang_track"] is True


def test_summarize_tracks_without_lyrics_lang():
    out = summarize_tracks({"subtitles": {}}, lyrics_lang=None)
    assert out["has_original_lang_track"] is False
    assert out["has_auto"] is False


def _corpus(tmp_path, spec):
    for vid, (lang, source) in spec.items():
        d = tmp_path / vid
        d.mkdir()
        (d / "features.json").write_text(json.dumps(
            {"title": vid, "lyrics_lang": lang, "lyrics_source": source}), encoding="utf-8")


def test_scan_corpus_is_resumable_and_summarizes(tmp_path):
    _corpus(tmp_path, {"aaaaaaaaaaa": ("ja", "asr"), "bbbbbbbbbbb": ("ko", None),
                       "ccccccccccc": ("ja", "ocr")})
    tracks = {"aaaaaaaaaaa": {"subtitles": {"ja": [], "en": []}},
              "bbbbbbbbbbb": {"subtitles": {"ko": []}},
              "ccccccccccc": {"subtitles": {}}}
    calls = []

    def fake_fetch(vid, sleep_s=0.0):
        calls.append(vid)
        return tracks[vid]

    out = tmp_path / "scan.jsonl"
    r1 = scan_corpus(tmp_path, out, fetch=fake_fetch, sleep_s=0)
    assert r1["scanned"] == 3 and r1["failed"] == 0
    r2 = scan_corpus(tmp_path, out, fetch=fake_fetch, sleep_s=0)
    assert r2["scanned"] == 0 and r2["skipped"] == 3
    assert len(calls) == 3

    rows = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines()]
    s = summarize_scan(rows)
    assert s["n"] == 3
    assert s["with_original_lang_track"] == 2
    assert s["asr_upgradable"] == ["aaaaaaaaaaa"]
    assert s["missing_lyrics_recoverable"] == ["bbbbbbbbbbb"]
    assert s["by_lyrics_source"]["ocr"] == {"n": 1, "with_original_track": 0}


def test_scan_corpus_records_fetch_failures(tmp_path):
    _corpus(tmp_path, {"ddddddddddd": ("ja", "ocr")})

    def boom(vid, sleep_s=0.0):
        raise RuntimeError("network down")

    out = tmp_path / "scan.jsonl"
    r = scan_corpus(tmp_path, out, fetch=boom, sleep_s=0)
    assert r["failed"] == 1
    row = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
    assert "network down" in row["error"]
    assert summarize_scan([row])["n"] == 0
