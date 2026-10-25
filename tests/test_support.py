"""Tests for diet tags, substitutions, explanations, and the real dataset."""
import json

from src.diet import diet_tags
from src.explain import explain, template_why
from src.normalize import load_default_vocab
from src.rank import Result, default_recipes_path, load_recipes
from src.substitutions import load_substitutions, suggest


def test_diet_tags_meat_blocks_vegetarian():
    tags = diet_tags(["chicken", "rice"])
    assert "vegetarian" not in tags and "vegan" not in tags


def test_diet_tags_dairy_is_vegetarian_but_not_vegan():
    tags = diet_tags(["milk", "sugar"])
    assert "vegetarian" in tags and "vegan" not in tags


def test_diet_tags_whole_words_only():
    # nutmeg is a spice, not a nut; coconut milk is plant-based.
    assert "nut_free" in diet_tags(["nutmeg", "sugar"])
    assert "vegan" in diet_tags(["coconut milk", "rice"])


def test_diet_tags_peanut_butter_is_not_nut_free():
    assert "nut_free" not in diet_tags(["peanut butter"])


def test_diet_tags_gluten():
    assert "gluten_free" not in diet_tags(["flour", "egg"])
    assert "gluten_free" in diet_tags(["rice", "egg"])


def test_substitutions_prefer_items_you_own():
    table = {"buttermilk": [{"items": ["milk", "vinegar"], "note": "x"},
                            {"items": ["plain yogurt"], "note": "y"}]}
    out = suggest(["buttermilk", "unknown thing"], table, {"plain yogurt"})
    assert out["buttermilk"][0]["text"] == "plain yogurt"
    assert out["buttermilk"][0]["have_all"] is True
    assert "unknown thing" not in out          # no row -> no invented advice


def test_template_explanation_cites_users_ingredients():
    r = Result(1, "Chicken Rice", 0.8, 0.75, 0.8, have=["chicken", "rice"],
               assumed=["salt"], missing=["onion"], key_have=["chicken", "rice"],
               key_total=2, steps=4)
    text = explain(r, {"onion": ["shallot"]})
    assert "chicken and rice" in text and "onion" in text and "swaps" in text


def test_explain_falls_back_to_template_without_llm_flag():
    r = Result(1, "X", 0.5, 1.0, 1.0, have=["egg"], missing=[], key_total=0)
    assert explain(r, {}, use_llm=True) == template_why(r, {})   # flag/env not set


def test_dataset_is_real_and_consistent():
    recipes = load_recipes(default_recipes_path())
    vocab = load_default_vocab()
    assert len(recipes) >= 300
    assert all(r["source"] for r in recipes)
    for r in recipes[:200]:
        assert 3 <= len(r["ingredients"]) <= 14
        assert set(r["ingredients"]) <= vocab.terms
        assert r["steps"] == len(json.loads(r["directions"]))


def test_substitution_table_keys_are_in_vocabulary():
    vocab = load_default_vocab()
    assert set(load_substitutions()) <= vocab.terms
