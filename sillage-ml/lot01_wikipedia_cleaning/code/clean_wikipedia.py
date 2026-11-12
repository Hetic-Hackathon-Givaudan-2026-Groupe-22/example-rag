"""Sillage G22 — nettoyage / audit du lot Wikimedia (1 ligne = article×wiki×mois).

Usage depuis la racine du dossier livré :
 python code/clean_wikipedia.py --input raw/observations_wikipedia.parquet \
   --quality raw/quality_report_wikipedia.csv --manifest raw/search_manifest_wikipedia.csv \
   --dictionary raw/dictionnaire_requetes.csv --out output

Compatible avec CSV .csv (UTF-8-SIG) et Parquet .parquet (nécessite pyarrow).
Ne fabrique ni pays, ni dates manquantes, ni observations, ni labels supervisés.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT_VERSION = "1.1.0"
LAST_COMPLETE_MONTH = pd.Period("2026-10", freq="M")
MIN_COMPLETENESS = 0.85
MIN_STREAK = 24
DATA_FIELDS = [
    "observation_id", "topic_id", "topic_label", "country_iso2", "wiki_project",
    "period_start", "period_end", "frequency", "source", "metric", "value", "unit",
    "query_original", "normalization_scope_id", "source_url", "page_url", "raw_file",
    "collected_at_utc", "is_synthetic", "label_reference", "license", "run_id", "quality_flags",
]


def hash_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def longest_streak(periods: pd.PeriodIndex) -> int:
    nums = sorted(set(p.ordinal for p in periods))
    if not nums:
        return 0
    best = cur = 1
    for a, b in zip(nums, nums[1:]):
        cur = cur + 1 if b == a + 1 else 1
        best = max(best, cur)
    return best


def normalize_bool(v) -> bool | None:
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    s = str(v).lower().strip()
    return {"true": True, "false": False, "0": False, "1": True}.get(s)


def flags_list(v) -> list[str]:
    try:
        x = json.loads(v) if isinstance(v, str) else v
        return x if isinstance(x, list) else []
    except (ValueError, TypeError):
        return []


def load_source(p: Path) -> pd.DataFrame:
    if p.suffix.lower() == ".parquet":
        try:
            return pd.read_parquet(p)
        except ImportError as e:
            raise RuntimeError("Pour lire Parquet : python -m pip install pyarrow. Ou utiliser le CSV extrait fourni.") from e
    if p.suffix.lower() == ".csv":
        return pd.read_csv(p, encoding="utf-8-sig", low_memory=False)
    raise ValueError("Entrée .parquet ou .csv requise")


def run(input_p: Path, quality_p: Path, manifest_p: Path, dict_p: Path, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    raw = load_source(input_p)
    q = pd.read_csv(quality_p, encoding="utf-8-sig")
    man = pd.read_csv(manifest_p, encoding="utf-8-sig")
    terms = pd.read_csv(dict_p, encoding="utf-8-sig")
    for field in DATA_FIELDS:
        if field not in raw.columns:
            raise ValueError(f"Colonne manquante dans l'entrée : {field}")
    if q.duplicated(["topic_id", "wiki_project"]).any():
        raise ValueError("Rapport qualité contient plusieurs lignes pour une même série")
    if man.duplicated(["topic_id", "wiki_project"]).any():
        raise ValueError("Manifeste de recherche contient plusieurs lignes pour une même série")

    df = raw.copy()
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    dates = pd.to_datetime(df["period_start"], format="%Y-%m-%d", errors="coerce")
    ends = pd.to_datetime(df["period_end"], format="%Y-%m-%d", errors="coerce")
    end_expected = dates + pd.offsets.MonthEnd(0)
    country_present = df["country_iso2"].notna() & df["country_iso2"].astype(str).str.strip().ne("")
    origin = df["is_synthetic"].map(normalize_bool)
    bad = pd.DataFrame(index=df.index)
    bad["invalid_value"] = df["value"].isna() | ~np.isfinite(df["value"]) | (df["value"] < 0)
    bad["invalid_date"] = dates.isna() | (dates.dt.day != 1) | (dates.dt.to_period("M") > LAST_COMPLETE_MONTH)
    bad["inconsistent_period_end"] = ends.isna() | (ends != end_expected)
    bad["missing_identity"] = (df["topic_id"].isna() | df["wiki_project"].isna() | df["source"].isna() | df["metric"].isna())
    bad["invalid_wiki_project"] = ~df["wiki_project"].astype(str).str.fullmatch(r"[a-z-]+\.wikipedia")
    bad["non_wikimedia_source"] = df["source"].ne("wikimedia_pageviews")
    bad["unexpected_country"] = country_present
    bad["invalid_origin"] = origin.isna() | origin.eq(True)
    bad["invalid_provenance"] = ~df["source_url"].astype(str).str.startswith("https://")
    invalid_mask = bad.any(axis=1)
    invalid = df.loc[invalid_mask].copy()
    invalid["rejection_reasons"] = (bad.loc[invalid_mask].apply(lambda r: ";".join(r.index[r.to_numpy()]), axis=1) if bool(invalid_mask.any()) else pd.Series(dtype=str))
    clean = df.loc[~invalid_mask].copy()
    clean["value"] = clean["value"].astype(float)
    clean["is_synthetic"] = False
    clean["period_start"] = dates.loc[~invalid_mask].dt.strftime("%Y-%m-%d")
    clean["period_end"] = ends.loc[~invalid_mask].dt.strftime("%Y-%m-%d")

    # Vérification des empreintes de lignes et conflits : ne jamais choisir arbitrairement un doublon discordant.
    key = clean["topic_id"].astype(str) + "|" + clean["wiki_project"].astype(str) + "|" + clean["source"].astype(str) + "|" + clean["metric"].astype(str) + "|" + clean["period_start"].astype(str)
    expected_id = key.map(lambda s: hashlib.sha1(s.encode("utf-8")).hexdigest()[:16])
    mismatch_ids = int((clean["observation_id"].astype(str) != expected_id).sum())
    if mismatch_ids:
        raise ValueError(f"{mismatch_ids} identifiants ne correspondent pas aux clés d'observation")
    if clean.duplicated(["topic_id", "wiki_project", "source", "metric", "period_start"]).any():
        same_key_cols = ["topic_id", "wiki_project", "source", "metric", "period_start"]
        d = clean.loc[clean.duplicated(same_key_cols, keep=False)]
        if d.groupby(same_key_cols)["value"].nunique(dropna=False).gt(1).any():
            raise ValueError("Doublons avec valeurs contradictoires : correction manuelle nécessaire")
        clean = clean.drop_duplicates(subset=same_key_cols, keep="first")
    removed_dups = int((~invalid_mask).sum() - len(clean))
    clean.sort_values(["topic_id", "wiki_project", "period_start"], inplace=True)
    clean.reset_index(drop=True, inplace=True)

    statuses = []
    for (topic, wiki), group in clean.groupby(["topic_id", "wiki_project"], sort=True):
        ps = pd.PeriodIndex(pd.to_datetime(group["period_start"]), freq="M")
        expected = (LAST_COMPLETE_MONTH - ps.min()).n + 1
        observed = len(group)
        streak = longest_streak(ps)
        coverage = observed / expected
        flags = sorted(set(flag for v in group["quality_flags"] for flag in flags_list(v)))
        if "hors_perimetre" in flags:
            status = "exclu_perimetre"
        elif coverage >= MIN_COMPLETENESS and streak >= MIN_STREAK:
            status = "a_verifier" if "mapping_a_verifier" in flags else "usable"
        else:
            status = "insuffisant"
        statuses.append({
            "topic_id": topic, "wiki_project": wiki, "country_iso2": None,
            "start": str(ps.min()), "end": str(ps.max()),
            "n_expected_to_cutoff": int(expected), "n_observed": int(observed),
            "n_missing_to_cutoff": int(expected-observed),
            "coverage_pct": round(100*coverage, 2), "max_consecutive_months": streak,
            "n_zeros": int((group["value"] == 0).sum()),
            "status_recomputed": status, "flags": ";".join(flags),
        })
    series = pd.DataFrame(statuses)
    series = series.merge(q[["topic_id", "wiki_project", "status", "expected", "observed"]].rename(columns={"status": "status_reported", "expected": "expected_reported", "observed": "observed_reported"}), on=["topic_id", "wiki_project"], how="left", validate="one_to_one")
    series["quality_report_matches"] = (series["status_recomputed"] == series["status_reported"]) & (series["n_expected_to_cutoff"] == series["expected_reported"]) & (series["n_observed"] == series["observed_reported"])
    if (~series["quality_report_matches"]).any():
        raise ValueError("Désaccord avec le rapport qualité original ; vérifier series_quality_recomputed avant publication")
    source_series = set(zip(man.topic_id, man.wiki_project))
    cleaned_series = set(zip(series.topic_id, series.wiki_project))
    if source_series != cleaned_series:
        raise ValueError(f"Séries du manifeste et du jeu nettoyé différentes : manifest={len(source_series)}, cleaned={len(cleaned_series)}")
    clean = clean.merge(series[["topic_id", "wiki_project", "status_recomputed"]], on=["topic_id", "wiki_project"], how="left", validate="many_to_one")
    assert clean["status_recomputed"].notna().all()
    clean.rename(columns={"status_recomputed": "quality_status"}, inplace=True)
    eligible = clean.loc[clean["quality_status"].eq("usable")].copy()
    review = clean.loc[~clean["quality_status"].eq("usable")].copy()
    m1cols = ["observation_id", "topic_id", "wiki_project", "period_start", "value", "source", "metric", "unit", "source_url", "page_url", "country_iso2", "is_synthetic", "quality_status"]
    m1 = eligible.loc[:, m1cols].copy().rename(columns={"topic_id": "ingredient", "period_start": "date"})
    m1.insert(2, "segment_type", "wiki_project")
    m1.rename(columns={"wiki_project": "segment_id"}, inplace=True)
    m1["normalization_scope"] = "absolute_pageviews_by_wikipedia_edition"

    # L'étiquette de la collecte est conservée en audit uniquement et JAMAIS dans le dataset de features.
    outputs = {
        "observations_clean_all.csv": clean,
        "observations_m1_eligible.csv": eligible,
        "observations_quarantine.csv": review,
        "observations_invalid.csv": invalid,
        "m1_wikipedia_contract.csv": m1,
        "series_quality_recomputed.csv": series,
    }
    for name, frame in outputs.items():
        frame.to_csv(out / name, index=False, encoding="utf-8-sig")
    # Optionnel : enregistrer le Parquet nettoyé si pyarrow est disponible.
    parquet_written = False
    try:
        eligible.to_parquet(out / "observations_m1_eligible.parquet", index=False)
        parquet_written = True
    except (ImportError, ModuleNotFoundError):
        pass

    stat_by_status = {s: {"n_series": int((series.status_recomputed==s).sum()), "n_obs": int((clean.quality_status==s).sum())} for s in ["usable", "insuffisant", "a_verifier", "exclu_perimetre"]}
    summary = {
        "data_source": "Wikimedia Pageviews (article views, editions linguistiques)",
        "raw_observations": len(raw), "validated_observations": len(clean), "invalid_observations": len(invalid),
        "duplicates_removed": removed_dups, "n_topics": int(clean.topic_id.nunique()),
        "n_wikipedia_editions": int(clean.wiki_project.nunique()),
        "n_series": len(series), "n_zero_values_preserved": int((clean.value==0).sum()),
        "date_min": str(clean.period_start.min()), "date_max": str(clean.period_start.max()),
        "status_breakdown": stat_by_status, "n_m1_eligible": len(eligible), "n_quarantine": len(review),
        "n_gt_dictionary_topics": int(terms.topic_id.nunique()),
        "n_wiki_topics_without_gt_dictionary_entry": int(len(set(clean.topic_id)-set(terms.topic_id))),
        "country_iso2_null_all_rows": bool(clean.country_iso2.isna().all()),
        "is_synthetic_count": int(clean.is_synthetic.sum()),
        "reported_quality_statuses_reproduced": bool(series.quality_report_matches.all()),
        "original_preparatory_labels_are_not_validated_ground_truth": True,
        "cleaned_parquet_written": parquet_written,
        "warnings": [
            "Les éditions linguistiques Wikipédia ne sont PAS des pays. Cross-market géographique non pris en charge.",
            "Les vues de pages sont un proxy d'intérêt documentaire et NON des volumes de recherche ou des ventes alimentaires.",
            "Ne PAS entraîner une classification supervisée avec label_reference sans validation humaine indépendante.",
            "Aucune interpolation des mois absents, aucun remplacement des zéros, aucun clipping des pics.",
            "La source brute echantillon_pageviews.csv n'était pas dans les fichiers reçus : reproduction possible depuis le Parquet uniquement.",
            "Le pipeline M1 existant exige un country ISO2 : NE PAS lui passer les langues comme pays. Adapter M1 à segment_type=wiki_project."
        ]
    }
    (out/"quality_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2), encoding="utf-8")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + hash_file(input_p)[:10]
    manifest = {
        "run_id": run_id,
        "pipeline": "sillage_wikipedia_cleaning", "script_version": SCRIPT_VERSION,
        "executed_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": str(input_p), "source_sha256": hash_file(input_p),
        "source_parquet_sha256_in_bundle": hash_file(input_p.parent/"observations_wikipedia.parquet") if (input_p.parent/"observations_wikipedia.parquet").exists() else None,
        "cutoff_month": str(LAST_COMPLETE_MONTH),
        "min_completeness": MIN_COMPLETENESS, "min_consecutive_months": MIN_STREAK,
        "reference_files": {k:hash_file(v) for k,v in [("quality",quality_p),("search_manifest",manifest_p),("dictionary",dict_p)]},
        "outputs_sha256": {n: hash_file(out/n) for n in outputs},
        "cleaning_policy": "retain all valid values; quarantine invalid/out-of-scope/mapping doubtful/too-short series; preserve source original",
    }
    (out/"processing_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    # Append-only journal : une ligne par exécution, sans perdre l'historique des transformations.
    run_log = out / "cleaning_runs.csv"
    log_row = pd.DataFrame([{"run_id": run_id, "script_version": SCRIPT_VERSION, "source_sha256": hash_file(input_p),
                             "n_raw": len(raw), "n_clean": len(clean), "n_eligible": len(eligible),
                             "n_quarantine": len(review), "n_invalid": len(invalid), "status": "success"}])
    log_row.to_csv(run_log, mode="a", header=not run_log.exists(), index=False, encoding="utf-8-sig")
    print(json.dumps({k:v for k,v in summary.items() if k in ["raw_observations", "validated_observations", "n_series", "n_m1_eligible", "n_quarantine", "status_breakdown"]},ensure_ascii=False,indent=2))
    return summary


def main():
    p=argparse.ArgumentParser(description="Sillage — audit et nettoyage reproductibles Wikimedia")
    p.add_argument("--input", default="raw/observations_wikipedia.parquet",type=Path)
    p.add_argument("--quality", default="raw/quality_report_wikipedia.csv",type=Path)
    p.add_argument("--manifest", default="raw/search_manifest_wikipedia.csv",type=Path)
    p.add_argument("--dictionary",default="raw/dictionnaire_requetes.csv",type=Path)
    p.add_argument("--out",default="output",type=Path)
    a=p.parse_args()
    run(a.input,a.quality,a.manifest,a.dictionary,a.out)
if __name__=="__main__":main()
