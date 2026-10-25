# Pantry Matcher: Project Report

Theme: **AI for Everyday Life - Smart Recommendations**

## 1. Problem

Most people have stood in front of the pantry or fridge with a handful of ingredients and no idea what to cook. Recipe apps and sites let you search by dish, but they rarely answer the question people actually have: *"Given what I have, what can I make, what would I still need, and could I swap something I already own?"*

## 2. Solution

Pantry Matcher takes the ingredients you have (typed, comma-separated, or tapped from chips) and recommends recipes **only from a real recipe dataset**, ranked by fit. For every recommendation it shows:

- a match score and a plain-language "why this recipe" line that cites your own ingredients;
- a **You have** list and a **Missing** list;
- a **substitution** suggestion for each missing item, preferring things you already own;
- the original ingredient lines and directions from the source.

Two sliders let you steer the ranking:
- **Strictness**: from "okay to buy a few things" to "use only what I have";
- **Effort**: from fewer steps to more involved (measured by step count, not clock time).

Dietary filters (vegetarian, vegan, gluten-free, nut-free) are applied from ingredient tags.

## 3. Innovation / USP

1. **Explained gaps.** Every missing ingredient is named, and where our curated table has a row, a substitute is offered, with the ones you already own listed first.
2. **Steerable, deterministic ranking.** The score is a short formula over sets (coverage, weighted importance, pantry utilization, missing penalty, effort gap). Anyone can recompute it by hand. Sliders change the weights and a hard cap, and the effect is visible.
3. **AI where it helps, not where it hurts.** An LLM is optional and only *rewords* retrieved facts. It cannot rank, invent recipes, or add ingredients.
4. **Honest evaluation.** We publish reproducible numbers against a baseline, including where we lose (see below).
5. **No invented recipes.** Every result is a real recipe from the dataset.

### Evaluation summary (full details in [eval.md](eval.md))

50 synthetic pantries built from real recipes (70% of a recipe's ingredients plus 2 unrelated items), fixed seed:

| Method | Top-1 | Top-5 | Avg missing items in top-5 |
|---|---|---|---|
| Baseline (raw ingredient overlap) | 78% | 90% | 4.44 |
| Pantry Matcher (Strictness 0.25) | 50% | 82% | 1.41 |

On the proxy task "recover the source recipe", the simple baseline is better, which is expected because the pantry is a subset of the source recipe. Pantry Matcher is designed for a different goal, recipes you can actually cook, and there its top results need about 1.4 missing ingredients versus 4.4 for the baseline. We do not claim higher accuracy than the baseline; we claim *more useful, explainable, steerable* recommendations. No user study was run.

## 4. Tech stack

- **Python** (written for 3.11+, tested on 3.14.6)
- **React 18 + Vite**: main UI (plain CSS), served with the API by FastAPI
- **FastAPI**: JSON API wrapping the ranking code
- **Streamlit**: original UI, kept as a fallback
- **pandas**: loading data
- **rapidfuzz**: typo-tolerant ingredient matching
- **pytest**: 53 tests
- **Data:** seeded sample of the public `corbt/all-recipes` dataset (RecipeNLG-style), 1,596 recipes after cleaning
- **Optional:** an LLM (Anthropic API) behind a flag for wording only

scikit-learn and sentence-transformers were considered and deliberately not used: a plain set-based score is easier to explain and needed neither.

## 5. Demo (software-only)

1. Start the app (`python -m uvicorn src.api:app --port 8000`, then open http://localhost:8000).
2. Type `chiken, rice, tomatos, onion, garlic` and note the spelling fixes shown under "Recognized pantry".
3. Read one card: score, "why" line, You have / Missing, a substitution marked "(you have this)".
4. Move **Strictness** to the right: results with many missing items disappear; at 1.0 only fully cookable recipes remain.
5. Move **Effort**: short recipes (2-4 steps) rise on the left; longer ones on the right.
6. Turn on **Vegan**: results change and meat/dairy recipes vanish.
7. Open "Score breakdown and steps" to show the real source recipe.

No camera or hardware is needed.

## 6. Source code

All code is in this repository: `app.py`, `src/` (normalize, rank, substitutions, explain, diet), `scripts/`, `tests/`, `data/`. See [README.md](README.md) to run it and [explain.md](explain.md) for a walkthrough of every module.

## Limitations

- 1,596 recipes is a sample, not the full corpus; some pantries will have few good matches.
- Ingredient mapping is simplified (e.g. ground beef and beef are the same item).
- The substitution table is small (115 rows) and hand-written; it covers common swaps only.
- Diet tags are heuristics from ingredient names, not allergy advice.
- Dataset license terms (non-commercial research) apply.
