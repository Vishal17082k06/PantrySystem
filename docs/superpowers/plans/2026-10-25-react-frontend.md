# React Frontend Implementation Plan

**Goal:** A distinctive React UI for Pantry Matcher backed by a thin FastAPI wrapper around `src/`.

**Architecture:** `src/api.py` exposes JSON endpoints over the existing normalize/rank/substitutions/explain modules (no logic changes). `frontend/` (Vite + React, plain CSS) calls them; in production FastAPI serves `frontend/dist`.

**Tech Stack:** FastAPI, uvicorn, httpx (tests); React 18, Vite, @fontsource fonts.

## Global constraints
- Software-only demo; no invented recipes; no financial/India-specific/time-habit content; effort = step count.
- Visual system: enamelware (cobalt/white, saffron, basil = have, tomato = missing); signature = jar shelf + jar gauge.
- Accessibility floor: keyboard focus, labels, reduced-motion, mobile layout.

## Tasks
1. API + tests (`src/api.py`, `tests/test_api.py`): POST /api/recommend, GET /api/suggest?q=, GET /api/starters, GET /api/health.
2. Frontend scaffold (`frontend/package.json`, `vite.config.js`, `index.html`, fonts, tokens.css).
3. Components: Shelf/Jar, PantryInput (autocomplete + corrections), Controls (sliders, diets), RecipeCard (jar gauge, substitutions, steps, shopping list), empty/loading/error states.
4. Build, run end-to-end, screenshot, fix, update docs.
