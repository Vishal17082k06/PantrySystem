"""Tests for src/rank.py using tiny hand-made recipes."""
import pytest

from src import rank as R
from src.rank import Settings, baseline_rank, rank


def recipe(rid, title, ings, steps=5, tags=()):
    return {"id": rid, "title": title, "ingredients": list(ings),
            "steps": steps, "diet_tags": set(tags), "source": "test"}


RECIPES = [
    recipe(1, "Chicken Rice", ["chicken", "rice", "onion", "salt"], steps=4),
    recipe(2, "Plain Rice", ["rice", "water", "salt"], steps=2,
           tags=["vegetarian", "vegan", "nut_free", "gluten_free"]),
    recipe(3, "Chicken Curry", ["chicken", "curry powder", "onion", "tomato", "cream"], steps=9),
    recipe(4, "Fancy Pie", ["flour", "butter", "apple", "sugar", "egg", "cinnamon"], steps=14),
]


def test_coverage_is_share_of_recipe_ingredients():
    assert R.coverage(3, 4) == 0.75
    assert R.coverage(0, 0) == 0.0


def test_title_ingredient_is_weighted_higher_than_normal_and_staples():
    assert R.ingredient_weight("chicken", "Chicken Rice") == R.KEY_WEIGHT
    assert R.ingredient_weight("onion", "Chicken Rice") == R.NORMAL_WEIGHT
    assert R.ingredient_weight("salt", "Chicken Rice") == R.STAPLE_WEIGHT


def test_title_match_is_whole_word_not_substring():
    # "pea" must not count as a title ingredient of "Peach Pie".
    assert R.ingredient_weight("pea", "Peach Pie") == R.NORMAL_WEIGHT


def test_importance_rewards_covering_key_ingredients():
    rec = RECIPES[0]
    with_chicken = R.importance(rec, {"chicken"})
    with_onion = R.importance(rec, {"onion"})
    assert with_chicken > with_onion


def test_missing_penalty_is_zero_to_one_and_increasing():
    assert R.missing_penalty(0) == 0
    assert 0 < R.missing_penalty(1) < R.missing_penalty(5) < 1


def test_max_missing_shrinks_as_strictness_grows():
    assert R.max_missing(0.0) == 5
    assert R.max_missing(1.0) == 0
    assert R.max_missing(0.5) <= R.max_missing(0.2)


def test_best_fit_ranks_first():
    top = rank(RECIPES, {"chicken", "rice", "onion"}, Settings(strictness=0.5))
    assert top[0].title == "Chicken Rice"


def test_staples_are_assumed_but_listed_separately():
    top = rank(RECIPES, {"rice"}, Settings(strictness=1.0, assume_staples=True))
    plain = next(r for r in top if r.title == "Plain Rice")
    assert plain.missing == [] and set(plain.assumed) == {"water", "salt"}


def test_staples_not_assumed_when_turned_off():
    top = rank(RECIPES, {"rice"}, Settings(strictness=0.0, assume_staples=False))
    plain = next(r for r in top if r.title == "Plain Rice")
    assert set(plain.missing) == {"water", "salt"}


def test_strictness_hides_recipes_with_too_many_missing():
    pantry = {"chicken", "onion"}                       # Curry misses 3 items
    relaxed = [r.title for r in rank(RECIPES, pantry, Settings(strictness=0.0))]
    strict = [r.title for r in rank(RECIPES, pantry, Settings(strictness=1.0))]
    assert "Chicken Curry" in relaxed and "Chicken Curry" not in strict


def test_dietary_filter_is_a_hard_filter():
    top = rank(RECIPES, {"rice", "chicken"}, Settings(strictness=0.0, diets=("vegan",)))
    assert [r.title for r in top] == ["Plain Rice"]


def test_effort_slider_prefers_matching_step_counts():
    pantry = {"chicken", "rice", "onion"}
    quick = Settings(strictness=0.0, effort=0.0)
    long = Settings(strictness=0.0, effort=1.0)
    gap_quick = R.effort_gap(2, quick.effort)
    gap_long = R.effort_gap(2, long.effort)
    assert gap_quick < gap_long
    assert rank(RECIPES, pantry, quick)[0].steps <= rank(RECIPES, pantry, long)[0].steps


def test_ranking_is_deterministic():
    a = rank(RECIPES, {"chicken", "rice"}, Settings(strictness=0.0))
    b = rank(RECIPES, {"rice", "chicken"}, Settings(strictness=0.0))
    assert [r.recipe_id for r in a] == [r.recipe_id for r in b]


def test_no_overlap_means_no_results():
    assert rank(RECIPES, {"unobtainium"}, Settings(strictness=0.0)) == []


def test_baseline_counts_raw_overlap_only():
    ranked = baseline_rank(RECIPES, {"chicken", "rice", "onion"})
    assert ranked[0] == (1, 3)           # Chicken Rice shares all three


def test_results_only_come_from_given_recipes():
    ids = {r["id"] for r in RECIPES}
    assert {r.recipe_id for r in rank(RECIPES, {"rice", "egg"}, Settings(strictness=0.0))} <= ids


def test_utilization_is_share_of_your_items_used_and_ignores_staples():
    assert R.utilization(2, {"chicken", "rice", "onion", "carrot"}) == 0.5
    assert R.utilization(1, {"salt", "rice"}) == 1.0     # salt is a staple
    assert R.utilization(0, set()) == 0.0


def test_recipe_using_more_of_your_items_beats_trivial_full_cover():
    tiny = recipe(10, "Plain Chicken", ["chicken", "salt", "pepper"], steps=4)
    rich = recipe(11, "Chicken Veg Rice", ["chicken", "rice", "carrot", "onion", "salt"], steps=4)
    top = rank([tiny, rich], {"chicken", "rice", "carrot", "onion"}, Settings(strictness=0.5))
    assert top[0].title == "Chicken Veg Rice"
