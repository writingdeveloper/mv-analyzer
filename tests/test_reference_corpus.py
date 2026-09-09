from pathlib import Path

import pytest

from mv_analyzer.reference_corpus import (
    REFERENCE_CORPUS,
    load_reference_rows,
    reference_corpus_public_metadata,
)


ROOT = Path(__file__).resolve().parents[1]


def test_reference_corpus_identity_is_stable():
    assert REFERENCE_CORPUS["id"] == "extreme-reference-2026-07"
    assert REFERENCE_CORPUS["label"] == "Extreme Reference Corpus v2026.07"
    assert REFERENCE_CORPUS["sampling"] == "extreme-groups"
    assert REFERENCE_CORPUS["collected_at"] == "2026-07-21"
    assert REFERENCE_CORPUS["domains"] == ["vocaloid", "kpop"]


def test_reference_rows_are_tracked_csv_and_domain_filterable():
    all_rows = load_reference_rows(ROOT, "all")
    vocaloid = load_reference_rows(ROOT, "vocaloid")
    kpop = load_reference_rows(ROOT, "kpop")

    assert len(all_rows) == 100
    assert len(vocaloid) == 50
    assert len(kpop) == 50
    assert {row["domain"] for row in vocaloid} == {"vocaloid"}
    assert {row["domain"] for row in kpop} == {"kpop"}


def test_reference_rows_reject_unknown_domain():
    with pytest.raises(ValueError, match="benchmark domain"):
        load_reference_rows(ROOT, "rock")


def test_public_metadata_uses_filtered_row_count():
    rows = load_reference_rows(ROOT, "kpop")
    meta = reference_corpus_public_metadata(rows, "kpop")

    assert meta == {
        "id": "extreme-reference-2026-07",
        "label": "Extreme Reference Corpus v2026.07",
        "sampling": "extreme-groups",
        "domain": "kpop",
        "n": 50,
        "domains": ["vocaloid", "kpop"],
        "collected_at": "2026-07-21",
        "collection_start": "2026-07-16",
        "collection_end": "2026-07-21",
        "corpus_sha256": "c05386318567bd0536a962ff2649a971a8e332c9a15bbfb7e21127262b84503d",
    }


def test_corpus_hash_does_not_depend_on_checkout_line_endings(tmp_path):
    content=(ROOT/"dataset/features_100mv.csv").read_text(encoding="utf-8-sig")
    digests=[]
    for style,text in [("lf",content),("crlf",content.replace("\n","\r\n"))]:
        root=tmp_path/style
        (root/"dataset").mkdir(parents=True)
        (root/"dataset/features_100mv.csv").write_bytes(text.encode("utf-8"))
        rows=load_reference_rows(root)
        digests.append(reference_corpus_public_metadata(rows)["corpus_sha256"])
    assert digests[0]==digests[1]


def test_canonical_digest_normalizes_nested_multiline_strings():
    from mv_analyzer.reference_corpus import canonical_sha256
    assert canonical_sha256({"x":["first\r\nsecond"]})==canonical_sha256({"x":["first\nsecond"]})


def test_corpus_hash_ignores_non_analysis_thumbnail_ocr_text():
    from mv_analyzer.reference_corpus import analysis_sha256, canonical_sha256
    left={"video_id":"abc","scene_cuts_per_minute":12.0,"thumb_text_content":"copyright-like OCR A"}
    right={"video_id":"abc","scene_cuts_per_minute":12.0}
    assert analysis_sha256(left)==analysis_sha256(right)
    assert canonical_sha256(left)!=canonical_sha256(right)


def test_public_sanitized_csv_has_same_corpus_fingerprint(tmp_path):
    import csv
    source=ROOT/"dataset/features_100mv.csv"
    target_root=tmp_path/"sanitized"
    (target_root/"dataset").mkdir(parents=True)
    with source.open(encoding="utf-8-sig",newline="") as src, (target_root/"dataset/features_100mv.csv").open("w",encoding="utf-8",newline="") as dst:
        reader=csv.DictReader(src)
        fields=[f for f in reader.fieldnames if f!="thumb_text_content"]
        writer=csv.DictWriter(dst,fieldnames=fields); writer.writeheader()
        for row in reader:
            row.pop("thumb_text_content",None); writer.writerow(row)
    original=reference_corpus_public_metadata(load_reference_rows(ROOT))["corpus_sha256"]
    sanitized=reference_corpus_public_metadata(load_reference_rows(target_root))["corpus_sha256"]
    assert sanitized==original
