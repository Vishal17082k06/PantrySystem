"""Ingredient normalization: messy text -> canonical vocabulary term.

Pipeline for one ingredient string:
    clean()        lowercase, drop quantities / units / prep words
    singularize()  "tomatoes" -> "tomato"
    Vocab.match()  exact -> alias -> fuzzy (rapidfuzz) -> None
"""
import csv
import re
from dataclasses import dataclass
from pathlib import Path

from rapidfuzz import fuzz, process

# Words that describe quantity or preparation, not the ingredient itself.
NOISE_WORDS = {
    "cup", "cups", "tablespoon", "tablespoons", "tbsp", "teaspoon", "teaspoons",
    "tsp", "pound", "pounds", "lb", "lbs", "ounce", "ounces", "oz", "gram",
    "grams", "g", "kg", "ml", "l", "liter", "liters", "pinch", "dash", "can",
    "cans", "package", "packages", "clove", "cloves", "slice", "slices",
    "chopped", "diced", "minced", "sliced", "grated", "shredded", "crushed",
    "fresh", "freshly", "ground", "large", "small", "medium", "whole", "ripe",
    "boneless", "skinless", "cooked", "uncooked", "raw", "frozen", "dried",
    "optional", "to", "taste", "of", "and", "or", "a", "an", "the", "for",
    "finely", "roughly", "thinly", "peeled", "halved", "cubed", "melted",
    "softened", "packed", "divided", "plus", "more", "about", "some",
    "c", "pkg", "jar", "carton", "bag", "box", "bottle", "stick", "envelope",
    "piece", "pieces", "cut", "up", "t", "stalk", "stalks", "sticks", "pt", "qt",
    "halves", "halve", "head", "kernel", "kernels", "firmly", "sifted", "soft",
    "cold", "beaten", "lukewarm", "none", "sprig", "sprigs", "container",
    "bunch", "crumbled",
}

# Irregular plurals the simple rules below would get wrong.
IRREGULAR = {"leaves": "leaf", "molasses": "molasses", "hummus": "hummus",
             "asparagus": "asparagus", "swiss": "swiss", "couscous": "couscous"}

FUZZY_CUTOFF = 82  # rapidfuzz score (0-100) needed to accept a fuzzy match


def singularize(word: str) -> str:
    """Very small English singularizer (good enough for food words)."""
    if word in IRREGULAR:
        return IRREGULAR[word]
    if len(word) <= 3 or word.endswith(("ss", "us")):
        return word
    if word.endswith("ies"):
        return word[:-3] + "y"           # berries -> berry
    if word.endswith("oes"):
        return word[:-2]                 # tomatoes -> tomato
    if word.endswith(("ches", "shes", "xes")):
        return word[:-2]                 # radishes -> radish
    if word.endswith("s"):
        return word[:-1]                 # onions -> onion
    return word


def clean(text: str) -> str:
    """Lowercase, keep the first option, strip digits/punctuation/noise words."""
    text = text.lower()
    text = re.sub(r"\(.*?\)", " ", text)          # "(optional)"
    text = text.split(",")[0]                     # "cream cheese, cubed" -> first part
    text = re.split(r"\s+or\s+", text)[0]         # "butter or margarine" -> butter
    # "saffron dissolved in hot water" -> "saffron": cut at connecting words so a
    # trailing word ("water") can't stand in for the real ingredient.
    text = re.split(r"\s+(?:in|with|dissolved|into|for|such|plus|mixed|stirred)\s+", text)[0]
    text = re.sub(r"[^a-z\s]", " ", text)         # digits, fractions, punctuation
    words = [w for w in text.split() if w not in NOISE_WORDS]
    if not words:
        return ""
    words[-1] = singularize(words[-1])             # only the head noun
    return " ".join(words)


@dataclass
class Match:
    raw: str                 # what the user typed
    canonical: str | None    # vocabulary term, or None if not recognised
    how: str                 # "exact" | "alias" | "fuzzy" | "none"
    score: float = 100.0


class Vocab:
    """Canonical ingredient names plus aliases (e.g. 'scallion' -> 'green onion')."""

    def __init__(self, terms, aliases=None):
        self.terms = set(terms)
        self.aliases = dict(aliases or {})
        self._choices = sorted(self.terms | set(self.aliases))

    @classmethod
    def from_csv(cls, path):
        """vocab.csv columns: canonical, aliases ('|'-separated), category."""
        terms, aliases, cats = [], {}, {}
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                terms.append(row["canonical"])
                cats[row["canonical"]] = row.get("category", "")
                for a in filter(None, row.get("aliases", "").split("|")):
                    aliases[a] = row["canonical"]
        v = cls(terms, aliases)
        v.categories = cats
        return v

    def _lookup(self, text: str) -> str | None:
        """Exact term or alias, else None."""
        if text in self.terms:
            return text
        return self.aliases.get(text)

    def match(self, raw: str, fuzzy: bool = True) -> Match:
        """Map one string to a vocabulary term (or report that we can't).

        Order: exact/alias -> longest known suffix -> fuzzy (typos).
        """
        text = clean(raw)
        if not text:
            return Match(raw, None, "none", 0.0)
        hit = self._lookup(text)
        if hit:
            return Match(raw, hit, "exact" if text in self.terms else "alias")
        # Drop leading modifiers: "boned chicken breast" -> "chicken breast".
        words = text.split()
        for i in range(1, len(words)):
            hit = self._lookup(" ".join(words[i:]))
            if hit:
                return Match(raw, hit, "suffix", 95.0)
        if fuzzy:
            # Typo fallback: closest known word, only if it is close enough.
            # fuzz.ratio compares whole strings, so "unicorn tears" != "corn".
            best = process.extractOne(text, self._choices, scorer=fuzz.ratio,
                                      score_cutoff=FUZZY_CUTOFF)
            if best:
                term, score, _ = best
                return Match(raw, self._lookup(term), "fuzzy", score)
        return Match(raw, None, "none", 0.0)


def parse_pantry(raw: str, vocab: Vocab):
    """Split 'tomatos, egg\\nrice' into (recognised canonical list, unknown strings)."""
    pieces = [p.strip() for p in re.split(r"[,\n;]", raw) if p.strip()]
    found, unknown = [], []
    for piece in pieces:
        m = vocab.match(piece)
        if m.canonical is None:
            unknown.append(piece)
        elif m.canonical not in found:
            found.append(m.canonical)
    return found, unknown


def load_default_vocab() -> Vocab:
    return Vocab.from_csv(Path(__file__).resolve().parent.parent / "data" / "vocab.csv")
