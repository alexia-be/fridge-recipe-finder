# app.py - the entry point of our web app
from flask import Flask, render_template, request, jsonify

from recipes import find_recipes
from vision import detect_ingredients, VisionError

app = Flask(__name__)

# Refuse files bigger than 5 MB (Flask enforces this for us)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

# Only these image types are allowed
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}

# Limits for the ingredient list sent to /recipes
MAX_INGREDIENTS = 40
MAX_NAME_LENGTH = 50


def error_response(code, message, status):
    """Every error uses this same JSON shape."""
    return jsonify({"error": {"code": code, "message": message}}), status


@app.route("/")
def home():
    # Send the HTML page from the templates/ folder
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    # The browser sends the photo under the name "photo"
    photo = request.files.get("photo")

    if photo is None or photo.filename == "":
        return error_response("NO_FILE", "Please choose a photo first.", 400)

    if photo.mimetype not in ALLOWED_TYPES:
        return error_response(
            "BAD_FILE_TYPE", "Please upload a JPG, PNG or WebP image.", 415
        )

    # Read the photo into memory only. It is never saved to disk.
    ingredients = detect_ingredients(photo.read())
    return jsonify({"ingredients": ingredients})


@app.route("/recipes", methods=["POST"])
def recipes():
    # The page sends the (possibly edited) ingredient list as JSON
    data = request.get_json(silent=True)  # silent=True: None instead of crashing
    ingredients = data.get("ingredients") if isinstance(data, dict) else None

    # It must be a list of text items
    if not isinstance(ingredients, list) or not all(isinstance(i, str) for i in ingredients):
        return error_response(
            "INVALID_REQUEST",
            "Something went wrong with the ingredient list. Please try again.",
            400,
        )

    # Tidy it up: trim spaces, drop blanks, cap the length and the count
    ingredients = [i.strip()[:MAX_NAME_LENGTH] for i in ingredients if i.strip()]
    ingredients = ingredients[:MAX_INGREDIENTS]

    if not ingredients:
        return error_response(
            "EMPTY_INGREDIENT_LIST", "Please add at least one ingredient.", 400
        )

    return jsonify({"ingredients": ingredients, "recipes": find_recipes(ingredients)})


@app.errorhandler(VisionError)
def handle_vision_error(e):
    # Any VisionError raised in vision.py ends up here, in our standard shape
    return error_response(e.code, e.message, e.status)


@app.errorhandler(413)
def too_large(e):
    # Runs automatically when a file is over the 5 MB limit
    return error_response("FILE_TOO_LARGE", "That photo is too big. Please use one under 5 MB.", 413)


if __name__ == "__main__":
    app.run(debug=True)