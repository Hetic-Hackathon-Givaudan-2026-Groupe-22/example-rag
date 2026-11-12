"""Pipeline M1: données brutes -> contrôle qualité -> caractéristiques -> alertes.

Les alertes signalent une émergence anormale; elles ne classent pas la durabilité.
Toutes les statistiques de la date t sont calculées à partir du passé <= t.
Les seuils sont EXPLORATOIRES, non validés statistiquement sur données de marché.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from sillage import __version__

SERIES_KEY = ["ingredient", "country", "source", "metric", "normalization_scope"]
REQUIRED = SERIES_KEY + ["date", "value", "is_synthetic"]
OPTIONAL = ["source_url"]
BOOL_MAPPING = {"true": True, "false": False, "1": True, "0": False, "yes": True, "no": False}


@dataclass(frozen=True)
class DetectionConfig:
    frequency: str = "weekly"  # weekly / monthly
    history_window: int = 12
    growth_lag: int = 4
    z_threshold: float = 3.0
    growth_threshold: float = 0.25
    cooldown: int = 4

    def check(self) -> None:
        if self.frequency not in {"weekly", "monthly"}:
            raise ValueError("frequency doit être 'weekly' ou 'monthly'")
        if self.history_window < 6 or self.growth_lag < 1 or self.cooldown < 1:
            raise ValueError("Fenêtres trop courtes / invalides")
        if self.growth_lag > self.history_window:
            raise ValueError("growth_lag doit être <= history_window")


def _load_mapping(mapping_file: Path | None) -> dict[str, str]:
    if mapping_file is None:
        return {}
    mapping = json.loads(mapping_file.read_text(encoding="utf-8"))
    if not isinstance(mapping, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in mapping.items()):
        raise ValueError("Mapping JSON attendu : {'colonne_brute': 'colonne_canonique'}")
    return mapping


def load_and_clean(input_csv: Path, mapping_file: Path | None = None) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Contrat strict: la provenance et l'origine réelle/synthétique sont obligatoires.

    Ne fabrique pas de pays, de source, de scope, de dates ou d'observations.
    Ignore les lignes invalides, refuse les doublons conflictuels.
    """
    raw = pd.read_csv(input_csv, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    raw.rename(columns={c: c.strip() for c in raw.columns}, inplace=True)
    mapping = _load_mapping(mapping_file)
    raw.rename(columns=mapping, inplace=True)
    if raw.columns.duplicated().any():
        raise ValueError("Le mapping produit des noms de colonnes dupliqués")
    missing = [col for col in REQUIRED if col not in raw.columns]
    if missing:
        raise ValueError(f"Colonnes obligatoires manquantes : {missing}. Voir README pour adapter vos données.")
    for col in OPTIONAL:
        if col not in raw.columns:
            raw[col] = ""
    raw_count = len(raw)
    work = raw[REQUIRED + OPTIONAL].copy()
    for col in SERIES_KEY + ["date", "is_synthetic", "source_url"]:
        work[col] = work[col].astype(str).str.strip()
    work["ingredient"] = work["ingredient"].str.lower()
    work["country"] = work["country"].str.upper()
    # ISO 8601 explicite : pas d'interprétation ambiguë JJ/MM vs MM/JJ.
    work["parsed_date"] = pd.to_datetime(work["date"], format="%Y-%m-%d", errors="coerce")
    work["value"] = pd.to_numeric(work["value"].astype(str).str.strip().str.replace(",", ".", regex=False), errors="coerce")
    work["origin"] = work["is_synthetic"].str.lower().map(BOOL_MAPPING)
    bad_date = int(work["parsed_date"].isna().sum())
    bad_value = int((work["value"].isna() | (work["value"] < 0) | ~np.isfinite(work["value"])).sum())
    bad_origin = int(work["origin"].isna().sum())
    bad_country = int((~work["country"].str.fullmatch(r"[A-Z]{2}")).sum())
    incomplete = work[SERIES_KEY].eq("").any(axis=1)
    missing_identity = int(incomplete.sum())
    invalid_mask = (
        work["parsed_date"].isna() | work["value"].isna() |
        (work["value"] < 0) | ~np.isfinite(work["value"]) |
        work["origin"].isna() |
        (~work["country"].str.fullmatch(r"[A-Z]{2}")) | incomplete
    )
    invalid_rows = int(invalid_mask.sum())
    work = work.loc[~invalid_mask].copy()
    work["is_synthetic"] = work["origin"].astype(bool)
    work["date"] = work["parsed_date"].dt.strftime("%Y-%m-%d")
    work.drop(columns=["parsed_date", "origin"], inplace=True)
    exact_duplicates = int(work.duplicated().sum())
    work.drop_duplicates(inplace=True)
    date_key = SERIES_KEY + ["date"]
    if work.duplicated(subset=date_key).any():
        bad = work.loc[work.duplicated(subset=date_key, keep=False), date_key].head(3)
        raise ValueError(f"Observations conflictuelles pour une même série/date : {bad.to_dict('records')}")
    if work.groupby(SERIES_KEY, dropna=False)["is_synthetic"].nunique().gt(1).any():
        raise ValueError("Une série mélange du réel et du synthétique : séparez les séries")
    work.sort_values(SERIES_KEY + ["date"], inplace=True, kind="stable")
    work.reset_index(drop=True, inplace=True)
    real_rows = work.loc[~work["is_synthetic"]]
    missing_url_real = int(real_rows["source_url"].eq("").sum())
    report = {
        "n_raw": raw_count,
        "n_clean": len(work),
        "n_invalid_rows_dropped": invalid_rows,
        "n_exact_duplicates_removed": exact_duplicates,
        "n_bad_dates": bad_date,
        "n_bad_values": bad_value,
        "n_bad_origin": bad_origin,
        "n_bad_country_format": bad_country,
        "n_missing_series_identity": missing_identity,
        "n_real_rows_missing_source_url": missing_url_real,
        "n_series": int(work.groupby(SERIES_KEY).ngroups),
        "n_real": int((~work["is_synthetic"]).sum()),
        "n_synthetic": int(work["is_synthetic"].sum()),
        "warning": "Pays vérifié au format alpha-2, pas au registre ISO complet; contrôler les alias et les scopes Google Trends.",
    }
    if work.empty:
        raise ValueError(f"Aucune donnée exploitable : {report}")
    return work, report


def _is_regular_dates(dates: pd.Series, frequency: str) -> bool:
    parsed = pd.to_datetime(dates)
    if len(parsed) <= 1:
        return True
    if frequency == "weekly":
        return bool((parsed.diff().iloc[1:] == pd.Timedelta(days=7)).all())
    periods = parsed.dt.to_period("M")
    return bool(all((periods.iloc[i].ordinal - periods.iloc[i-1].ordinal) == 1 for i in range(1, len(periods))))


def detect(cleaned: pd.DataFrame, cfg: DetectionConfig, series_key: list[str] | None = None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """N'applique aucun lissage utilisant des observations futures."""
    cfg.check()
    key_cols = SERIES_KEY if series_key is None else series_key
    if not key_cols or any(c not in cleaned.columns for c in key_cols):
        raise ValueError("Clés de série manquantes : " + str(key_cols))
    feature_rows: list[dict] = []
    signal_rows: list[dict] = []
    series_summaries: list[dict] = []
    for values_key, group in cleaned.groupby(key_cols, sort=True):
        group = group.sort_values("date").reset_index(drop=True)
        props = dict(zip(key_cols, values_key))
        origin = bool(group.loc[0, "is_synthetic"])
        n = len(group)
        regular = _is_regular_dates(group["date"], cfg.frequency)
        status = "ok" if regular and n > cfg.history_window else ("irregular_frequency" if not regular else "insufficient_history")
        alerts_count = 0
        previous_raw_alert = []
        if status == "ok":
            x = group["value"].astype(float).to_numpy()
            for i in range(cfg.history_window, n):
                history = x[i-cfg.history_window:i]
                center = float(np.median(history))
                mad = float(np.median(np.abs(history-center)))
                sigma = max(1.0, 1.4826 * mad)  # plancher heuristique documenté
                z = float((x[i]-center) / sigma)
                prior = float(x[i-cfg.growth_lag])
                growth = float((x[i]-prior) / max(1.0, abs(prior)))
                raw_signal = z >= cfg.z_threshold and growth >= cfg.growth_threshold and x[i] > center
                is_new = bool(raw_signal and not any(previous_raw_alert[-cfg.cooldown:]))
                previous_raw_alert.append(bool(raw_signal))
                row = {
                    **props,
                    "date": group.loc[i, "date"],
                    "value": round(float(x[i]), 5),
                    "baseline_past_median": round(center, 5),
                    "robust_z": round(z, 5),
                    "growth_lag": round(growth, 5),
                    "is_raw_anomaly": bool(raw_signal),
                    "is_new_emergence": is_new,
                    "is_synthetic": origin,
                }
                feature_rows.append(row)
                if is_new:
                    signal_rows.append(row)
                    alerts_count += 1
        series_summaries.append({
            **props,
            "n_observations": n,
            "first_date": group.loc[0, "date"],
            "last_date": group.loc[n-1, "date"],
            "status": status,
            "emergence_events": alerts_count,
            "first_detected_at": next((s["date"] for s in signal_rows if all(s[k] == props[k] for k in key_cols)), None),
            "is_synthetic": origin,
        })
    return pd.DataFrame(feature_rows), pd.DataFrame(signal_rows), pd.DataFrame(series_summaries)


def _json_safe(records: list[dict]) -> list[dict]:
    result = []
    for row in records:
        obj = {}
        for k, v in row.items():
            if isinstance(v, (np.integer,)):
                v = int(v)
            elif isinstance(v, (np.floating,)):
                v = float(v)
            elif isinstance(v, (np.bool_,)):
                v = bool(v)
            if isinstance(v, float) and not np.isfinite(v):
                v = None
            obj[k] = v
        result.append(obj)
    return result


def publish(input_csv: Path, out_dir: Path, cfg: DetectionConfig, mapping_file: Path | None = None) -> dict:
    """Publie un artefact versionné à partir des données effectivement fournies."""
    cleaned, quality = load_and_clean(input_csv, mapping_file)
    features, signals, summaries = detect(cleaned, cfg)
    out_dir.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(out_dir / "cleaned.csv", index=False, encoding="utf-8-sig")
    features.to_csv(out_dir / "features.csv", index=False, encoding="utf-8-sig")
    (out_dir / "signals.json").write_text(json.dumps(_json_safe(signals.to_dict("records")), ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "series.json").write_text(json.dumps(_json_safe(summaries.to_dict("records")), ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "quality.json").write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {
        "model_version": f"M1-statistical-baseline-{__version__}",
        "method": "robust_z_past_median_plus_lag_growth",
        "status": "baseline_non_calibrated_not_M2",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_file": input_csv.name,
        "input_sha256": hashlib.sha256(input_csv.read_bytes()).hexdigest(),
        "parameters": asdict(cfg),
        "n_input_cleaned": len(cleaned),
        "n_series": len(summaries),
        "n_detected_events": len(signals),
        "contains_synthetic": bool(cleaned["is_synthetic"].any()),
        "contains_real": bool((~cleaned["is_synthetic"]).any()),
        "scientific_warning": "Ce détecteur n'est pas un classifieur buzz/durable et son score n'est pas une probabilité. Validation indépendante nécessaire.",
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser(description="Sillage M1 : nettoyage + détection + publication")
    ap.add_argument("--input", type=Path, required=True, help="CSV brut au format canonique")
    ap.add_argument("--out", type=Path, required=True, help="Dossier de résultats")
    ap.add_argument("--frequency", choices=["weekly", "monthly"], default="weekly")
    ap.add_argument("--mapping", type=Path, default=None, help="JSON optionnel des noms de colonnes")
    ap.add_argument("--window", type=int, default=12)
    ap.add_argument("--lag", type=int, default=4)
    ap.add_argument("--z", type=float, default=3.0)
    ap.add_argument("--growth", type=float, default=0.25)
    args = ap.parse_args()
    manifest = publish(args.input, args.out, DetectionConfig(frequency=args.frequency,
        history_window=args.window, growth_lag=args.lag, z_threshold=args.z,
        growth_threshold=args.growth), args.mapping)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
