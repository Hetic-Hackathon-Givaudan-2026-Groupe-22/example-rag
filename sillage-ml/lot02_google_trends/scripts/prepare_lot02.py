"""Sillage lot 02: preparer un CSV Google Trends geolocalise compatible avec M1.
Usage: python scripts/prepare_lot02.py
Uniquement bibliotheque standard Python; n'ajoute pas de donnees ni de labels au modele.
"""
import csv
import hashlib
import json
import math
from collections import defaultdict, Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
CLEAN = ROOT / "data" / "clean"
REPORTS = ROOT / "reports"
FILES = {
    "gt_p0": "google_trends_lot_P0_2019_2026.csv",
    "gt_reference": "reference_30_cas_google_trends_2019_2026.csv",
    "wiki": "wikipedia_attention_documentaire_2019_2026.csv",
    "prix": "prix_matieres_2019_2026.csv",
}
VALID_COUNTRIES = {"FR", "US", "JP", "KR", "AE"}


def read(name):
    with (RAW / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, columns, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_number(value, lo=0, hi=100):
    v = float(value)
    if not math.isfinite(v) or not lo <= v <= hi:
        raise ValueError(f"Valeur numerique invalide: {value}")
    return v


def main():
    gt = read(FILES["gt_p0"])
    ref = read(FILES["gt_reference"])
    wiki = read(FILES["wiki"])
    prix = read(FILES["prix"])
    ids = set()
    country_rows, world_rows = [], []
    series_country = defaultdict(list)
    for r in gt:
        if r["observation_id"] in ids:
            raise ValueError("Observation ID en doublon dans P0")
        ids.add(r["observation_id"])
        val = parse_number(r["value"])
        if r["frequency"] != "monthly" or r["metric"] != "search_interest_index":
            raise ValueError("Format P0 non prevu")
        if r["is_synthetic"].lower() != "false":
            raise ValueError("Donnee synthetique dans P0")
        if not r["normalization_scope_id"] or not r["source_url"]:
            raise ValueError("Provenance ou normalisation absente dans P0")
        country = r["country_iso2"]
        if country:
            if country not in VALID_COUNTRIES:
                raise ValueError(f"Pays inconnu: {country}")
            c = {
                "ingredient": r["topic_id"],
                "country": country,
                "source": r["source"],
                "metric": r["metric"],
                "normalization_scope": r["normalization_scope_id"],
                "date": r["period_start"],
                "value": str(val),
                "is_synthetic": "False",
                "source_url": r["source_url"],
            }
            country_rows.append(c)
            series_country[(c["ingredient"],country,c["normalization_scope"])].append(c["date"])
        else:
            # Le scope renseigne explicitement une comparaison mondiale ;
            # ne jamais attribuer un code pays fictif aux series WORLD.
            if "monde_WORLD" not in r["normalization_scope_id"]:
                raise ValueError("Zone vide sans perimetre WORLD explicite")
            world_rows.append({
                "ingredient": r["topic_id"],
                "segment_type": "world_comparison",
                "segment_id": "WORLD",
                "source": r["source"],
                "metric": r["metric"],
                "normalization_scope": r["normalization_scope_id"],
                "date": r["period_start"],
                "value": str(val),
                "is_synthetic": "False",
                "source_url": r["source_url"],
            })
    for key, dates in series_country.items():
        if len(dates) != len(set(dates)):
            raise ValueError(f"Deux observations meme date: {key}")
    country_rows.sort(key=lambda r: (r["ingredient"],r["country"],r["date"]))
    world_rows.sort(key=lambda r: (r["ingredient"],r["date"]))
    country_cols = ["ingredient", "country", "source", "metric", "normalization_scope", "date", "value", "is_synthetic", "source_url"]
    world_cols = ["ingredient", "segment_type", "segment_id", "source", "metric", "normalization_scope", "date", "value", "is_synthetic", "source_url"]
    write_csv(CLEAN / "google_trends_p0_M1_pays.csv", country_cols, country_rows)
    write_csv(CLEAN / "google_trends_p0_WORLD_separe.csv", world_cols, world_rows)

    # Labels sur SUJETS, pas sur les observations temporelles: pas de fuite de cible vers M1.
    by_topic = defaultdict(list)
    ref_series = defaultdict(list)
    for r in ref:
        parse_number(r["indice_0_100"])
        if r["zone"] not in VALID_COUNTRIES | {"WORLD"}:
            raise ValueError(f"Zone de reference inconnue: {r['zone']}")
        by_topic[r["topic_id"]].append(r)
        ref_series[(r["topic_id"],r["zone"])].append(r)
    topic_rows = []
    for topic, rows in sorted(by_topic.items()):
        label_set = {r["label"] for r in rows}
        if len(label_set) != 1 or next(iter(label_set)) not in {"buzz", "tendance"}:
            raise ValueError(f"Labels incompatibles pour {topic}")
        label = next(iter(label_set))
        zones = sorted({r["zone"] for r in rows})
        topic_rows.append({
            "topic_id":topic,"topic_label":rows[0]["terme"],"reference_label":label,
            "zones":";".join(zones),"n_zones":str(len(zones)),
            "n_observations":str(len(rows)),
            "first_month":min(r["mois"] for r in rows),
            "last_month":max(r["mois"] for r in rows),
            "review_required":"true", "in_food_scope":"false" if topic == "oud" else "true",
            "status":"labels_provisoires_non_valides",
            "source_url_example": rows[0]["source_url"],
        })
    topic_cols = ["topic_id","topic_label","reference_label","zones","n_zones","n_observations","first_month","last_month","review_required","in_food_scope","status","source_url_example"]
    write_csv(CLEAN / "reference_30_sujets_labels_A_REVOIR.csv",topic_cols,topic_rows)
    summaries = []
    for (topic, zone), rows in sorted(ref_series.items()):
        v = [float(r["indice_0_100"]) for r in rows]
        summaries.append({
            "topic_id":topic,"zone":zone,"label_reference":rows[0]["label"],
            "n_months":len(rows),"first_month":min(r["mois"] for r in rows),
            "last_month":max(r["mois"] for r in rows),
            "n_zero_values":sum(x == 0 for x in v),
            "n_inferieur_a_1":sum('inferieur_a_1' in r["quality_flags"] for r in rows),
            "max_value":max(v),"min_value":min(v),"query_original":rows[0]["query_original"],
            "source_url":rows[0]["source_url"],
        })
    write_csv(REPORTS/"reference_30_series_qualite.csv",list(summaries[0]),summaries)

    # Compare P0 et reference sans les fusionner; deux fenetres de normalisation differents.
    ref_map = {(r["topic_id"],r["zone"],r["mois"]): r for r in ref}
    pair = defaultdict(list)
    p0_query, ref_query = {}, {}
    for r in gt:
        country=r["country_iso2"]
        if not country:
            continue
        key=(r["topic_id"],country,r["period_start"][:7])
        other=ref_map.get(key)
        if other is not None:
            label=(r["topic_id"],country)
            pair[label].append(abs(float(r["value"])-float(other["indice_0_100"])))
            p0_query[label] = r["query_original"]
            ref_query[label] = other["query_original"]
    comparison=[]
    for (topic,country),deltas in sorted(pair.items()):
        comparison.append({
            "topic_id":topic,"country":country,"n_overlapping_months":len(deltas),
            "identical_values_count":sum(d<1e-8 for d in deltas),
            "mean_abs_difference_index":round(sum(deltas)/len(deltas),3),
            "p0_query":p0_query[(topic,country)],
            "reference_query":ref_query[(topic,country)],
            "same_query_literal":str(p0_query[(topic,country)]==ref_query[(topic,country)]).lower(),
            "warning":"ne_pas_concatenier_normalisations_differentes",
        })
    write_csv(REPORTS/"comparaison_p0_vs_reference.csv",list(comparison[0]),comparison)
    price_keys={(r["matiere"],r["mois"]) for r in prix}
    if len(price_keys)!=len(prix):
        raise ValueError("Doublons date+matiere dans prix")
    for r in prix:
        price=float(r["valeur"])
        if not math.isfinite(price) or price<=0:
            raise ValueError("Prix ou indice non positif")

    for r in wiki:
        if r["country_iso2"]:
            raise ValueError("Wiki langue non assimilable a un pays")
    checksums={k:sha256(RAW/v) for k,v in FILES.items()}
    audit = {
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "sources":{"google_trends_p0":len(gt),"google_trends_reference":len(ref),"wikipedia":len(wiki),"prix":len(prix)},
        "total_observations":len(gt)+len(ref)+len(wiki)+len(prix),
        "gt_p0":{"topics":len({r['topic_id'] for r in gt}),"countries":sorted({r['country_iso2'] for r in gt if r['country_iso2']}),
            "n_country_series":len(series_country),"n_country_rows":len(country_rows),"n_world_comparison_rows":len(world_rows),
            "n_below_one_flags":sum('inferieur_a_1' in r['quality_flags'] for r in gt)},
        "gt_reference":{"n_topics":len(by_topic),"n_series":len(ref_series),"n_observations":len(ref),
            "label_distribution":dict(Counter(x["reference_label"] for x in topic_rows)),
            "topics_out_of_food_scope":[x["topic_id"] for x in topic_rows if x["in_food_scope"]=="false"],
            "n_below_one_flags":sum('inferieur_a_1' in r['quality_flags'] for r in ref),
            "n_overlapping_series_p0":len(pair)},
        "wiki":{"observations":len(wiki),"countries_inferred":0,"n_wiki_projects":len({r['wiki_project'] for r in wiki})},
        "prices":{"n_series":len({r['serie_id'] for r in prix}),"n_rows":len(prix),"last_date":max(r['mois'] for r in prix),"types":sorted({r['matiere'] for r in prix})},
        "raw_input_sha256":checksums,
        "cleaned_input_sha256":{"google_trends_p0_M1_pays":sha256(CLEAN/"google_trends_p0_M1_pays.csv"),
            "google_trends_p0_WORLD":sha256(CLEAN/"google_trends_p0_WORLD_separe.csv"),
            "reference_30_sujets":sha256(CLEAN/"reference_30_sujets_labels_A_REVOIR.csv")},
        "limitations":[
            "Les labels M2 sont provisoires et un label concerne un sujet entier, pas une zone-date.",
            "Les exports de 2014-2026 et 2019-2026 ont des normalisations non interchangeables.",
            "Les editions linguistiques Wikipedia ne sont pas des pays.",
            "P0 et reference se recoupent: ne pas les compter comme deux jeux independants.",
            "Les fichiers CSV sources d'export bruts cites dans raw_file ne sont pas fournis dans le lot transmis.",
            "Le flag inferieur_a_1 signale des valeurs faibles ou censurees; ne pas les traiter comme des mesures exactes.",
            "Indices Google Trends ne mesurent pas le volume absolu de recherches ni les ventes alimentaires.",
        ]
    }
    REPORTS.mkdir(exist_ok=True)
    (REPORTS/"audit_lot02.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"country_rows":len(country_rows),"world_rows":len(world_rows),"reference_topics":len(topic_rows),"reference_series":len(ref_series),"wiki_rows":len(wiki),"prices":len(prix)},ensure_ascii=False,indent=2))

if __name__ == '__main__':
    main()
