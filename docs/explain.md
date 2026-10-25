# How Pantry Matcher works (plain English)

Read this top to bottom and you can explain every module. The flow is:

```
what you type  ->  normalize.py  ->  canonical items
                                        |
recipes.csv  ----------------------->  rank.py  -> scored results
                                        |
substitutions.csv -> substitutions.py   |
                                        v
                                    explain.py -> "why" text -> app.py shows it
```

## The data (`data/`)

- **recipes.csv**: 1,596 real recipes. Columns: `title`, `ingredients` (clean canonical names, as JSON), `raw_ingredients` (original lines, for display), `directions`, `steps` (count of direction lines), `diet_tags`, `source`.
- **vocab.csv**: the list of ~330 canonical ingredient names (e.g. `tomato`, `chicken breast`) with aliases (e.g. `scallion` means `green onion`). It is the "dictionary" the whole app agrees on.
- **substitutions.csv**: hand-written "if you lack X, try Y" rows with a short note.

Why a vocabulary? Computers compare strings exactly. "2 cups chopped onions" and "onion" are different strings but the same pantry item. Mapping everything to one canonical name makes set comparisons ("do I have this?") reliable.

## `src/normalize.py`: turning messy text into canonical names

`clean(text)` does this to "2 cups chopped onions, divided":
1. lowercase, remove brackets;
2. keep only the part before the first comma and before " or " (so "butter or margarine" becomes butter);
3. cut at connecting words ("saffron **dissolved in** hot water" becomes saffron; otherwise the trailing word "water" would wrongly stand in for it);
4. drop digits, punctuation, units and prep words (cups, chopped, fresh...);
5. singularize the last word (onions becomes onion, tomatoes becomes tomato).

`Vocab.match(text)` then tries, in order:
1. **exact** match against the vocabulary;
2. **alias** match (`scallion` to `green onion`);
3. **suffix** match: drop leading words until something matches ("boned skinless chicken breast" becomes `chicken breast`);
4. **fuzzy** match with **rapidfuzz**: the closest vocabulary word by string similarity (`fuzz.ratio`, needs score of at least 82/100). This fixes typos like "chiken" and "paprica". We use whole-string similarity so that "unicorn tears" does *not* match "corn".
5. Otherwise it returns `None`. We would rather say "not recognized" than guess wrong.

`parse_pantry(text, vocab)` splits your input on commas/newlines/semicolons, matches each piece, removes duplicates, and returns `(found, unknown)`.

## `src/diet.py`: dietary tags

A tag is given only if **no** ingredient contains a forbidden *word* (whole words, so `nutmeg` is not mistaken for `nut`). Example: `vegetarian` is blocked by chicken, beef, fish, gelatin, bouillon, and so on. A few plant-based look-alikes (coconut milk, peanut butter) are exempted from the vegan check. The lists are conservative: if unsure, the recipe is *not* tagged. Tags are computed once when the dataset is built.

## `src/rank.py`: the ranking formula

For a recipe, the ingredients are sorted into three groups:
- **have**: in your pantry;
- **assumed**: staples (salt, pepper, oil, water...) you did not list, when "assume staples" is on;
- **missing**: everything else.

Then:

```
score = 0.40 * coverage
      + 0.40 * importance
      + 0.25 * utilization
      - w3   * missing_penalty
      - 0.35 * effort_gap
```

| Term | Meaning | Example |
|---|---|---|
| **coverage** | share of the recipe's ingredients you have (have + assumed) / total | have 4 of 5 = 0.8 |
| **importance** | like coverage but weighted: an ingredient named in the title counts 2, a staple counts 0.25, others 1. Having the chicken in "Chicken Soup" matters more than having the salt. | |
| **utilization** | share of *your* (non-staple) items the recipe uses. Prevents a 3-ingredient recipe from always beating a richer one that uses more of what you own. | uses 3 of your 5 items = 0.6 |
| **missing_penalty** | `n / (n + 3)`, a number from 0 to 1 that rises with each missing item but flattens out (1 missing = 0.25, 3 = 0.5) | |
| **effort_gap** | how far the recipe's step count is from what the Effort slider asks for, scaled 0 to 1. Target steps = `3 + effort * 12` (slider 0 gives 3 steps, slider 1 gives 15). | |

**Strictness** (0 to 1) does two things:
1. a **hard cap**: recipes with more than `round((1 - strictness) * 5)` missing items are hidden (strictness 1 means zero missing allowed; 0 allows five);
2. it sets `w3 = 0.2 + 0.6 * strictness`, so each missing item costs more as strictness rises.

**Effort** (0 to 1) only moves the target step count (above).

Dietary filters are **hard filters**: a recipe lacking a chosen tag is dropped before scoring.

Results are sorted by score (highest first). Ties: fewer missing items first, then recipe id, so the output is fully deterministic: same input always gives same output, no randomness, no model.

**Baseline** (`baseline_rank`): just counts shared ingredients. Used only in the evaluation as a comparison.

### Why these weights?

They are simple, round numbers chosen by reasoning, not an optimizer. Coverage and importance get equal weight (0.4); utilization is smaller (0.25) because it is a tie-breaker-style nudge; the effort weight was raised to 0.35 after the first value (0.15) barely changed the results when the slider moved. See `docs/eval.md` and `docs/DEVLOG.md` for the story.

## `src/substitutions.py`

Loads the CSV into `{missing item: [options]}`. `suggest()` returns, for each missing item that has a row, its options with the ones **you already own** first. If there is no row, nothing is returned (we never invent a substitution).

## `src/explain.py`

- `template_why()` builds a sentence from ranker facts only: "Uses your chicken and rice - 5 of its 6 ingredients are covered. You still need onion. Possible swaps exist for onion."
- With `PANTRY_LLM=1` and an API key, `llm_why()` asks a model to **reword the same facts**. The prompt tells it to use only those facts. If the call fails for any reason, the template is used. The LLM never sees the ranking logic and cannot change scores.

## `app.py`

Only wiring: sidebar inputs, call `parse_pantry` -> `rank` -> `suggest` -> `explain`, then draw cards. Loading is cached with `st.cache_resource` so the CSVs are read once.

## `scripts/`

- `fetch_data.py`: downloads a seeded random sample of recipes.
- `build_dataset.py`: parses, builds the vocabulary from frequent ingredient phrases (a phrase must appear in at least 12 recipes), keeps only recipes whose lines *all* map, assigns diet tags, writes the CSVs.
- `evaluate.py`: builds synthetic pantries and produces `docs/eval.md`.

## Key terms

- **Deterministic**: same input, same output, always.
- **Fuzzy matching**: matching strings that are *similar*, not identical.
- **Hard filter vs score**: a filter removes items entirely; a score only reorders them.
- **Top-k hit rate**: how often the right answer appears in the first k results.
