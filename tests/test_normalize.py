"""Tests for src/normalize.py (small hand-made vocabulary, no dataset needed)."""
import pytest

from src.normalize import Vocab, clean, parse_pantry, singularize


@pytest.fixture
def vocab():
    return Vocab(
        terms=["tomato", "chicken", "chicken breast", "onion", "red onion",
               "green onion", "butter", "sour cream", "egg", "salt"],
        aliases={"scallion": "green onion"},
    )


def test_singularize_common_plurals():
    assert singularize("tomatoes") == "tomato"
    assert singularize("berries") == "berry"
    assert singularize("onions") == "onion"
    assert singularize("radishes") == "radish"


def test_singularize_leaves_tricky_words_alone():
    assert singularize("molasses") == "molasses"
    assert singularize("asparagus") == "asparagus"
    assert singularize("leaves") == "leaf"


def test_clean_strips_quantities_units_and_prep_words():
    assert clean("2 cups chopped onions") == "onion"
    assert clean("1/2 tsp. salt") == "salt"


def test_clean_keeps_first_option_and_first_part():
    assert clean("butter or margarine") == "butter"
    assert clean("cream cheese, cubed") == "cream cheese"


def test_clean_cuts_at_connecting_words():
    # Without the cut, this would collapse to just "water".
    assert clean("saffron dissolved in 1 tablespoon hot water") == "saffron"


def test_exact_and_plural_match(vocab):
    assert vocab.match("Tomatoes").canonical == "tomato"
    assert vocab.match("tomatos").canonical == "tomato"   # typo via singularize


def test_alias_match(vocab):
    m = vocab.match("scallions")
    assert (m.canonical, m.how) == ("green onion", "alias")


def test_fuzzy_match_fixes_typos(vocab):
    m = vocab.match("chiken")
    assert m.canonical == "chicken" and m.how == "fuzzy"


def test_unknown_words_are_not_guessed(vocab):
    assert vocab.match("unicorn tears").canonical is None
    assert vocab.match("").canonical is None


def test_suffix_match_drops_leading_modifiers(vocab):
    assert vocab.match("boned skinless chicken breasts").canonical == "chicken breast"


def test_longer_term_wins_over_head_word(vocab):
    # "sour cream" must not be reduced to something shorter.
    assert vocab.match("sour cream").canonical == "sour cream"


def test_parse_pantry_splits_dedupes_and_reports_unknowns(vocab):
    found, unknown = parse_pantry("tomatos, egg\nEggs; blorp", vocab)
    assert found == ["tomato", "egg"]
    assert unknown == ["blorp"]
