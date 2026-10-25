# Pantry Matcher: setup and run

## What it does

Enter pantry items (typed, comma-separated, or tapped from chips). The app recommends recipes **only from a real dataset**, ranked by fit. Each recipe shows a match score, a "you have" list, a "missing" list, suggested substitutions for each missing item, and a plain-language "why this recipe" line. Strictness and Effort sliders and dietary filters (vegetarian, vegan, gluten-free, nut-free) steer the results.

## Setup

Requires Python 3.11+ (developed and tested on Python 3.14.6 on Windows; 3.11 was not tested directly).

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows;  source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
```

## Run the React app (recommended UI)

Needs Node 18+ (built with Node 22).

```bash
cd frontend
npm install
npm run build        # creates frontend/dist
cd ..
python -m uvicorn src.api:app --port 8000
```

Open http://localhost:8000. FastAPI serves both the JSON API (`/api/...`) and the built React app.

**Developing the UI** (hot reload): run the API as above, then in a second terminal `cd frontend && npm run dev` and open http://localhost:5173. Vite forwards `/api` calls to port 8000.

If port 8000 is already in use on your machine, pick another (`--port 8010`) and open that port instead. For hot reload, change the proxy target in `frontend/vite.config.js` to match.

## Run the Streamlit app (original UI, still works)

```bash
streamlit run app.py
```

Open the URL Streamlit prints (usually http://localhost:8501).

## Run the tests

```bash
python -m pytest
```

53 tests cover normalization, ranking, diet tags, substitutions, explanations, dataset consistency and the API.

## Reproduce the evaluation

```bash
python scripts/evaluate.py      # writes docs/eval.md
```

## Rebuild the dataset (optional)

`data/recipes.csv`, `data/vocab.csv` are committed, so you do not need to do this. To rebuild from scratch:

```bash
python scripts/fetch_data.py 60      # downloads ~5,800 recipes to data/raw/ (needs internet)
python scripts/build_dataset.py      # builds data/recipes.csv + data/vocab.csv
```

## Data source and honesty notes

- **Dataset:** a seeded random sample of the Hugging Face dataset [`corbt/all-recipes`](https://huggingface.co/datasets/corbt/all-recipes), which has RecipeNLG-style recipes (title, ingredient lines, directions). We downloaded it through the public API, so **no sample or synthetic recipes were written by us**. The dataset's original license terms (RecipeNLG is intended for non-commercial research use) apply; check them before any commercial use.
- **Filtering:** we keep a recipe only if *every* ingredient line maps into our vocabulary, so ingredient lists are never silently shortened. This reduces ~5,800 raw recipes to 1,596. Two craft entries (clay, play dough) were removed.
- **Steps** are the number of direction lines in the source (used as the Effort measure; we do not use cooking time).
- **Substitutions** are a small hand-written table (`data/substitutions.csv`, 115 rows). If the table has no row for an ingredient, the app says so.
- **Diet tags** are derived from ingredient words and are intentionally conservative (ambiguous items such as bouillon or Worcestershire count as non-vegetarian). They are a convenience, not allergy advice.
- **No nutrition or health claims** are made anywhere.

## Optional: LLM-written explanations

By default the "why" line is a template filled from facts. To let an LLM reword it:

```bash
pip install anthropic
set ANTHROPIC_API_KEY=your-key       # PowerShell: $env:ANTHROPIC_API_KEY="your-key"
set PANTRY_LLM=1
streamlit run app.py                 # a checkbox appears in the sidebar
```

The model gets only the retrieved facts (recipe title, your items, missing items, substitutions) and cannot affect ranking. Each call sends those facts to an external service and may cost money; it is off unless you set both variables. If the call fails, the template text is used. This path has not been exercised against the live API in development (no key was used).

## Layout

```
app.py                 Streamlit UI (wiring only)
src/api.py             FastAPI JSON layer for the React UI
frontend/              React + Vite UI (src/components, src/styles)
src/normalize.py       text -> canonical ingredient (cleaning, fuzzy match)
src/rank.py            scoring formula, filters, baseline
src/substitutions.py   substitution lookup
src/explain.py         "why" text (+ optional LLM)
src/diet.py            dietary tags from ingredient words
data/                  recipes.csv, vocab.csv, substitutions.csv
scripts/               fetch_data.py, build_dataset.py, evaluate.py
tests/                 53 tests
docs/                  report, outline, explain, eval, devlog
```
