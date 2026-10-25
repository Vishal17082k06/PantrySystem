"""Curated substitution table: 'missing ingredient' -> things that can stand in.

The table is a small hand-written CSV (data/substitutions.csv) with columns
    missing, substitute, note
A substitute can be several items joined by '+', e.g. 'milk+lemon juice'.
We never invent substitutions: if the table has no row, we say nothing.
"""
import csv
from pathlib import Path


def load_substitutions(path=None) -> dict[str, list[dict]]:
    """Read the CSV into {missing: [{'items': [...], 'note': str}, ...]}."""
    path = path or Path(__file__).resolve().parent.parent / "data" / "substitutions.csv"
    table: dict[str, list[dict]] = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            table.setdefault(row["missing"], []).append(
                {"items": row["substitute"].split("+"), "note": row["note"]})
    return table


def suggest(missing: list[str], table: dict, pantry) -> dict[str, list[dict]]:
    """For each missing item, list substitutes; ones you already own come first.

    Each suggestion: {'text': 'milk + lemon juice', 'note': ..., 'have_all': bool}
    """
    pantry = set(pantry)
    out = {}
    for item in missing:
        options = [{"text": " + ".join(o["items"]), "note": o["note"],
                    "have_all": all(i in pantry for i in o["items"])}
                   for o in table.get(item, [])]
        options.sort(key=lambda o: not o["have_all"])   # owned first (stable)
        if options:
            out[item] = options
    return out


def suggestion_texts(suggestions: dict) -> dict[str, list[str]]:
    """Flatten to {missing: ['text', ...]} for the explanation module."""
    return {k: [o["text"] for o in v] for k, v in suggestions.items()}
