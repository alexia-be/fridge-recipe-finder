# vision.py - sends a photo to the local Ollama model and returns ingredients
import base64
import io
import json
import requests
from PIL import Image, ImageOps, UnidentifiedImageError

OLLAMA_URL = "http://localhost:11434/api/chat"  # Ollama's local address
MODEL = "qwen3-vl:8b-instruct"
TIMEOUT_SECONDS = 120  # the first request is slow while the model loads
MAX_SIDE = 1024        # shrink big photos: faster, and fits the model's memory

PROMPT = (
    "Look at this photo of the inside of a fridge. List the distinct food and "
    "drink items you can clearly see. Use short, singular, lowercase names, "
    'like "egg", "tomato" or "milk". Do not guess brands. '
    'Answer only with JSON like {"ingredients": ["egg", "milk"]}.'
)


class VisionError(Exception):
    """An error we can show to the user: it has a code, a message and an HTTP status."""

    def __init__(self, code, message, status):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def prepare_image(image_bytes):
    """Check the image is real, fix its rotation, shrink it, return JPEG bytes."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = ImageOps.exif_transpose(img)  # fix sideways phone photos
        img = img.convert("RGB")            # JPEG can't store transparency
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise VisionError(
            "IMAGE_INVALID",
            "That file doesn't look like a valid photo. Please try another one.",
            400,
        )
    img.thumbnail((MAX_SIDE, MAX_SIDE))  # only shrinks, never enlarges
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


def ask_model(image_b64):
    """Send the image to Ollama and return the model's text answer."""
    payload = {
        "model": MODEL,
        "stream": False,  # one complete answer instead of word-by-word
        # Force the answer to be JSON in exactly this shape
        "format": {
            "type": "object",
            "properties": {"ingredients": {"type": "array", "items": {"type": "string"}}},
            "required": ["ingredients"],
        },
        "options": {"temperature": 0.2},  # low = more consistent answers
        "messages": [{"role": "user", "content": PROMPT, "images": [image_b64]}],
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT_SECONDS)
    except requests.exceptions.ConnectionError:
        raise VisionError(
            "OLLAMA_UNAVAILABLE",
            "The local AI (Ollama) isn't running. Please start Ollama and try again.",
            503,
        )
    except requests.exceptions.Timeout:
        raise VisionError(
            "TIMEOUT",
            "The AI took too long to answer. Please try again, or try a smaller photo.",
            504,
        )

    if response.status_code == 404:  # Ollama says 404 when the model isn't downloaded
        raise VisionError(
            "MODEL_NOT_FOUND",
            "The AI model hasn't been downloaded yet. Please follow the setup steps in the README.",
            503,
        )
    if response.status_code != 200:
        raise VisionError(
            "OLLAMA_ERROR", "The AI had a problem. Please try again.", 502
        )
    
    return response.json()["message"]["content"]


def parse_ingredients(text):
    """Turn the model's JSON text into a clean list of ingredient names."""
    try:
        items = json.loads(text)["ingredients"]
        if not isinstance(items, list):
            raise TypeError
    except (json.JSONDecodeError, KeyError, TypeError):
        raise VisionError(
            "BAD_MODEL_OUTPUT",
            "The AI gave an answer we couldn't read. Please try again.",
            502,
        )

    cleaned = []
    for item in items:
        if isinstance(item, str):
            name = item.strip().lower()
            if name and name not in cleaned:  # skip blanks and duplicates
                cleaned.append(name)

    if not cleaned:
        raise VisionError(
            "NO_INGREDIENTS",
            "We couldn't spot any food in that photo. Try a clearer, closer photo.",
            422,
        )
    return cleaned[:40]  # a sensible upper limit


def detect_ingredients(image_bytes):
    """The one function app.py calls: photo bytes in, ingredient list out."""
    jpeg = prepare_image(image_bytes)
    image_b64 = base64.b64encode(jpeg).decode("ascii")  # text form of the image
    answer = ask_model(image_b64)
    return parse_ingredients(answer)