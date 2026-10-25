"""Download a seeded random sample of real recipes (no extra dependencies).

Source: Hugging Face dataset `corbt/all-recipes` (RecipeNLG-style recipes:
title + ingredient lines + directions), read through the public
datasets-server REST API, 100 rows per request.

Usage: python scripts/fetch_data.py [n_requests]
Output: data/raw/recipes_raw.jsonl  (git-ignored; rebuilt by this script)
"""
import json
import random
import sys
import time
import urllib.request
from pathlib import Path

DATASET = "corbt/all-recipes"
TOTAL_ROWS = 2_000_000          # dataset has ~2.1M rows; stay safely inside
URL = ("https://datasets-server.huggingface.co/rows?dataset=" + DATASET +
       "&config=default&split=train&offset={offset}&length=100")
OUT = Path(__file__).resolve().parent.parent / "data" / "raw" / "recipes_raw.jsonl"


def fetch_chunk(offset: int) -> list[str]:
    """Return the raw recipe texts for 100 rows starting at `offset`."""
    for attempt in range(4):
        try:
            with urllib.request.urlopen(URL.format(offset=offset), timeout=60) as r:
                data = json.load(r)
            return [row["row"]["input"] for row in data["rows"]]
        except Exception as exc:  # network hiccup / rate limit: back off and retry
            print(f"  offset {offset} attempt {attempt + 1} failed: {exc}")
            time.sleep(3 * (attempt + 1))
    return []


def main(n_requests: int) -> None:
    rng = random.Random(42)  # fixed seed -> same sample every run
    offsets = rng.sample(range(0, TOTAL_ROWS, 100), n_requests)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(OUT, "w", encoding="utf-8") as f:
        for i, off in enumerate(offsets, 1):
            for text in fetch_chunk(off):
                f.write(json.dumps({"text": text}) + "\n")
                count += 1
            print(f"{i}/{n_requests} chunks, {count} recipes")
            time.sleep(0.5)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 60)
