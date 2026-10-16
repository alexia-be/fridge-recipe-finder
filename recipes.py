# recipes.py - finds recipes that match the ingredients the user has
import json
from pathlib import Path

# Path to the recipe file, built relative to this file so it works anywhere
DATA_FILE = Path(__file__).parent / "data" / "recipes.json"


def load_recipes():
    """Read all recipes from the JSON file."""
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def normalize(name):
    """Make names comparable: 'Eggs ' -> 'egg', 'Tomatoes' -> 'tomato'."""
    name = name.strip().lower()
    if name.endswith("oes"):          # tomatoes -> tomato, potatoes -> potato
        return name[:-2]
    if len(name) > 3 and name.endswith("s") and not name.endswith(("ss", "us")):
        return name[:-1]              # eggs -> egg, onions -> onion
    return name


def find_recipes(user_ingredients):
    """Return recipes that use at least one of the user's ingredients,
    best match first, with what the user has and what is missing."""
    have = {normalize(i) for i in user_ingredients if i.strip()}
    results = []

    for recipe in load_recipes():
        needed = [normalize(i) for i in recipe["ingredients"]]
        matched = [i for i in needed if i in have]
        missing = [i for i in needed if i not in have]

        if matched:  # skip recipes that share nothing with the fridge
            results.append({
                "name": recipe["name"],
                "instructions": recipe["instructions"],
                "matched": matched,
                "missing": missing,
            })

    # Most matched ingredients first; ties go to the recipe missing fewer
    results.sort(key=lambda r: (-len(r["matched"]), len(r["missing"])))
    return results