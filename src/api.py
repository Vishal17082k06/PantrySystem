"""FastAPI layer: exposes the existing modules as JSON for the React frontend.

No ranking logic lives here. This file only (1) validates the request,
(2) calls normalize -> rank -> substitutions -> explain, and (3) shapes the
answer as JSON. Run with:  uvicorn src.api:app --reload
"""
import dataclasses
import json
import re
from pathlib import Path
from typing import Literal

import pandas as pd
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from rapidfuzz import fuzz, process

from src.explain import explain, llm_enabled
from src.normalize import load_default_vocab
from src.rank import STAPLES, Settings, default_recipes_path, load_recipes, max_missing, rank
from src.substitutions import load_substitutions, suggest, suggestion_texts

ROOT = Path(__file__).resolve().parent.parent
N_STARTERS = 24
MAX_SUGGESTIONS = 8

# Loaded once at startup (the CSVs are small).
VOCAB = load_default_vocab()
RECIPES = load_recipes(default_recipes_path())
RECIPES_BY_ID = {r["id"]: r for r in RECIPES}
SUBS = load_substitutions()
COUNTS = dict(pd.read_csv(ROOT / "data" / "vocab.csv")[["canonical", "recipe_count"]].values)

app = FastAPI(title="Pantry Matcher API")


class RecommendRequest(BaseModel):
    """What the UI sends. Pydantic rejects out-of-range values with HTTP 422."""
    items: list[str] = Field(default_factory=list, max_length=60)
    strictness: float = Field(0.3, ge=0, le=1)
    effort: float = Field(0.5, ge=0, le=1)
    diets: list[Literal["vegetarian", "vegan", "gluten_free", "nut_free"]] = []
    assume_staples: bool = True
    top_n: int = Field(8, ge=1, le=20)
    use_llm: bool = False


def read_items(raw_items: list[str]):
    """Normalize each typed item. Returns (pantry, unknown, corrections, resolved).

    `resolved` has one entry per input piece, in order, so the UI can show what
    each thing it typed turned into (and remove the right one later).
    """
    pantry, unknown, corrections, resolved = [], [], [], []
    for chunk in raw_items:
        for raw in re.split(r"[,;\n]", chunk):
            raw = raw.strip()
            if not raw:
                continue
            m = VOCAB.match(raw)
            resolved.append({"raw": raw, "canonical": m.canonical, "how": m.how})
            if m.canonical is None:
                if raw not in unknown:
                    unknown.append(raw)
                continue
            if m.canonical not in pantry:
                pantry.append(m.canonical)
            if m.how == "fuzzy":
                corrections.append({"raw": raw, "canonical": m.canonical})
    return pantry, unknown, corrections, resolved


def result_to_json(r, pantry, use_llm: bool) -> dict:
    """Ranker Result + the extras the card needs (why, swaps, steps)."""
    subs = suggest(r.missing, SUBS, pantry)
    recipe = RECIPES_BY_ID[r.recipe_id]
    data = dataclasses.asdict(r)
    data.update(
        id=data.pop("recipe_id"),
        why=explain(r, suggestion_texts(subs), use_llm),
        substitutions=subs,
        raw_ingredients=json.loads(recipe["raw_ingredients"]),
        directions=json.loads(recipe["directions"]),
        diet_tags=sorted(recipe["diet_tags"]),
    )
    return data


@app.get("/api/health")
def health():
    return {"status": "ok", "recipes": len(RECIPES), "llm": llm_enabled()}


@app.post("/api/recommend")
def recommend(req: RecommendRequest):
    pantry, unknown, corrections, resolved = read_items(req.items)
    settings = Settings(req.strictness, req.effort, tuple(req.diets), req.assume_staples)
    results = rank(RECIPES, pantry, settings, req.top_n) if pantry else []
    return {
        "pantry": pantry,
        "unknown": unknown,
        "corrections": corrections,
        "resolved": resolved,
        "max_missing": max_missing(req.strictness),
        "total_recipes": len(RECIPES),
        "results": [result_to_json(r, pantry, req.use_llm) for r in results],
    }


@app.get("/api/suggest")
def suggest_items(q: str = Query("", max_length=40)):
    """Autocomplete: prefix matches first, then word matches, then typo matches."""
    q = q.strip().lower()
    if not q:
        return []
    # name we search on -> canonical ingredient it stands for
    names = {t: t for t in VOCAB.terms} | dict(VOCAB.aliases)
    popular = lambda n: -COUNTS.get(names[n], 0)   # common ingredients first
    hits = sorted((n for n in names if n.startswith(q)), key=popular)
    word_hits = (n for n in names if n not in hits and any(w.startswith(q) for w in n.split()))
    hits += sorted(word_hits, key=popular)
    if len(hits) < MAX_SUGGESTIONS and len(q) >= 3:
        close = process.extract(q, list(names), scorer=fuzz.ratio, score_cutoff=70, limit=5)
        hits += [n for n, _, _ in close if n not in hits]
    out, seen = [], set()
    for n in hits:
        canon = names[n]
        if canon not in seen:
            seen.add(canon)
            out.append({"name": canon, "count": int(COUNTS.get(canon, 0))})
    return out[:MAX_SUGGESTIONS]


@app.get("/api/starters")
def starters():
    """Most common non-staple ingredients, shown as quick-add tiles."""
    ranked = sorted((c for c in VOCAB.terms if c not in STAPLES), key=lambda c: -COUNTS.get(c, 0))
    return [{"name": c, "count": int(COUNTS.get(c, 0))} for c in ranked[:N_STARTERS]]


# In production the built React app is served from the same server.
DIST = ROOT / "frontend" / "dist"
if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="frontend")
