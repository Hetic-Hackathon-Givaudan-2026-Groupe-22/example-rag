"""Rolling descriptive attention states, NEVER a substitute for M2 buzz-vs-trend classification.

Each state uses ONLY monthly observations through its origin month. A new
observation moves the window and refreshes the state. Forecasts remain
unchanged last-value predictions, for an honest side-by-side comparison.
"""
from __future__ import annotations
from typing import Any
import numpy as np

INTERVAL_MONTHS = 3
MIN_HISTORY_MONTHS = 12
CHANGE_THRESHOLD_POINTS = 5.0
CHANGE_THRESHOLD_RATE = .15
LOW_ATTENTION_THRESHOLD = 5.0
HIGH_ATTENTION_THRESHOLD = 15.0

STATES = (
    "faible_attention", "hausse_a_confirmer", "hausse_persistante",
    "stable", "stable_niveau_eleve", "repli_a_confirmer", "repli_persistant",
)


def _increasing(current: float, previous: float) -> bool:
    return current - previous >= CHANGE_THRESHOLD_POINTS and (current - previous) / max(previous, 5.0) >= CHANGE_THRESHOLD_RATE


def _decreasing(current: float, previous: float) -> bool:
    return previous - current >= CHANGE_THRESHOLD_POINTS and (previous - current) / max(previous, 5.0) >= CHANGE_THRESHOLD_RATE


def describe_history(history: np.ndarray) -> dict[str, Any]:
    """Describe past three NON-OVERLAPPING blocks of 3 months, no future info.

    This is an exploratory rule using relative GT index points. Does not claim
    persistent interest = validated durable consumer trend or commercial demand.
    """
    y = np.asarray(history, dtype=float)
    if len(y) < MIN_HISTORY_MONTHS:
        raise ValueError(f"Historique requis >= {MIN_HISTORY_MONTHS} mois")
    if not np.isfinite(y).all() or (y < 0).any() or (y > 100).any():
        raise ValueError("Série Google Trends invalide (valeurs 0..100 requises)")
    before, previous, recent = (float(np.mean(y[-9:-6])),
                                float(np.mean(y[-6:-3])), float(np.mean(y[-3:])))
    growing_now = _increasing(recent, previous)
    growing_before = _increasing(previous, before)
    shrinking_now = _decreasing(recent, previous)
    shrinking_before = _decreasing(previous, before)
    if growing_now:
        state = "hausse_persistante" if growing_before else "hausse_a_confirmer"
    elif shrinking_now:
        state = "repli_persistant" if shrinking_before else "repli_a_confirmer"
    elif recent < LOW_ATTENTION_THRESHOLD and previous < LOW_ATTENTION_THRESHOLD:
        state = "faible_attention"
    elif recent >= HIGH_ATTENTION_THRESHOLD:
        state = "stable_niveau_eleve"
    else:
        state = "stable"
    return {
        "phase": state,
        "mean_months_minus_8_to_minus_6": round(before, 4),
        "mean_previous_3_months": round(previous, 4),
        "mean_recent_3_months": round(recent, 4),
        "delta_recent_vs_previous_points": round(recent - previous, 4),
        "delta_previous_vs_before_points": round(previous - before, 4),
        "last_observed_index": float(y[-1]),
        "growth_confirmed_two_intervals": bool(growing_now and growing_before),
        "decline_confirmed_two_intervals": bool(shrinking_now and shrinking_before),
        "is_buzz_vs_trend_label": False,
    }


def history_states(series: list[dict]) -> list[dict]:
    """Refresh rolling states MONTHLY for each geographic series."""
    out = []
    for s in series:
        values, dates = s["values"], s["dates"]
        for j in range(MIN_HISTORY_MONTHS - 1, len(values)):
            r = describe_history(values[:j+1])
            out.append({
                "ingredient": s["ingredient"], "country": s["country"],
                "normalization_scope": s["normalization_scope"],
                "dataset_partition": s["dataset_partition"],
                "normalization_window": s["normalization_window"],
                "query_original": s["query_original"], "source_url": s["source_url"],
                "origin_month": dates[j].strftime("%Y-%m"),
                "history_available_months": j+1, **r,
            })
    return out
