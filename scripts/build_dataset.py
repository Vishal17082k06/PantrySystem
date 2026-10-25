"""Turn raw recipes into data/vocab.csv and data/recipes.csv.

Steps
 1. Parse each raw text into title / ingredient lines / directions.
 2. Count cleaned ingredient phrases -> frequent ones become the vocabulary.
 3. Map every ingredient line onto the vocabulary. A recipe is kept ONLY if
    every line maps (so ingredient lists are complete, never silently cut).
 4. Derive diet tags from the normalized ingredients.

Usage: python scripts/build_dataset.py        (after scripts/fetch_data.py)
"""
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.diet import diet_tags          # noqa: E402
from src.normalize import Vocab, clean  # noqa: E402
from src.rank import STAPLES            # noqa: E402

RAW = ROOT / "data" / "raw" / "recipes_raw.jsonl"
MIN_RECIPES_PER_TERM = 12      # a phrase must appear this often to join the vocab
MAX_TERM_WORDS = 3
MAX_RECIPES = 2500
SOURCE = "corbt/all-recipes (RecipeNLG-style, Hugging Face)"

# Hand-written synonyms (alias -> canonical). Dropped if canonical isn't in vocab.
ALIASES = {
    # regional / spelling synonyms
    "scallion": "green onion", "spring onion": "green onion",
    "coriander": "cilantro", "aubergine": "eggplant", "courgette": "zucchini",
    "capsicum": "bell pepper", "garbanzo bean": "chickpea", "prawn": "shrimp",
    "cornflour": "cornstarch", "bicarbonate soda": "baking soda",
    "double cream": "heavy cream", "mayo": "mayonnaise", "catsup": "ketchup",
    "oleo": "margarine", "crabmeat": "crab meat", "cayenne": "cayenne pepper",
    # variants that should count as the same pantry item
    "icing sugar": "powdered sugar", "confectioner sugar": "powdered sugar",
    "confectioners sugar": "powdered sugar", "caster sugar": "sugar",
    "white sugar": "sugar", "granulated sugar": "sugar",
    "light brown sugar": "brown sugar", "dark brown sugar": "brown sugar",
    "all purpose flour": "flour", "plain flour": "flour", "wheat flour": "flour",
    "unsalted butter": "butter", "cold butter": "butter", "soft butter": "butter",
    "vanilla extract": "vanilla", "vanilla flavoring": "vanilla",
    "sharp cheddar cheese": "cheddar cheese", "sharp cheese": "cheese",
    "parmesan": "parmesan cheese", "yellow onion": "onion",
    "heavy whipping cream": "heavy cream", "whipping cream": "heavy cream",
    "dry yeast": "yeast", "active dry yeast": "yeast",
    "kosher salt": "salt", "sea salt": "salt", "coarse salt": "salt",
    "cooking oil": "vegetable oil", "salad oil": "vegetable oil",
    "canola oil": "vegetable oil", "chicken stock": "chicken broth",
    "vegetable stock": "vegetable broth", "beaten egg": "egg",
    "quick oat": "oat", "quick cooking oat": "oat", "rolled oat": "oat",
    "oatmeal": "oat", "breadcrumb": "bread crumb", "dry bread crumb": "bread crumb",
    "dill weed": "dill", "parsley flake": "parsley", "flat leaf parsley": "parsley",
    "lemon rind": "lemon zest", "lemon peel": "lemon zest",
    "green pepper": "bell pepper", "green bell pepper": "bell pepper",
    "red bell pepper": "bell pepper", "jalapeno pepper": "jalapeno",
    "unsweetened cocoa powder": "cocoa", "cocoa powder": "cocoa",
    "semisweet chocolate chip": "chocolate chip", "creamy peanut butter": "peanut butter",
    "yukon gold potato": "potato", "russet potato": "potato", "red potato": "potato",
    "mashed banana": "banana", "skim milk": "milk", "sweet milk": "milk",
    "pet milk": "evaporated milk", "eagle brand milk": "sweetened condensed milk",
    "condensed milk": "sweetened condensed milk", "juice lemon": "lemon juice",
    "warm water": "water", "hot water": "water", "cold water": "water",
    "boiling water": "water", "basil leaf": "basil", "thyme leaf": "thyme",
    "chicken breast half": "chicken breast", "graham cracker crumb": "graham cracker",
    "tomatoe": "tomato", "potatoe": "potato",
    "white flour": "flour", "mint leaf": "mint", "cilantro leaf": "cilantro",
    "parsley leaf": "parsley", "hard boiled egg": "egg", "boiled egg": "egg",
    "celery rib": "celery", "black pepper": "pepper", "white onion": "onion",
    "sweet onion": "onion", "dry red wine": "red wine", "dry white wine": "white wine",
    "broccoli floret": "broccoli", "taco seasoning mix": "taco seasoning",
    "pitted date": "date",
}
# Phrases that are not real ingredients (too vague). Recipes using them are skipped.
BLOCKED = {"white", "soda", "filling", "topping", "fruit", "vegetable", "none egg",
           "mixed vegetable", "ice", "ice cube", "meat", "crust", "sweet", "none"}


# The corpus contains a few craft recipes (clay, play dough...). Not food -> skip.
NON_FOOD_TITLE = re.compile(
    r"\b(clay|play ?dough|slime|glue|soap|potpourri|ornaments?|paint|putty|"
    r"wallpaper|modeling|lotion|shampoo)\b", re.I)


def parse_recipe(text: str):
    """Split raw text into (title, ingredient_lines, directions) or None."""
    if "\n\nIngredients:\n" not in text or "\n\nDirections:\n" not in text:
        return None
    head, rest = text.split("\n\nIngredients:\n", 1)
    ing_block, dir_block = rest.split("\n\nDirections:\n", 1)
    title = head.strip().encode("ascii", "ignore").decode().strip()
    lines = [l[2:].strip() for l in ing_block.splitlines() if l.startswith("- ")]
    steps = [l[2:].strip() for l in dir_block.splitlines() if l.startswith("- ")]
    # "salt and pepper" is two ingredients; split it so neither is lost.
    expanded = []
    for l in lines:
        if clean(l) in ("salt pepper", "salt black pepper", "salt white pepper"):
            expanded += ["salt", "pepper"]
        else:
            expanded.append(l)
    return title, expanded, steps


def build_vocab(parsed) -> Vocab:
    """Frequent cleaned phrases become canonical vocabulary terms."""
    counts = Counter()
    for _, lines, _ in parsed:
        for phrase in {clean(l) for l in lines}:
            if phrase and len(phrase.split()) <= MAX_TERM_WORDS:
                counts[phrase] += 1
    terms = {p for p, c in counts.items() if c >= MIN_RECIPES_PER_TERM} - BLOCKED
    # An alias replaces a standalone term of the same name (merging variants).
    aliases = {a: c for a, c in ALIASES.items() if c in terms}
    terms -= set(aliases)
    vocab = Vocab(terms, aliases)
    vocab.counts = counts
    return vocab


def main():
    with open(RAW, encoding="utf-8") as f:
        parsed = [p for line in f if (p := parse_recipe(json.loads(line)["text"]))]
    print(f"parsed {len(parsed)} raw recipes")

    vocab = build_vocab(parsed)
    print(f"vocabulary: {len(vocab.terms)} terms")

    rows, seen_titles, used = [], set(), Counter()
    for title, lines, steps in parsed:
        if not title or title.lower() in seen_titles or NON_FOOD_TITLE.search(title):
            continue
        mapped = [vocab.match(l, fuzzy=False).canonical for l in lines]
        if not lines or None in mapped:
            continue                       # incomplete mapping -> skip recipe
        ings = list(dict.fromkeys(mapped))  # unique, order kept
        if not (3 <= len(ings) <= 14 and 2 <= len(steps) <= 20):
            continue
        seen_titles.add(title.lower())
        used.update(ings)
        rows.append({
            "id": len(rows), "title": title, "ingredients": json.dumps(ings),
            "raw_ingredients": json.dumps(lines), "directions": json.dumps(steps),
            "steps": len(steps), "diet_tags": "|".join(diet_tags(ings)),
            "source": SOURCE,
        })
        if len(rows) >= MAX_RECIPES:
            break

    out = ROOT / "data"
    with open(out / "recipes.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    # Only keep vocabulary terms that actually occur in kept recipes.
    alias_by_term = {}
    for a, c in vocab.aliases.items():
        alias_by_term.setdefault(c, []).append(a)
    with open(out / "vocab.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["canonical", "aliases", "category", "recipe_count"])
        for term, n in used.most_common():
            w.writerow([term, "|".join(alias_by_term.get(term, [])),
                        "staple" if term in STAPLES else "ingredient", n])
    print(f"kept {len(rows)} recipes, {len(used)} vocabulary terms in use")


if __name__ == "__main__":
    main()
