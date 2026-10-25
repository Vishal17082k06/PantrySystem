"""Dietary tags derived from ingredient words (no external data, no guessing).

A tag is given only if NO ingredient contains a word from that tag's
"forbidden" set. The sets are deliberately conservative: when an ingredient is
ambiguous (e.g. bouillon, worcestershire) we treat it as NOT compliant.
Tagging is by whole words, so "nutmeg" is not mistaken for "nut".
"""

MEAT_FISH = {
    "chicken", "beef", "pork", "bacon", "ham", "sausage", "turkey", "lamb",
    "veal", "steak", "hamburger", "pepperoni", "salami", "hot dog", "frankfurter",
    "fish", "tuna", "salmon", "shrimp", "crab", "lobster", "clam", "oyster",
    "anchovy", "sardine", "lard", "gelatin", "bouillon", "worcestershire",
    "venison", "duck", "meat", "wiener", "chorizo", "prosciutto", "scallop",
    "chuck", "jello", "hamburger", "rib", "roast", "brisket", "tenderloin",
}
ANIMAL_PRODUCTS = {  # extra items that make a recipe non-vegan
    "milk", "butter", "cheese", "cream", "egg", "yogurt", "honey", "mayonnaise",
    "buttermilk", "cheddar", "mozzarella", "parmesan", "margarine", "whey",
    "custard", "mayo", "ghee", "marshmallow", "caramel", "whipped", "whip",
    "creme", "pudding", "yolk", "albumen",
}
GLUTEN = {
    "flour", "bread", "pasta", "noodle", "spaghetti", "macaroni", "cracker",
    "cereal", "bun", "tortilla", "oat", "barley", "couscous", "bisquick",
    "biscuit", "breadcrumb", "crouton", "pita", "beer", "wheat", "rye",
    "lasagna", "soy", "cookie", "cake", "pizza", "dough", "pretzel", "roll",
    "pancake", "waffle", "bran", "semolina", "orzo", "fettuccine", "linguine",
    "ramen", "pie", "graham", "crust", "wafer", "crescent", "soup", "krispy",
    "muffin", "croissant", "bagel", "brownie",
}
NUTS = {
    "almond", "pecan", "walnut", "cashew", "pistachio", "hazelnut", "peanut",
    "nut", "macadamia", "pine", "praline", "marzipan", "nutella",
}

# Plant-based items whose name contains an animal-product word.
PLANT_OK = {"coconut milk", "peanut butter", "cream tartar", "soy milk",
            "almond milk", "oat milk", "coconut cream", "cocoa butter"}

FORBIDDEN = {
    "vegetarian": MEAT_FISH,
    "vegan": MEAT_FISH | ANIMAL_PRODUCTS,
    "gluten_free": GLUTEN,
    "nut_free": NUTS,
}
ALL_DIETS = list(FORBIDDEN)


def diet_tags(ingredients) -> list[str]:
    """Return the diets this ingredient list satisfies, e.g. ['vegetarian']."""
    words = {w for ing in ingredients for w in ing.split()}
    # For the animal-product check, ignore the plant-based look-alikes above.
    animal_words = {w for ing in ingredients if ing not in PLANT_OK
                    for w in ing.split()}
    tags = []
    for tag, bad in FORBIDDEN.items():
        check = animal_words if tag in ("vegetarian", "vegan") else words
        if not (check & bad):
            tags.append(tag)
    return tags
