from mv_analyzer import doctor


def test_doctor_default_does_not_touch_services(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("service access should not happen")
    monkeypatch.setattr(doctor.urllib.request, "urlopen", fail)
    rows = doctor.inspect_environment()
    assert not any(r["name"] == "ollama-api" for r in rows)
