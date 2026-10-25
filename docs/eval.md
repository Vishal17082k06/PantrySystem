# Evaluation

All numbers below are produced by `python scripts/evaluate.py` (fixed seed 7), so they can be reproduced exactly.

## Summary (honest reading)

- On the proxy task "recover the source recipe", the raw-overlap baseline is still ahead of Pantry Matcher at every Strictness (see the table below). That task favours the baseline by construction: the pantry is a subset of the source recipe, so raw overlap is close to ideal for it.
- Pantry Matcher is built for a different goal, recipes you can actually cook. On that measure it is far better: its top-5 recipes need about 1.5 missing ingredients on average (Strictness 0), versus more than 4 for the baseline.
- The baseline cannot explain what is missing, suggest substitutions, or be steered. Those are the product's reasons to exist; the numbers here are a check that the ranking is sensible, not a claim of higher accuracy.

## Setup

- **Recipes searched:** 1596 real recipes (`data/recipes.csv`).
- **Task:** "Find the recipe again from a partial pantry." For each test, pick a real recipe, keep 70% of its non-staple ingredients as the pantry, and add 2 random unrelated ingredients as noise. The test passes if the source recipe appears in the top 1 (or top 5) results.
- **Baseline:** rank recipes by the raw count of shared ingredients. No weights, no penalties, no filters.
- **Pantry Matcher:** the full scoring formula (coverage + weighted importance + pantry utilization - missing penalty - effort gap) at default Effort 0.5, no dietary filter, staples assumed.

## Main result: 50 synthetic pantries

| Method | Top-1 | Top-5 |
|---|---|---|
| Baseline (raw ingredient overlap) | 78% | 90% |
| Pantry Matcher, Strictness 0.00 | 50% | 82% |
| Pantry Matcher, Strictness 0.25 | 50% | 82% |
| Pantry Matcher, Strictness 0.50 | 34% | 64% |
| Pantry Matcher, Strictness 0.75 | 14% | 24% |
| Pantry Matcher, Strictness 1.00 | 0% | 0% |

## Larger run for stability: 500 synthetic pantries

| Method | Top-1 | Top-5 |
|---|---|---|
| Baseline (raw ingredient overlap) | 76% | 92% |
| Pantry Matcher, Strictness 0.00 | 53% | 87% |
| Pantry Matcher, Strictness 0.25 | 51% | 84% |
| Pantry Matcher, Strictness 0.50 | 43% | 70% |
| Pantry Matcher, Strictness 0.75 | 23% | 29% |
| Pantry Matcher, Strictness 1.00 | 0% | 0% |

## Does it still work when the pantry has fewer of the dish's ingredients?

(500 pantries per row, distractors added as above.)

| Share of the recipe's ingredients in the pantry | Baseline top-5 | Ours top-5 (Strictness 0.00) |
|---|---|---|
| 50% | 85% | 58% |
| 70% | 92% | 82% |
| 90% | 95% | 90% |

## What the ranker is actually for: recipes you can cook

| Method | Avg missing items in each top-5 recipe | Top-5 recipes with 2 or fewer missing |
|---|---|---|
| Baseline (raw overlap) | 4.44 | 20% |
| Pantry Matcher, Strictness 0.00 | 1.52 | 82% |
| Pantry Matcher, Strictness 0.25 | 1.41 | 86% |
| Pantry Matcher, Strictness 0.50 | 1.17 | 100% |
| Pantry Matcher, Strictness 0.75 | 0.75 | 100% |
| Pantry Matcher, Strictness 1.00 | 0.00 | 100% |

## Effect of the Strictness slider

Strictness is not a quality knob. It expresses intent: low means "I'm happy to buy a few things", high means "use only what I have". It hides recipes that need more than `round((1 - strictness) * 5)` missing ingredients and raises the penalty for each missing one. Because our test pantries are deliberately **incomplete** (they hold only 70% of the source recipe), a high Strictness correctly hides the source recipe, so hit rates fall as Strictness rises. That is the slider doing its job, not the ranker failing.

Over the 50 official pantries:

| Strictness | Avg recipes returned | Avg missing items in top 5 |
|---|---|---|
| 0.00 | 323 | 1.52 |
| 0.25 | 206 | 1.41 |
| 0.50 | 40 | 1.17 |
| 0.75 | 10 | 0.75 |
| 1.00 | 1 | 0.00 |

Example with one pantry (`carrot, chicken, egg, garlic, onion, rice, soy sauce`):

| Strictness | Top 3 |
|---|---|
| 0.0 | Classic Blasted Chicken (missing 0); Shredded Chicken Sandwiches (missing 1); Egg Noodles (missing 1) |
| 0.5 | Classic Blasted Chicken (missing 0); Shredded Chicken Sandwiches (missing 1); Egg Noodles (missing 1) |
| 1.0 | Classic Blasted Chicken (missing 0) |

## Effect of the Effort slider

Same pantry, Strictness 0.25. Effort 0 prefers few steps, Effort 1 prefers more involved recipes (step count, not clock time).

| Effort | Top 3 |
|---|---|
| 0.0 | Classic Blasted Chicken (4 steps); German Rice (3 steps); Egg Drop Soup (2 steps) |
| 0.5 | Classic Blasted Chicken (4 steps); Shredded Chicken Sandwiches (13 steps); Egg Noodles (9 steps) |
| 1.0 | Shredded Chicken Sandwiches (13 steps); Classic Blasted Chicken (4 steps); Italian Pasta (12 steps) |

## Design change found by this evaluation

The first version of the formula had no utilization term. The example pantry showed that tiny recipes such as "chicken, salt, pepper" always ranked first for small pantries, because they are 100% covered. Adding a pantry-utilization term (share of *your* items the recipe uses, weight 0.25) raised Strictness-0 top-5 recovery from 72% to 82% on these same 50 pantries while keeping recipes near-fully cookable. The weight was set once for this reason and was not tuned against the metric.

A second change was made for usability, not accuracy: the Effort weight was raised from 0.15 to 0.35 because the first version barely changed the results when the slider moved. The tables in this file were all generated with the final weights.

## Limitations (please read)

- The source recipe is a proxy for "a good answer". Near-duplicate recipes (many sites publish the same dish) can legitimately outrank it, so true quality is probably a little higher than the top-1 number suggests.
- Pantries are synthetic and built from the same dataset we search. They show the ranker works as designed; they do not prove real users will love the results. No user study was run.
- The dataset is a sample of 1596 recipes, not the full corpus.
- The baseline breaks ties by recipe id, which is arbitrary but fixed.
