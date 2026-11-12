"""M3: monthly search-interest forecasting. Each model only sees values before its forecast origin."""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

HORIZON = 3
MODELS = ("last_value", "seasonal_naive_12", "holt_damped", "ridge_direct")
CUTOFFS = tuple(pd.date_range("2024-01-01", "2026-07-01", freq="3MS"))
VALID_COUNTRIES = ("FR", "US", "JP", "KR", "AE")


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _bool_value(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin(("true", "1", "yes"))


def load_series(path: str | Path) -> list[dict]:
    """Reject incomplete/ambiguous series; never interpolate or manufacture missing months."""
    df = pd.read_csv(path, dtype={"country_iso2": "string"})
    cols = {"topic_id", "country_iso2", "period_start", "value", "normalization_scope_id",
            "frequency", "source", "source_url", "query_original", "is_synthetic"}
    missing = cols - set(df)
    if missing:
        raise ValueError(f"Colonnes manquantes: {sorted(missing)}")
    df = df.copy()
    df = df[~_bool_value(df.is_synthetic)]
    df = df[df.country_iso2.isin(VALID_COUNTRIES)]  # WORLD is not a country
    if (df.frequency != "monthly").any():
        raise ValueError("Les données doivent être mensuelles")
    df["date"] = pd.to_datetime(df.period_start, errors="raise")
    if (df["date"].dt.day != 1).any():
        raise ValueError("period_start doit être le 1er jour du mois")
    if df.value.isna().any() or (~df.value.between(0, 100)).any():
        raise ValueError("Valeurs non numériques / hors de [0,100]")
    result = []
    group = ["topic_id", "country_iso2", "normalization_scope_id", "query_original"]
    for keys, g in df.groupby(group, dropna=False, sort=True):
        g = g.sort_values("date").reset_index(drop=True)
        if g["date"].duplicated().any():
            raise ValueError(f"Doublon mensuel pour {keys}")
        expected = pd.date_range(g.date.iloc[0], g.date.iloc[-1], freq="MS")
        if len(expected) != len(g) or not np.array_equal(expected.values, g.date.values):
            raise ValueError(f"Mois manquants dans {keys} : conserver en quarantaine, pas en zéro")
        if len(g) < 60:
            continue
        if g.source.nunique() != 1 or g.source_url.nunique() != 1:
            raise ValueError(f"Provenance incohérente pour {keys}")
        result.append({
            "ingredient": str(keys[0]), "country": str(keys[1]),
            "normalization_scope": str(keys[2]), "query_original": str(keys[3]),
            "source": str(g.source.iloc[0]), "source_url": str(g.source_url.iloc[0]),
            "dates": pd.DatetimeIndex(g.date), "values": g.value.to_numpy(float),
            "dataset_partition": str(g.dataset_partition.iloc[0]) if "dataset_partition" in g else "pilot_p0",
            "normalization_window": str(g.normalization_window.iloc[0]) if "normalization_window" in g else "2019-01_to_2026-10",
        })
    if not result:
        raise ValueError("Aucune série mensuelle géographique éligible")
    return result


def _features(y: np.ndarray, next_month: int) -> np.ndarray:
    # Features depend only on the 24 past values and the month being predicted.
    if len(y) < 24:
        raise ValueError("Au moins 24 mois sont nécessaires pour les features")
    return np.array([
        y[-1], y[-2], y[-3], y[-6], y[-12], y[-24],
        y[-3:].mean(), y[-6:].mean(), y[-12:].mean(),
        y[-6:].std(), y[-12:].std(),
        float((y[-12:] > 0).mean()),
        float(y[-3:].mean() - y[-12:-3].mean()),
        np.sin(2 * np.pi * next_month / 12),
        np.cos(2 * np.pi * next_month / 12),
    ])


def _ridge_direct(history: np.ndarray, origin_month: pd.Timestamp, horizon: int) -> np.ndarray:
    """Fit direct h-step models, using training origins whose targets are known by cutoff."""
    out = []
    for h in range(1, horizon+1):
        X, target = [], []
        # j is EXCLUSIVE historical end. y[j+h-1] is target and must exist in history.
        for j in range(24, len(history)-h+1):
            forecast_month = (origin_month - pd.DateOffset(months=len(history)-j)) + pd.DateOffset(months=h)
            X.append(_features(history[:j], forecast_month.month))
            target.append(history[j+h-1])
        if len(target) < 12:
            raise ValueError("Trop peu d'origines pour la régression")
        model = make_pipeline(StandardScaler(), Ridge(alpha=30.0))
        model.fit(np.asarray(X), np.asarray(target))
        wanted_month = (origin_month + pd.DateOffset(months=h)).month
        out.append(float(model.predict(_features(history, wanted_month)[None, :])[0]))
    return np.asarray(out, dtype=float)


def _holt_damped(history: np.ndarray, horizon: int, alpha: float = .30,
                 beta: float = .10, phi: float = .85) -> np.ndarray:
    # Fixed smoothing parameters; no optimization on the validation period.
    level, trend = float(history[0]), float(history[1] - history[0])
    for value in history[1:]:
        prev_level = level
        level = alpha * float(value) + (1 - alpha) * (level + phi * trend)
        trend = beta * (level - prev_level) + (1 - beta) * phi * trend
    return np.asarray([level + trend * sum(phi**k for k in range(1, h+1))
                       for h in range(1, horizon+1)], dtype=float)


def predict(history: np.ndarray, origin_month: pd.Timestamp,
            model: str, horizon: int = HORIZON) -> np.ndarray:
    history = np.asarray(history, dtype=float)
    if horizon < 1 or horizon > 12 or len(history) < 48:
        raise ValueError("Historique requis >=48 mois ; horizon 1..12")
    if model == "last_value":
        preds = np.repeat(history[-1], horizon)
    elif model == "seasonal_naive_12":
        preds = history[-12:][:horizon]
    elif model == "holt_damped":
        preds = _holt_damped(history, horizon)
    elif model == "ridge_direct":
        preds = _ridge_direct(history, pd.Timestamp(origin_month), horizon)
    else:
        raise ValueError(f"Modèle inconnu: {model}")
    # Google Trends range per-normalization is 0..100; avoid impossible values.
    return np.clip(preds, 0, 100)


def backtest(series: list[dict]) -> pd.DataFrame:
    records = []
    for s in series:
        dates, values = s["dates"], s["values"]
        for origin in CUTOFFS:
            ix = np.flatnonzero(dates == origin)
            if len(ix) != 1 or ix[0] < 59 or ix[0] + HORIZON >= len(dates):
                continue
            j = int(ix[0]); history = values[:j+1]
            actuals = values[j+1:j+1+HORIZON]
            for model in MODELS:
                preds = predict(history, origin, model)
                for h, (pred, actual) in enumerate(zip(preds, actuals), start=1):
                    records.append({
                        "ingredient": s["ingredient"], "country": s["country"],
                        "normalization_scope": s["normalization_scope"],
                        "dataset_partition": s["dataset_partition"], "model": model,
                        "origin_month": origin.strftime("%Y-%m"),
                        "target_month": dates[j+h].strftime("%Y-%m"),
                        "horizon_months": h, "actual": float(actual),
                        "prediction": float(pred), "abs_error": float(abs(actual-pred)),
                        "error": float(pred-actual), "split": "final_holdout" if origin == CUTOFFS[-1] else "selection",
                    })
    df = pd.DataFrame(records)
    if df.empty:
        raise ValueError("Pas de folds de backtest valides")
    return df


def metrics(backtest_df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    grouped = (backtest_df.groupby(["split", "model"], sort=True)
               .agg(mae=("abs_error", "mean"), bias=("error", "mean"),
                    n_predictions=("abs_error", "size"), n_series=("normalization_scope", "nunique"))
               .reset_index())
    grouped["rmse"] = [np.sqrt(np.mean(g.error.to_numpy(float)**2))
                       for _, g in backtest_df.groupby(["split", "model"], sort=True)]
    selection = grouped[grouped.split == "selection"].sort_values(["mae", "model"])
    return grouped, str(selection.model.iloc[0])


def forecast_latest(series: list[dict], selected_model: str, include_all=True) -> pd.DataFrame:
    records = []
    selected = MODELS if include_all else (selected_model,)
    for s in series:
        origin = s["dates"][-1]
        for model in selected:
            preds = predict(s["values"], origin, model)
            for h, pred in enumerate(preds, 1):
                records.append({
                    "ingredient": s["ingredient"], "country": s["country"],
                    "normalization_scope": s["normalization_scope"],
                    "dataset_partition": s["dataset_partition"],
                    "normalization_window": s["normalization_window"],
                    "query_original": s["query_original"], "source_url": s["source_url"],
                    "model": model, "selected_model": selected_model,
                    "is_selected": model == selected_model,
                    "origin_month": origin.strftime("%Y-%m"),
                    "target_month": (origin + pd.DateOffset(months=h)).strftime("%Y-%m"),
                    "horizon_months": h, "predicted_index_0_100": round(float(pred), 4),
                    "unit": "Google_Trends_relative_index_0_100", "is_synthetic": False,
                    "forecast_is_estimate": True,
                })
    return pd.DataFrame(records)
