"""Deterministic recipe ranking.

    score = w1*coverage + w2*importance + w5*utilization
            - w3*missing_penalty - w4*effort_gap

utilization is the 5th term (added after testing, see docs/DEVLOG.md): the
share of YOUR ingredients that the recipe uses. Without it, tiny recipes such
as "chicken, salt, pepper" always win for a small pantry.

Everything here is plain arithmetic on sets, so any score can be explained
line by line. No randomness, no model calls.
"""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from src.normalize import singularize

# Ingredients most kitchens already have. Counted as "assumed" (not missing)
# when Settings.assume_staples is on.
STAPLES = {"salt", "pepper", "black pepper", "water", "oil", "vegetable oil",
           "olive oil", "cooking spray"}

STAPLE_WEIGHT = 0.25   # staples matter little when judging fit
KEY_WEIGHT = 2.0       # ingredient named in the recipe title ("Chicken Soup")
NORMAL_WEIGHT = 1.0

W_COVERAGE = 0.4       # w1: share of recipe ingredients you have
W_IMPORTANCE = 0.4     # w2: share of *important* ingredients you have
W_UTILIZATION = 0.25   # w5: share of YOUR ingredients the recipe uses
W_EFFORT = 0.35        # w4: how far the step count is from your preference
MAX_STEPS_SCALE = 15   # step counts are compared on a 0..15 scale
MAX_MISSING_AT_ZERO = 5  # Strictness 0 allows up to 5 missing ingredients


@dataclass
class Settings:
    strictness: float = 0.3      # 0 = okay to buy things .. 1 = only my items
    effort: float = 0.5          # 0 = few steps .. 1 = more involved
    diets: tuple = ()            # e.g. ("vegetarian", "nut_free")
    assume_staples: bool = True  # treat salt/oil/water... as always available


@dataclass
class Result:
    recipe_id: int
    title: str
    score: float
    coverage: float
    importance: float
    have: list = field(default_factory=list)      # recipe ingredients you listed
    assumed: list = field(default_factory=list)   # staples we assumed you own
    missing: list = field(default_factory=list)
    key_have: list = field(default_factory=list)  # title ingredients you have
    key_total: int = 0
    steps: int = 0
    source: str = ""


# ---------- small building blocks (each one is easy to explain) ----------

def load_recipes(path) -> list[dict]:
    """Read recipes.csv into a list of dicts with parsed ingredient lists."""
    df = pd.read_csv(path)
    df["ingredients"] = df["ingredients"].apply(json.loads)
    df["diet_tags"] = df["diet_tags"].fillna("").apply(
        lambda s: set(filter(None, s.split("|"))))
    return df.to_dict("records")


def ingredient_weight(ing: str, title: str) -> float:
    """Key (in title) = 2, staple = 0.25, everything else = 1."""
    if ing in STAPLES:
        return STAPLE_WEIGHT
    title_words = {singularize(w) for w in re.findall(r"[a-z]+", title.lower())}
    if title_words & set(ing.split()):
        return KEY_WEIGHT
    return NORMAL_WEIGHT


def split_ingredients(recipe: dict, pantry: set, assume_staples: bool):
    """Sort recipe ingredients into have / assumed / missing (order kept)."""
    have, assumed, missing = [], [], []
    for ing in recipe["ingredients"]:
        if ing in pantry:
            have.append(ing)
        elif assume_staples and ing in STAPLES:
            assumed.append(ing)
        else:
            missing.append(ing)
    return have, assumed, missing


def coverage(n_have: int, n_total: int) -> float:
    """Share of the recipe's ingredients that are covered (0..1)."""
    return n_have / n_total if n_total else 0.0


def importance(recipe: dict, covered: set) -> float:
    """Weighted share: covering 'chicken' in Chicken Soup counts more than 'salt'."""
    weights = {i: ingredient_weight(i, recipe["title"]) for i in recipe["ingredients"]}
    total = sum(weights.values())
    return sum(w for i, w in weights.items() if i in covered) / total if total else 0.0


def utilization(n_used: int, pantry: set) -> float:
    """Share of the user's own (non-staple) ingredients this recipe uses."""
    mine = [p for p in pantry if p not in STAPLES]
    return n_used / len(mine) if mine else 0.0


def missing_penalty(n_missing: int) -> float:
    """Squash missing count into 0..1: 0->0, 1->0.25, 3->0.5, 9->0.75."""
    return n_missing / (n_missing + 3)


def effort_gap(steps: int, effort: float) -> float:
    """Distance between the recipe's step count and the wanted step count."""
    target = 3 + effort * 12                      # slider 0..1 -> 3..15 steps
    return min(abs(steps - target) / MAX_STEPS_SCALE, 1.0)


def max_missing(strictness: float) -> int:
    """Hard cap on missing ingredients: strictness 1 -> 0, strictness 0 -> 5."""
    return round((1 - strictness) * MAX_MISSING_AT_ZERO)


def penalty_weight(strictness: float) -> float:
    """w3 grows with strictness: 0.2 (relaxed) .. 0.8 (strict)."""
    return 0.2 + 0.6 * strictness


# ---------- the ranker ----------

def score_recipe(recipe: dict, pantry: set, s: Settings) -> Result | None:
    """Score one recipe; None if it is filtered out."""
    if not set(s.diets) <= recipe["diet_tags"]:
        return None                                # dietary filter (hard)
    have, assumed, missing = split_ingredients(recipe, pantry, s.assume_staples)
    if not have:
        return None                                # nothing in common
    if len(missing) > max_missing(s.strictness):
        return None                                # strictness cap (hard)
    covered = set(have) | set(assumed)
    cov = coverage(len(covered), len(recipe["ingredients"]))
    imp = importance(recipe, covered)
    used = len([h for h in have if h not in STAPLES])
    score = (W_COVERAGE * cov + W_IMPORTANCE * imp
             + W_UTILIZATION * utilization(used, pantry)
             - penalty_weight(s.strictness) * missing_penalty(len(missing))
             - W_EFFORT * effort_gap(recipe["steps"], s.effort))
    keys = [i for i in recipe["ingredients"]
            if ingredient_weight(i, recipe["title"]) == KEY_WEIGHT]
    return Result(recipe["id"], recipe["title"], round(score, 4), round(cov, 3),
                  round(imp, 3), have, assumed, missing,
                  [k for k in keys if k in covered], len(keys),
                  recipe["steps"], recipe.get("source", ""))


def rank(recipes: list[dict], pantry, settings: Settings | None = None,
         top_n: int = 10) -> list[Result]:
    """Return the best `top_n` recipes, best first. Ties: fewer missing, then id."""
    s = settings or Settings()
    pantry = set(pantry)
    results = [r for rec in recipes if (r := score_recipe(rec, pantry, s))]
    results.sort(key=lambda r: (-r.score, len(r.missing), r.recipe_id))
    return results[:top_n]


def baseline_rank(recipes: list[dict], pantry, top_n: int = 10) -> list[tuple]:
    """Baseline for the evaluation: just count raw ingredient overlap.

    Returns (recipe_id, overlap) pairs. No weights, no penalties, no filters.
    Ties are broken by recipe id (arbitrary, but fixed).
    """
    pantry = set(pantry)
    scored = [(rec["id"], len(pantry & set(rec["ingredients"]))) for rec in recipes]
    scored = [x for x in scored if x[1] > 0]
    scored.sort(key=lambda x: (-x[1], x[0]))
    return scored[:top_n]


def default_recipes_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "recipes.csv"
