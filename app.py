# app.py - the entry point of our web app
from flask import Flask, render_template, request, jsonify
from recipes import find_recipes
from vision import detect_ingredients, VisionError

app = Flask(__name__)

# Refuse files bigger than 5 MB (Flask enforces this for us)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

# Only these image types are allowed
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}

# Temporary hardcoded ingredients (Milestone 4 will detect them from a photo)
SAMPLE_INGREDIENTS = ["eggs", "tomatoes", "onion", "cheese"]


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

@app.route("/recipes")
def recipes():
    # Look up recipes for the sample ingredients and return them as JSON
    return jsonify({
        "ingredients": SAMPLE_INGREDIENTS,
        "recipes": find_recipes(SAMPLE_INGREDIENTS),
    })

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