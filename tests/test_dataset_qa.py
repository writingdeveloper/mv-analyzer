import csv

from mv_analyzer.dataset_qa import audit_dataset


def test_dataset_qa_detects_duplicate_id(tmp_path):
    p = tmp_path / "x.csv"
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["video_id", "group"])
        w.writeheader()
        w.writerow({"video_id": "same", "group": "top"})
        w.writerow({"video_id": "same", "group": "bottom"})
    out = audit_dataset(p, {"rows": 2, "cols": 2, "groups": {"top": 1, "bottom": 1}})
    assert any("unique" in e for e in out["errors"])


def test_dataset_qa_accepts_public_redaction_column_count(tmp_path):
    p=tmp_path/"x.csv"
    with p.open("w",encoding="utf-8",newline="") as fh:
        w=csv.DictWriter(fh,fieldnames=["video_id","group"]); w.writeheader(); w.writerow({"video_id":"a","group":"top"})
    out=audit_dataset(p,{"rows":1,"cols":(2,3),"groups":{"top":1}})
    assert out["errors"]==[]
