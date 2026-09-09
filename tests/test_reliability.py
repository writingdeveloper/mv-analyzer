from mv_analyzer.reliability import score_predictions


def test_score_predictions_perfect():
    labels = [
        {"i": 0, "mood": "dark", "shot_type": "wide", "style": "anime", "num_characters": 1},
        {"i": 1, "mood": "calm", "shot_type": "closeup", "style": "3dcg", "num_characters": 2},
    ]
    out = score_predictions(labels, labels)
    assert out["n"] == 2
    assert out["categorical"]["mood"]["accuracy"] == 1.0
    assert out["categorical"]["style"]["kappa"] == 1.0
    assert out["num_characters"]["exact"] == 1.0


def test_score_predictions_uses_explicit_indices():
    labels = [{"i": 4, "mood": "dark", "shot_type": "wide", "style": "anime", "num_characters": 1}]
    preds = [{"i": 4, "mood": "calm", "shot_type": "wide", "style": "anime", "num_characters": 2}]
    out = score_predictions(preds, labels)
    assert out["n"] == 1
    assert out["categorical"]["mood"]["accuracy"] == 0.0
    assert out["num_characters"]["within1"] == 1.0
