# app.py - the entry point of our web app
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Refuse files bigger than 5 MB (Flask enforces this for us)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

# Only these image types are allowed
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


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

    # For now we only report the file name and size.
    # We do NOT save the photo anywhere (privacy).
    size = len(photo.read())
    return jsonify({"message": "Photo received", "filename": photo.filename, "bytes": size})


@app.errorhandler(413)
def too_large(e):
    # Runs automatically when a file is over the 5 MB limit
    return error_response("FILE_TOO_LARGE", "That photo is too big. Please use one under 5 MB.", 413)


if __name__ == "__main__":
    app.run(debug=True)