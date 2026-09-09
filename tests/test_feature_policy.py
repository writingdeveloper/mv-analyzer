from mv_analyzer.feature_policy import audit_ok, audit_rows


def test_audit_rejects_missing_groups():
    out = audit_rows([{"group": "top", "duration_s": 10}] * 10)
    assert audit_ok(out) is False
    assert any("bottom" in e for e in out["errors"])


def test_experimental_columns_are_visible_but_not_errors():
    rows = []
    for group in ("top", "bottom"):
        for i in range(10):
            rows.append({"group": group, "duration_s": i + 1, "ext_color_change_mean": 0.1})
    out = audit_rows(rows)
    assert "ext_color_change_mean" in out["experimental_columns"]
    assert not any("ext_color" in e for e in out["errors"])
