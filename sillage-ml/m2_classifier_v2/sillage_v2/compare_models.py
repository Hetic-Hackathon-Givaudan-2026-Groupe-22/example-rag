"""Comparaison reproductible M2 / modèles préspécifiés, LOOTO au niveau sujet.

Ceci compare des signatures *rétrospectives* : utiliser avec précaution.
Ne pas présenter le résultat comme une prédiction pré-pic.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
import sklearn
from joblib import dump
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, brier_score_loss,
    confusion_matrix, f1_score, precision_recall_fscore_support, roc_auc_score,
)
from sklearn.model_selection import LeaveOneOut
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier
import xgboost

from sillage_v2.features import FEATURE_COLUMNS, FeaturePolicy, extract_features

SEED = 42
VERSION = "2.1.0-comparison-experimental"
MODEL_NAMES = ("Logistic Regression", "Random Forest", "XGBoost")


def candidate(name: str):
    """Hyperparamètres fixes et déclarés dans le code AVANT comparaison."""
    if name == "Logistic Regression":
        return Pipeline([
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(
                C=0.3, class_weight="balanced", max_iter=2000, random_state=SEED)),
        ])
    if name == "Random Forest":
        return RandomForestClassifier(
            n_estimators=200, max_depth=3, min_samples_leaf=2,
            class_weight="balanced", random_state=SEED, n_jobs=1,
        )
    if name == "XGBoost":
        return XGBClassifier(
            n_estimators=80, max_depth=2, learning_rate=0.05,
            subsample=1.0, colsample_bytree=1.0, reg_lambda=2.0,
            objective="binary:logistic", eval_metric="logloss",
            random_state=SEED, n_jobs=1, tree_method="hist",
        )
    raise ValueError(f"Modèle inconnu: {name}")


def verify_features(df: pd.DataFrame, *, expected_topics: int) -> pd.DataFrame:
    required = {"topic_id", "label", *FEATURE_COLUMNS}
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Colonnes manquantes: {missing}")
    if len(df) != expected_topics:
        raise ValueError(f"Attendu {expected_topics} sujets, reçu {len(df)}")
    if df.topic_id.duplicated().any():
        raise ValueError("Fuite potentielle: plusieurs lignes pour un même sujet")
    if df.label.isna().any() or not df.label.isin([0, 1]).all():
        raise ValueError("Labels invalides")
    if df.label.nunique() != 2:
        raise ValueError("Il faut les deux classes")
    if not np.isfinite(df[FEATURE_COLUMNS].to_numpy(dtype=float)).all():
        raise ValueError("Features non finies")
    if "oud" in df.topic_id.values:
        raise ValueError("Oud hors du périmètre alimentaire")
    return df.sort_values("topic_id").reset_index(drop=True)


def looto(df: pd.DataFrame, model_name: str) -> pd.DataFrame:
    d = df.reset_index(drop=True)
    x = d[FEATURE_COLUMNS].to_numpy(float)
    y = d.label.to_numpy(int)
    pred, prob = np.zeros(len(d), dtype=int), np.zeros(len(d), dtype=float)
    for train_idx, test_idx in LeaveOneOut().split(x):
        # Le sujet évalué ne figure PAS dans l'ensemble d'entraînement.
        assert not set(d.topic_id.iloc[train_idx]).intersection(d.topic_id.iloc[test_idx])
        model = candidate(model_name)
        model.fit(x[train_idx], y[train_idx])
        pred[test_idx] = model.predict(x[test_idx])
        prob[test_idx] = model.predict_proba(x[test_idx])[:, 1]
    return pd.DataFrame({
        "topic_id": d.topic_id, "label_reference": np.where(y == 1, "tendance", "buzz"),
        "prediction_oof": np.where(pred == 1, "tendance", "buzz"),
        "score_tendance_non_calibre": prob,
        "correct_oof": pred == y,
        "fold": "leave_one_topic_out",
        "label_verifie_independamment": False,
    })


def measure(predictions: pd.DataFrame) -> dict:
    y = (predictions.label_reference == "tendance").to_numpy(int)
    p = (predictions.prediction_oof == "tendance").to_numpy(int)
    prob = predictions.score_tendance_non_calibre.to_numpy(float)
    prs, rcs, fs, _ = precision_recall_fscore_support(
        y, p, labels=[0, 1], zero_division=0)
    cm = confusion_matrix(y, p, labels=[0, 1])
    return {
        "n_cases": int(len(y)), "correct": int((y == p).sum()),
        "accuracy": float(accuracy_score(y, p)),
        "balanced_accuracy": float(balanced_accuracy_score(y, p)),
        "f1_macro": float(f1_score(y, p, average="macro", zero_division=0)),
        "precision_buzz": float(prs[0]), "recall_buzz": float(rcs[0]),
        "precision_tendance": float(prs[1]), "recall_tendance": float(rcs[1]),
        "roc_auc": float(roc_auc_score(y, prob)),
        "brier_score": float(brier_score_loss(y, prob)),
        "confusion_buzz_tendance": {
            "TN": int(cm[0, 0]), "FP": int(cm[0, 1]),
            "FN": int(cm[1, 0]), "TP": int(cm[1, 1]),
        },
        "errors": predictions.loc[~predictions.correct_oof, "topic_id"].tolist(),
    }


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare(input_path: Path, out: Path) -> dict:
    raw = pd.read_csv(input_path, encoding="utf-8-sig", low_memory=False)
    # Drapeau min_zones=1 pour conserver le cas faible couverture du référentiel historique.
    features, audit = extract_features(raw, FeaturePolicy(min_zones=1))
    features = verify_features(features, expected_topics=30)
    if len(audit) != 30:
        raise ValueError("Le référentiel source ne comporte pas 30 sujets")
    if "pistachio" not in features.topic_id.values:
        raise ValueError("Pistache provisoire manquante")
    if len(features) != 30 or set(features.topic_id) != set(audit.topic_id):
        raise ValueError("Audit et caractéristiques incohérents")

    out.mkdir(parents=True, exist_ok=True)
    features.to_csv(out / "features_by_topic.csv", index=False)
    audit.to_csv(out / "audit_30_references.csv", index=False)
    results = {}
    per_case = None
    for name in MODEL_NAMES:
        preds = looto(features, name)
        metrics = measure(preds)
        results[name] = metrics
        # Sous-table par sujet pour inspection et audit reproductible.
        preds.rename(columns={
            "prediction_oof": f"prediction_{name.lower().replace(' ', '_')}",
            "score_tendance_non_calibre": f"score_{name.lower().replace(' ', '_')}",
            "correct_oof": f"correct_{name.lower().replace(' ', '_')}",
        })[["topic_id", f"prediction_{name.lower().replace(' ', '_')}",
            f"score_{name.lower().replace(' ', '_')}",
            f"correct_{name.lower().replace(' ', '_')}"]].to_csv(
                out / ("predictions_" + name.lower().replace(" ", "_") + ".csv"), index=False)
        if per_case is None:
            per_case = preds[["topic_id", "label_reference"]].copy()
        label = name.lower().replace(" ", "_")
        per_case = per_case.merge(pd.DataFrame({
            "topic_id": preds.topic_id,
            "prediction_" + label: preds.prediction_oof,
            "correct_" + label: preds.correct_oof,
        }), on="topic_id", validate="one_to_one")

    per_case.to_csv(out / "comparaison_par_sujet.csv", index=False)
    # Sélection technique : F1 macro LOOTO, puis préférence au plus simple en cas d'égalité.
    # Ceci n'est PAS une sélection validée sur un test indépendant.
    winner = max(MODEL_NAMES, key=lambda n: (results[n]["f1_macro"], -MODEL_NAMES.index(n)))
    reduced = features.loc[features.topic_id != "pistachio"].reset_index(drop=True)
    sensitivity = {name: measure(looto(reduced, name)) for name in MODEL_NAMES}

    # Base naïve (pré-spécifiée) toujours buzz, pour lecture du gain de performance.
    baseline = pd.DataFrame({
        "label_reference": np.where(features.label == 1, "tendance", "buzz"),
        "prediction_oof": "buzz", "score_tendance_non_calibre": 0.0,
        "topic_id": features.topic_id,
        "correct_oof": features.label == 0,
    })

    # Le modèle publié contient l'ensemble des 30 sujets, uniquement pour INFERENCE.
    fitted = candidate(winner).fit(
        features[FEATURE_COLUMNS].to_numpy(float), features.label.to_numpy(int))
    dump({
        "model": fitted, "feature_columns": FEATURE_COLUMNS,
        "model_type": winner, "version": VERSION,
        "training_topic_ids": features.topic_id.tolist(),
        "training_n": len(features),
        "label_status": "provisional_unverified",
        "prediction_scope": "retrospective_full_window_2019_2026",
        "classes": {"0": "buzz", "1": "tendance"},
    }, out / "model_v2.joblib")
    winner_predictions = looto(features, winner)
    winner_predictions = winner_predictions.merge(
        audit[["topic_id", "n_zones", "status"]], on="topic_id", how="left")
    winner_predictions.to_csv(out / "predictions_30_oof.csv", index=False)

    warnings = [
        "M2 caractérise des trajectoires complètes 2019–2026 : AUCUNE prédiction pré-pic validée.",
        "Les labels ont été fournis par l'équipe, non vérifiés indépendamment.",
        "Le label tendance de pistachio est PROVISOIRE (hypothèse de travail).",
        "La normalisation Google Trends de pistachio P0 diffère de l'historique de référence.",
        "Choisir le meilleur des 3 sur ces mêmes 30 cas introduit un biais de sélection.",
        "Les scores retournés par les modèles ne sont pas des probabilités calibrées.",
        "La taille n=30 rend l'incertitude importante ; les mois ne sont pas des exemples indépendants.",
        "Les sujets ont été choisis par l'équipe et peuvent être particulièrement faciles à séparer a posteriori.",
        "WORLD est exclu ; whipped_lemonade n'a qu'un seul pays exploitable.",
        "Les features incluent des mois futurs par rapport à une date historique T éventuelle.",
    ]
    doc = {
        "version": VERSION,
        "evaluation": "leave_one_topic_out_retrospective",
        "reference_topics_total": len(audit),
        "food_cases_evaluated": len(features),
        "class_counts": {
            "buzz": int((features.label == 0).sum()),
            "tendance": int((features.label == 1).sum()),
        },
        "comparison": results,
        "always_buzz_baseline": measure(baseline),
        "sensitivity_without_provisional_pistachio": sensitivity,
        "selected_candidate": winner,
        "selection_basis": "max LOOTO F1 macro, tie favors simpler model; no independent test set",
        "warnings": warnings,
    }
    (out / "metrics_v2.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest = {
        "version": VERSION, "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_file": str(input_path), "input_sha256": sha256(input_path),
        "python": platform.python_version(), "numpy": np.__version__,
        "pandas": pd.__version__, "scikit_learn": sklearn.__version__,
        "xgboost": xgboost.__version__,
        "feature_columns": FEATURE_COLUMNS,
        "random_state": SEED,
        "model_candidates": {name: candidate(name).get_params() for name in MODEL_NAMES},
        "model_selected": winner,
        "metrics_file": "metrics_v2.json",
        "predictions_file": "predictions_30_oof.csv",
        "repro_command": "python -m sillage_v2.compare_models --input data/raw/reference_30_aliments_pistache_PROVISOIRE.csv --out artifacts/comparison_v2",
    }
    (out / "manifest_comparison_v2.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    rows = ["| Modèle | Corrects | Accuracy | F1 macro | Erreurs |", "|---|---:|---:|---:|---|"]
    for name in MODEL_NAMES:
        r = results[name]
        rows.append(f"| {name} | {r['correct']}/30 | {r['accuracy']:.3f} | {r['f1_macro']:.3f} | {', '.join(r['errors']) or 'aucune'} |")
    (out / "RAPPORT_COMPARAISON_V2.md").write_text(
        "# Sillage — Comparaison M2 V2 (exploratoire)\n\n"
        "**Données :** 30 aliments, 15 buzz / 15 tendances, label pistache PROVISOIRE.\n\n"
        "**Méthode :** Leave-One-Topic-Out, prétraitement appris dans chaque fold, "
        "hyperparamètres prédéfinis ; mêmes 7 features pour les trois modèles.\n\n"
        + "\n".join(rows) + "\n\n"
        + f"**Candidat technique :** {winner}. Une sélection sur le même jeu n'est pas une validation indépendante.\n\n"
        + "## Sensibilité : exclure pistache\n\n"
        + "\n".join(f"- {name} : {v['correct']}/29 ; F1 macro {v['f1_macro']:.3f}"
                    for name, v in sensitivity.items()) + "\n\n"
        + "## Limitations\n\n"
        + "\n".join(f"- {w}" for w in warnings) + "\n\n"
        + "## Fichiers de preuve\n\n"
        + "- `comparaison_par_sujet.csv` : prévisions comparables par sujet\n"
        + "- `predictions_*.csv` : OOF de chaque modèle\n"
        + "- `metrics_v2.json` : scores et matrices de confusion\n"
        + "- `manifest_comparison_v2.json` : version, paramètres et SHA256 de la source\n"
        + "- `model_v2.joblib` : modèle entier sélectionné sur 30 sujets (à ne charger que depuis une source fiable)\n"
        + "- `predictions_30_oof.csv` : OOF du modèle retenu pour l'API\n",
        encoding="utf-8",
    )
    return doc


def main():
    parser = argparse.ArgumentParser(description="Comparaison M2 : 3 modèles, LOOTO, historique complet")
    parser.add_argument("--input", type=Path, default=Path("data/raw/reference_30_aliments_pistache_PROVISOIRE.csv"))
    parser.add_argument("--out", type=Path, default=Path("artifacts/comparison_v2"))
    args = parser.parse_args()
    metrics = compare(args.input, args.out)
    print(json.dumps({
        "selected_candidate": metrics["selected_candidate"],
        "summary": {name: {"correct": result["correct"], "f1_macro": result["f1_macro"]}
                    for name, result in metrics["comparison"].items()},
        "output": str(args.out),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
