"""Tests for the FastAPI layer (src/api.py)."""
import pytest
from fastapi.testclient import TestClient

from src.api import app

client = TestClient(app)


def recommend(**body):
    body.setdefault("items", ["chicken", "rice", "onion"])
    return client.post("/api/recommend", json=body)


def test_health_reports_recipe_count():
    data = client.get("/api/health").json()
    assert data["status"] == "ok" and data["recipes"] >= 300


def test_recommend_returns_explained_results():
    r = recommend()
    assert r.status_code == 200
    data = r.json()
    assert 0 < len(data["results"]) <= 8
    first = data["results"][0]
    for key in ("id", "title", "score", "coverage", "have", "missing", "assumed",
                "why", "substitutions", "directions", "raw_ingredients", "steps"):
        assert key in first
    assert first["why"]


def test_typos_are_corrected_and_reported():
    data = recommend(items=["chiken", "tomatos"]).json()
    assert "chicken" in data["pantry"] and "tomato" in data["pantry"]
    assert {"raw": "chiken", "canonical": "chicken"} in data["corrections"]


def test_unknown_items_are_reported_not_guessed():
    data = recommend(items=["chicken", "unicorn tears"]).json()
    assert data["unknown"] == ["unicorn tears"]
    assert data["pantry"] == ["chicken"]


def test_empty_pantry_gives_no_results():
    data = recommend(items=[]).json()
    assert data["results"] == [] and data["pantry"] == []


def test_strictness_one_only_returns_fully_cookable_recipes():
    data = recommend(strictness=1.0).json()
    assert data["max_missing"] == 0
    assert all(r["missing"] == [] for r in data["results"])


def test_diet_filter_is_applied():
    data = recommend(items=["tomato", "onion", "garlic"], diets=["vegan"], strictness=0.0).json()
    assert data["results"]
    assert all("vegan" in r["diet_tags"] for r in data["results"])


def test_substitutions_attached_to_missing_items():
    data = recommend(items=["egg", "flour", "sugar"], strictness=0.0, top_n=20).json()
    subs = [r["substitutions"] for r in data["results"] if r["substitutions"]]
    assert subs, "expected at least one recipe with a known substitution"
    option = next(iter(subs[0].values()))[0]
    assert {"text", "note", "have_all"} <= set(option)


def test_invalid_slider_value_is_rejected():
    assert recommend(strictness=2).status_code == 422
    assert recommend(diets=["keto"]).status_code == 422


def test_suggest_matches_prefix_and_survives_typos():
    names = [s["name"] for s in client.get("/api/suggest", params={"q": "chic"}).json()]
    assert "chicken" in names
    assert client.get("/api/suggest", params={"q": ""}).json() == []


def test_starters_are_common_non_staples():
    names = [s["name"] for s in client.get("/api/starters").json()]
    assert len(names) >= 10
    assert "salt" not in names and "water" not in names


def test_resolved_lines_up_with_each_input_item():
    data = recommend(items=["chiken", "unicorn tears", "Rice"]).json()
    assert [(x["raw"], x["canonical"]) for x in data["resolved"]] == [
        ("chiken", "chicken"), ("unicorn tears", None), ("Rice", "rice")]
    assert data["resolved"][0]["how"] == "fuzzy"


def test_suggest_puts_the_most_common_ingredient_first():
    names = [s["name"] for s in client.get("/api/suggest", params={"q": "chic"}).json()]
    assert names[0] == "chicken"
    counts = [s["count"] for s in client.get("/api/suggest", params={"q": "ch"}).json()]
    prefix_counts = counts[:3]
    assert prefix_counts == sorted(prefix_counts, reverse=True)
