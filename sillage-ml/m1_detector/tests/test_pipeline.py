from __future__ import annotations

import json
from pathlib import Path
import os
import subprocess
import sys

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from sillage.pipeline import DetectionConfig, detect, load_and_clean, publish
from sillage.evaluation import evaluate
from sillage.api import app

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def demo_data(tmp_path):
    path = tmp_path / "demo.csv"
    rows = []
    from datetime import date, timedelta
    for country, weekstart in [("JP", 30), ("FR", 40)]:
        for i in range(72):
            value = 14.0
            if i >= weekstart:
                value += min((i-weekstart+1)*4, 45)
            rows.append({"ingredient": "matcha", "country": country, "date": (date(2024, 1, 1) + timedelta(weeks=i)).isoformat(),
                         "source": "synthetic_test", "metric": "attention", "value": str(value),
                         "normalization_scope": f"{country}_independent", "is_synthetic": "true", "source_url": ""})
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def test_clean_and_detect_order(demo_data):
    cleaned, report = load_and_clean(demo_data)
    assert report["n_clean"] == 144
    assert report["n_synthetic"] == 144
    features, signals, series = detect(cleaned, DetectionConfig())
    assert len(series) == 2
    onset = dict(zip(signals["country"], signals["date"]))
    assert onset["JP"] < onset["FR"]
    assert "robust_z" in features.columns
    assert series["status"].eq("ok").all()


def test_no_future_leakage(demo_data):
    clean, _ = load_and_clean(demo_data)
    cfg = DetectionConfig()
    early = clean.loc[clean["date"] <= "2024-10-20"].copy()
    features_early, _, _ = detect(early, cfg)
    features_full, _, _ = detect(clean, cfg)
    f = features_full.loc[features_full["date"] <= "2024-10-20"].reset_index(drop=True)
    pd.testing.assert_frame_equal(features_early.reset_index(drop=True), f)


def test_duplicate_conflict_rejected(demo_data):
    df = pd.read_csv(demo_data)
    copy = df.iloc[0].copy()
    copy["value"] = "999"
    df = pd.concat([df, pd.DataFrame([copy])], ignore_index=True)
    df.to_csv(demo_data, index=False)
    with pytest.raises(ValueError, match="conflictuelles"):
        load_and_clean(demo_data)


def test_invalid_date_dropped(demo_data):
    df = pd.read_csv(demo_data)
    df.loc[0, "date"] = "yesterday"
    df.to_csv(demo_data, index=False)
    clean, quality = load_and_clean(demo_data)
    assert quality["n_invalid_rows_dropped"] == 1
    assert len(clean) == 143


def test_irregular_series_marked_not_modeled(demo_data):
    clean, _ = load_and_clean(demo_data)
    bad = clean.loc[~((clean["country"] == "JP") & (clean["date"] == "2024-01-22"))].copy()
    _, signals, series = detect(bad, DetectionConfig())
    assert series.loc[series["country"] == "JP", "status"].iloc[0] == "irregular_frequency"
    assert not (signals["country"] == "JP").any()


def test_evaluation_and_api_use_published_artifacts(demo_data, tmp_path, monkeypatch):
    out = tmp_path / "published"
    manifest = publish(demo_data, out, DetectionConfig())
    assert manifest["contains_synthetic"] and not manifest["contains_real"]
    signals = json.loads((out / "signals.json").read_text(encoding="utf-8"))
    assert signals
    date_hit = next(s["date"] for s in signals if s["country"] == "JP")
    cleaned, _ = load_and_clean(demo_data)
    refs = pd.DataFrame([
        {"case_id": "1", "ingredient": "matcha", "country": "JP", "source": "synthetic_test", "metric": "attention", "normalization_scope": "JP_independent", "as_of_date": date_hit, "reference_label": "1", "rationale": "simulation positive", "source_url": ""},
        {"case_id": "2", "ingredient": "matcha", "country": "JP", "source": "synthetic_test", "metric": "attention", "normalization_scope": "JP_independent", "as_of_date": "2024-05-20", "reference_label": "0", "rationale": "simulation negative", "source_url": ""},
    ])
    score = evaluate(cleaned, refs, DetectionConfig())
    assert score["n_cases"] == 2
    assert score["confusion"]["TP"] == 1
    assert score["confusion"]["TN"] == 1
    assert score["warnings"]
    monkeypatch.setenv("SILLAGE_ARTIFACT_DIR", str(out))
    client = TestClient(app)
    assert client.get("/health").json()["status"] == "ready"
    model = client.get("/model").json()
    assert model["input_sha256"] == manifest["input_sha256"]
    api_signals = client.get("/signals", params={"country": "JP"}).json()
    assert api_signals["n_matching"] > 0
    assert all(r["country"] == "JP" and r["is_synthetic"] for r in api_signals["results"])
