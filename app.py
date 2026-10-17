# app.py - the entry point of our web app
import time

from flask import Flask, render_template, request, jsonify
from werkzeug.exceptions import HTTPException

from logging_setup import setup_logging
from recipes import find_recipes
from vision import detect_ingredients, check_ollama, VisionError

app = Flask(__name__)
logger = setup_logging()

# Refuse files bigger than 5 MB (Flask enforces this for us)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

# Only these image types are allowed
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}

# Limits for the ingredient list sent to /recipes
MAX_INGREDIENTS = 40
MAX_NAME_LENGTH = 50

# Friendly text for common web errors (404 = not found, 405 = wrong method)
HTTP_MESSAGES = {
    404: ("NOT_FOUND", "That address doesn't exist."),
    405: ("METHOD_NOT_ALLOWED", "That address doesn't accept this kind of request."),
}


def error_response(code, message, status):
    """Every error uses this same JSON shape, and is written to the log."""
    logger.warning("Error %s (HTTP %s)", code, status)
    return jsonify({"error": {"code": code, "message": message}}), status


@app.route("/")
def home():
    # Send the HTML page from the templates/ folder
    return render_template("index.html")


@app.route("/health")
def health():
    # Reports whether the app, Ollama and the model are ready
    ollama_status, model_status = check_ollama()
    healthy = ollama_status == "ok" and model_status == "ready"
    body = {
        "status": "ok" if healthy else "degraded",
        "app": "ok",  # if you can read this, the app itself is running
        "ollama": ollama_status,
        "model": model_status,
    }
    return jsonify(body), (200 if healthy else 503)


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
    image_bytes = photo.read()
    # Log the type and size only, never the file name or the image itself
    logger.info("Photo received: %s, %d bytes", photo.mimetype, len(image_bytes))

    start = time.perf_counter()
    ingredients = detect_ingredients(image_bytes)
    logger.info(
        "Detected %d ingredients in %.1f s", len(ingredients), time.perf_counter() - start
    )
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


@app.errorhandler(HTTPException)
def handle_http_error(e):
    # Other web errors, like 404 (unknown address) or 405 (wrong request type)
    code, message = HTTP_MESSAGES.get(
        e.code, ("REQUEST_ERROR", "The request could not be processed.")
    )
    return error_response(code, message, e.code)


@app.errorhandler(Exception)
def handle_unexpected_error(e):
    # The safety net: any bug we didn't plan for ends up here
    logger.exception("Unexpected error")  # writes the full details to the log
    return error_response(
        "INTERNAL_ERROR", "Something went wrong on our side. Please try again.", 500
    )


if __name__ == "__main__":
    app.run(debug=True)