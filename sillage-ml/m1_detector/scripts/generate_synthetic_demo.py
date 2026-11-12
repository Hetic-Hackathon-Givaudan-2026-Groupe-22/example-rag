"""Génère uniquement des données FICTIVES pour tester l'exécution."""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

OUT = Path("data/raw/demo_SYNTHETIC.csv")


def main():
    rng = random.Random(42)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["ingredient", "country", "date", "source", "metric", "value", "normalization_scope", "is_synthetic", "source_url"])
        w.writeheader()
        for country, lag in [("JP", 0), ("FR", 9), ("US", 18)]:
            for week in range(80):
                value = 15 + rng.uniform(-2, 2)
                if week >= 30+lag:
                    value += min((week-(30+lag))*3.5, 40)
                w.writerow({"ingredient": "matcha", "country": country,
                            "date": (date(2024, 1, 1)+timedelta(weeks=week)).isoformat(),
                            "source": "SYNTHETIC", "metric": "synthetic_interest",
                            "value": round(value, 3),
                            "normalization_scope": f"synthetic_matcha_{country}_separate",
                            "is_synthetic": "true", "source_url": ""})
    print(f"ATTENTION : données fictives -> {OUT}")

if __name__ == "__main__":
    main()
