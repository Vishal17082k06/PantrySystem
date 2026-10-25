# Dev log

## Decisions

| Decision | Choice | Why / trade-off |
|---|---|---|
| Dataset | Seeded 5,800-recipe sample of Hugging Face `corbt/all-recipes`, fetched via the public REST API | Real data was reachable, so no sample file was written by hand. Trade-off: license is research-oriented; sample is not the full corpus. |
| Vocabulary | Built from frequent cleaned ingredient phrases (>=12 recipes) plus a hand-written alias table | Simple and explainable. Trade-off: coarse (ground beef = beef). |
| Keep a recipe only if all lines map | Yes | Prevents silently shortened ingredient lists, which would inflate scores. Cost: 5,800 -> 1,596 recipes. |
| Ranking | Deterministic set-based formula | Judges can recompute any score. Alternative: embeddings (more fuzzy, not explainable). Not used. |
| Strictness | Hard cap on missing items + penalty weight | Slider has a visible, predictable effect. |
| Effort | Step count (direction lines), never time | Brief requirement; also avoids unreliable time fields. |
| LLM | Optional, off by default, rewrites facts only, falls back to template | Keeps ranking explainable and the demo working without keys or cost. Not tested against the live API. |
| scikit-learn / sentence-transformers | Not used | Not needed for a set-based score; fewer dependencies to explain. |
| Dependencies | streamlit, pandas, rapidfuzz, pytest | pytest was a dependency beyond the original stack list; it was proposed in the plan and treated as approved when asked to finish. `anthropic` is optional and not in requirements. |

## Things that went wrong and how they were fixed

1. **Noisy vocabulary.** The first auto-built vocabulary contained entries like "pecan halve", "sticks butter", "molasse". Fixed with more noise words, an irregular-plural map, and an alias table.
2. **Silent ingredient loss.** "ground saffron dissolved in 1 tablespoon hot water" collapsed to "water". Fixed by cutting lines at connecting words (in, with, dissolved...). A unit test now covers this.
3. **Over-loose fuzzy matching.** "unicorn tears" matched "corn". Switched from `WRatio` to whole-string `ratio` with a cutoff of 82. Tested.
4. **Non-food recipes** ("Non-Hardening Clay", "Edible Play Dough") appeared in the data. Filtered by title.
5. **The ranker lost to the baseline on "find the source recipe"** (first run: 68% vs 90% top-5). Rather than tune to the metric, we looked at the results: tiny 3-ingredient recipes won because they were 100% covered. That motivated the **pantry-utilization term** (a deliberate fifth term added to the formula proposed in the plan). Weight 0.25 was set once, not swept. The baseline is still ahead on this proxy task, and `docs/eval.md` says so. The ranker is much better at cookability (about 1.5 vs 4.4 missing items).
6. **Effort slider too weak.** With weight 0.15 the results barely changed. Raised to 0.35 for usability; documented in eval.md.

## Process notes (honest)

- The brief asked for tests alongside the code; the unit tests were written **after** the first implementation of each module rather than strictly test-first. They pass (40), and two (utilization, connecting-word cut) were added specifically to lock in bug fixes.
- Python 3.14.6 was used locally, while the brief names 3.11. The code uses nothing newer than 3.10 syntax (`X | None`), but 3.11 itself was not run.
- Competitor descriptions on the "Existing Gap" slide come from public web summaries, not hands-on testing. Verify before presenting.
- The sandbox had no live LLM key, so `llm_why` has not been run against the real API.

## What AI tools helped with what

| Tool | Used for |
|---|---|
| Claude Code (Claude Sonnet 5.5) | Planning, writing the modules/tests/scripts/docs, debugging the issues above, running the evaluation. |
| Web search (via Claude Code) | Checking public descriptions of competitor apps. |

All code is intended to be explained line by line; `docs/explain.md` is the walkthrough. Review it and the code before presenting, since you are responsible for being able to defend every line.
