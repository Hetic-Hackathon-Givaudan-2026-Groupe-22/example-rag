"""Invariants essentiels de la comparaison 3 candidats M2."""
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from sillage_v2.compare_models import (
    MODEL_NAMES, candidate, verify_features, looto, measure,
)
from sillage_v2.features import FEATURE_COLUMNS

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ROOT / 'artifacts/v2_pistache_PROVISOIRE/features_by_topic.csv'


def test_three_models_present():
    assert set(MODEL_NAMES) == {'Logistic Regression','Random Forest','XGBoost'}
    for name in MODEL_NAMES:
        assert hasattr(candidate(name), 'predict_proba')


def test_30_distinct_topics_and_two_classes():
    data = verify_features(pd.read_csv(FEATURES), expected_topics=30)
    assert len(data) == 30
    assert data.topic_id.nunique() == 30
    assert (data.label.value_counts().sort_index().to_dict()) == {0: 15, 1: 15}
    assert 'pistachio' in data.topic_id.tolist()


def test_topic_duplicate_rejected():
    data = pd.read_csv(FEATURES)
    bad = pd.concat([data, data.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match='plusieurs lignes'):
        verify_features(bad, expected_topics=31)


def test_no_label_inside_features_and_finite_values():
    data = pd.read_csv(FEATURES)
    assert 'label' not in FEATURE_COLUMNS
    assert 'topic_id' not in FEATURE_COLUMNS
    assert np.isfinite(data[FEATURE_COLUMNS].to_numpy(float)).all()


def test_models_produce_complete_out_of_fold_predictions():
    data = verify_features(pd.read_csv(FEATURES), expected_topics=30)
    for name in MODEL_NAMES:
        preds = looto(data, name)
        assert len(preds) == 30
        assert preds.topic_id.nunique() == 30
        assert preds.score_tendance_non_calibre.between(0,1).all()
        result = measure(preds)
        assert sum(result['confusion_buzz_tendance'].values()) == 30


def test_model_comparison_published_files():
    out=ROOT/'artifacts/comparison_v2'
    if not (out/'metrics_v2.json').exists():
        pytest.skip('Comparer les modèles avant le contrôle des artefacts')
    import json
    payload=json.loads((out/'metrics_v2.json').read_text(encoding='utf-8'))
    assert payload['food_cases_evaluated']==30
    assert set(payload['comparison'])==set(MODEL_NAMES)
    pred=pd.read_csv(out/'comparaison_par_sujet.csv')
    assert len(pred)==30 and pred.topic_id.nunique()==30
