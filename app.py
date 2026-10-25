"""Pantry Matcher - Streamlit UI.  Run with:  streamlit run app.py

The UI only wires things together; all logic lives in src/.
"""
import json

import pandas as pd
import streamlit as st

from src.diet import ALL_DIETS
from src.explain import explain, llm_enabled
from src.normalize import Vocab, load_default_vocab, parse_pantry
from src.rank import Settings, default_recipes_path, load_recipes, rank
from src.substitutions import load_substitutions, suggest, suggestion_texts

st.set_page_config(page_title="Pantry Matcher", page_icon="🥕", layout="wide")

DIET_LABELS = {"vegetarian": "Vegetarian", "vegan": "Vegan",
               "gluten_free": "Gluten-free", "nut_free": "Nut-free"}
N_CHIPS = 40


@st.cache_resource
def load_data():
    """Load recipes, vocabulary and substitution table once per session."""
    vocab = load_default_vocab()
    recipes = load_recipes(default_recipes_path())
    return vocab, recipes, load_substitutions()


def chip_options(vocab: Vocab) -> list[str]:
    """Most common non-staple ingredients, used as clickable chips."""
    df = pd.read_csv(default_recipes_path().parent / "vocab.csv")
    df = df[df["category"] != "staple"].head(N_CHIPS)
    return list(df["canonical"])


def read_pantry(typed: str, chips: list[str], vocab: Vocab):
    """Combine typed text and chips into a canonical pantry + feedback."""
    found, unknown = parse_pantry(typed, vocab)
    corrections = []
    for piece in [p.strip() for p in typed.replace("\n", ",").replace(";", ",").split(",") if p.strip()]:
        m = vocab.match(piece)
        if m.canonical and m.how == "fuzzy":
            corrections.append(f"{piece} -> {m.canonical}")
    pantry = list(dict.fromkeys(chips + found))
    return pantry, unknown, corrections


def show_result(r, rank_no, pantry, table, use_llm):
    """Render one recommendation card."""
    subs = suggest(r.missing, table, pantry)
    with st.container(border=True):
        left, right = st.columns([4, 1])
        left.subheader(f"{rank_no}. {r.title}")
        right.metric("Match score", f"{r.score:.2f}")
        st.write(explain(r, suggestion_texts(subs), use_llm))

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**You have**")
            st.write(", ".join(r.have) if r.have else "-")
            if r.assumed:
                st.caption("Assumed pantry staples: " + ", ".join(r.assumed))
        with c2:
            st.markdown("**Missing**")
            if not r.missing:
                st.write("Nothing - you can cook this now.")
            for item in r.missing:
                options = subs.get(item)
                if options:
                    best = options[0]
                    owned = " (you have this)" if best["have_all"] else ""
                    st.write(f"- **{item}** - could use {best['text']}{owned}: {best['note']}")
                    for extra in options[1:3]:
                        st.caption(f"   or {extra['text']}: {extra['note']}")
                else:
                    st.write(f"- **{item}** - no substitute in our table")

        with st.expander("Score breakdown and steps"):
            st.write(f"Coverage {r.coverage:.0%} of the recipe's ingredients - "
                     f"weighted importance {r.importance:.0%} - {r.steps} steps")
            full = next(x for x in st.session_state["recipes_by_id"] if x["id"] == r.recipe_id)
            st.markdown("**Ingredients (as written in the source)**")
            for line in json.loads(full["raw_ingredients"]):
                st.write(f"- {line}")
            st.markdown("**Directions**")
            for i, step in enumerate(json.loads(full["directions"]), 1):
                st.write(f"{i}. {step}")
            st.caption(f"Source: {r.source}")


def main():
    vocab, recipes, table = load_data()
    st.session_state["recipes_by_id"] = recipes

    st.title("🥕 Pantry Matcher")
    st.caption("Tell us what is in your kitchen. We rank real recipes by how well they fit, "
               "and explain what is missing and what could stand in for it.")

    with st.sidebar:
        st.header("Your pantry")
        typed = st.text_area("Type ingredients (comma-separated)",
                             placeholder="chicken, rice, tomatos, onion", height=100)
        chips = st.pills("...or tap to add", chip_options(vocab),
                         selection_mode="multi", default=[]) or []
        st.header("Steer the results")
        strictness = st.slider("Strictness", 0.0, 1.0, 0.3, 0.05,
                               help="Left: fine to buy a few things. Right: use only what I have.")
        st.caption("← okay to buy a few things   |   only my items →")
        effort = st.slider("Effort", 0.0, 1.0, 0.5, 0.05,
                           help="Based on the number of steps, not clock time.")
        st.caption("← fewer steps   |   more involved →")
        diets = st.multiselect("Dietary filters", ALL_DIETS,
                               format_func=DIET_LABELS.get)
        assume = st.checkbox("Assume I have salt, pepper, oil and water", value=True)
        use_llm = False
        if llm_enabled():
            use_llm = st.checkbox("Reword explanations with an LLM", value=False,
                                  help="Ranking is unchanged. The LLM only rewrites the facts.")

    pantry, unknown, corrections = read_pantry(typed, chips, vocab)
    if not pantry:
        st.info("Add a few ingredients on the left to get recommendations.")
        return

    st.markdown("**Recognized pantry:** " + ", ".join(pantry))
    if corrections:
        st.caption("Spelling fixed: " + "; ".join(corrections))
    if unknown:
        st.warning("Not recognized (ignored): " + ", ".join(unknown))

    settings = Settings(strictness, effort, tuple(diets), assume)
    results = rank(recipes, pantry, settings, top_n=8)
    if not results:
        st.error("No recipe fits these settings. Try moving Strictness left, "
                 "adding ingredients, or removing a dietary filter.")
        return
    st.caption(f"Showing the top {len(results)} of {len(recipes)} recipes in our dataset.")
    for i, r in enumerate(results, 1):
        show_result(r, i, pantry, table, use_llm)

    st.divider()
    st.caption("Recipes come from a public dataset; we never invent recipes. Dietary tags are "
               "derived from ingredient names and are conservative, but always check labels "
               "if you have an allergy.")


main()
