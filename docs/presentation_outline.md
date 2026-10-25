# Presentation outline: Pantry Matcher

Suggested length: 5-7 minutes + live demo.

## 1. Problem
- You open the pantry, see random ingredients, and have no idea what to cook.
- Wasted ingredients, last-minute extra shopping, and decision fatigue.

## 2. Target users
- Students and shared households cooking from whatever is on hand.
- Anyone who wants to use up what they have before buying more.
- People with dietary needs who must filter results.

## 3. Existing gap
Tools people use today (**as publicly described; verify each against the current app before presenting, we did not test them hands-on**):

| Tool | What it does well | Gap Pantry Matcher targets |
|---|---|---|
| **SuperCook** | Pick pantry ingredients from a large list; shows recipes you can make with them. | In our review of its public descriptions we found no per-recipe explanation of what is missing or a substitution feature. |
| **BigOven** ("Use Up Leftovers") | Suggests meals from a few ingredients you choose. | Described as limited to a few ingredients; no steerable strictness or explained substitutions found in public material. |
| **Yummly** | Large catalogue, diet filters, include/exclude ingredient search. | Search and filters, but no ranked "fit" explanation or pantry-aware substitutions found in public material. |

The specific gaps we address:
1. **Explained missing items**: named per recipe, not just a count.
2. **Substitutions** you may already own.
3. **Steerable ranking**: Strictness and Effort sliders.
4. **Published evaluation numbers**, including our weaknesses.

(Speaker note: if asked, say we compared against public descriptions and a raw-overlap baseline, not against these apps' internals.)

## 4. Solution
- Enter pantry; get real recipes ranked by fit with a "why" line.
- You have / Missing / Substitutions on every card.
- Sliders + diet filters.

## 5. Innovation
- Deterministic, explainable score (show the formula on one slide).
- LLM only rewords facts (optional); never ranks, never invents.
- Pantry-utilization term, found through our own evaluation.
- Honest evaluation: simple baseline wins "find the source recipe"; we win on cookability (4.4 vs 1.4 missing).

## 6. Architecture
```
input -> normalize (clean + fuzzy) -> rank (formula, filters) -> substitutions -> explain -> UI
                         ^                    ^
                    vocab.csv            recipes.csv (real dataset)
```

## 7. Tech
Python, Streamlit, pandas, rapidfuzz, pytest; seeded sample of a public RecipeNLG-style dataset (1,596 recipes); optional LLM behind a flag.

## 8. Live demo
1. Type a pantry with typos (`chiken, rice, tomatos, onion, garlic`).
2. Open a card: why-line, missing item, substitution marked as owned.
3. Strictness slider: show results shrink to fully cookable.
4. Effort slider: short vs long recipes.
5. Vegan filter.
6. (Optional) Show `docs/eval.md`.

## 9. Future scope
- Larger dataset and a bigger, reviewed substitution table.
- Learn weights from user feedback (still keeping explanations).
- Quantities-aware matching ("you have 1 egg, recipe needs 3").
- Smarter ingredient hierarchy (ground beef vs steak).
- A small user study to validate recommendation quality.
