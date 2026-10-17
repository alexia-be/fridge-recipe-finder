# tests/test_app.py - automated tests for the error cases and main features
import io

import pytest
import requests
from PIL import Image

import app as app_module
import vision


# ----- Helpers that every test can use -----

@pytest.fixture
def client():
    """A fake browser that sends requests to the app."""
    app_module.app.config["TESTING"] = True
    app_module.logger.disabled = True  # keep test runs out of the real log file
    with app_module.app.test_client() as test_client:
        yield test_client
    app_module.logger.disabled = False


@pytest.fixture(autouse=True)
def block_real_ollama(monkeypatch):
    """Safety net: no test may talk to the real Ollama (autouse = runs every time)."""
    def refuse(*args, **kwargs):
        raise AssertionError("This test tried to call the real Ollama")

    monkeypatch.setattr(vision.requests, "post", refuse)
    monkeypatch.setattr(vision.requests, "get", refuse)


class FakeResponse:
    """Pretends to be Ollama's answer."""

    def __init__(self, status_code=200, content=""):
        self.status_code = status_code
        self._content = content

    def json(self):
        return {"message": {"content": self._content}}


def ollama_returns(monkeypatch, response):
    """Make the fake Ollama give this answer."""
    monkeypatch.setattr(vision.requests, "post", lambda *args, **kwargs: response)


def ollama_raises(monkeypatch, error):
    """Make the fake Ollama fail with this error."""
    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(vision.requests, "post", fail)


def photo_bytes():
    """A tiny but valid JPEG image, made in memory."""
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), "red").save(buffer, format="JPEG")
    return buffer.getvalue()


def upload(client, content, content_type="image/jpeg", filename="fridge.jpg"):
    """Send a file to /upload, like the web page does."""
    return client.post(
        "/upload",
        data={"photo": (io.BytesIO(content), filename, content_type)},
        content_type="multipart/form-data",
    )


def assert_error(response, status, code):
    """Check the standard error shape, the status code and the error code."""
    assert response.status_code == status
    error = response.get_json()["error"]
    assert error["code"] == code
    assert error["message"]  # there is a human-readable message


# ----- Upload problems -----

def test_no_file(client):
    assert_error(client.post("/upload"), 400, "NO_FILE")


def test_wrong_file_type(client):
    response = upload(client, b"%PDF-1.4", content_type="application/pdf", filename="doc.pdf")
    assert_error(response, 415, "BAD_FILE_TYPE")


def test_file_too_large(client):
    too_big = b"0" * (5 * 1024 * 1024 + 1)  # just over 5 MB
    assert_error(upload(client, too_big), 413, "FILE_TOO_LARGE")


def test_empty_file(client):
    assert_error(upload(client, b""), 400, "IMAGE_INVALID")


def test_corrupted_image(client):
    assert_error(upload(client, b"this is not an image"), 400, "IMAGE_INVALID")


# ----- Ollama and model problems -----

def test_ollama_not_running(client, monkeypatch):
    ollama_raises(monkeypatch, requests.exceptions.ConnectionError())
    assert_error(upload(client, photo_bytes()), 503, "OLLAMA_UNAVAILABLE")


def test_model_takes_too_long(client, monkeypatch):
    ollama_raises(monkeypatch, requests.exceptions.ReadTimeout())
    assert_error(upload(client, photo_bytes()), 504, "TIMEOUT")


def test_model_not_downloaded(client, monkeypatch):
    ollama_returns(monkeypatch, FakeResponse(status_code=404))
    assert_error(upload(client, photo_bytes()), 503, "MODEL_NOT_FOUND")


def test_model_returns_invalid_json(client, monkeypatch):
    ollama_returns(monkeypatch, FakeResponse(content="Sorry, I can see eggs and milk"))
    assert_error(upload(client, photo_bytes()), 502, "BAD_MODEL_OUTPUT")


def test_no_ingredients_found(client, monkeypatch):
    ollama_returns(monkeypatch, FakeResponse(content='{"ingredients": []}'))
    assert_error(upload(client, photo_bytes()), 422, "NO_INGREDIENTS")


def test_successful_upload_cleans_the_list(client, monkeypatch):
    # Messy model answer: capital letter, extra space, a duplicate, a blank
    messy = '{"ingredients": ["Egg ", "milk", "egg", ""]}'
    ollama_returns(monkeypatch, FakeResponse(content=messy))

    response = upload(client, photo_bytes())

    assert response.status_code == 200
    assert response.get_json()["ingredients"] == ["egg", "milk"]


# ----- Recipe lookup -----

def test_recipes_are_ranked_and_show_missing(client):
    response = client.post(
        "/recipes", json={"ingredients": ["eggs", "tomatoes", "onion", "cheese"]}
    )
    assert response.status_code == 200

    recipes = response.get_json()["recipes"]
    assert recipes[0]["name"] == "Tomato Omelette"
    assert recipes[0]["missing"] == []

    # Best matches must come first
    counts = [len(r["matched"]) for r in recipes]
    assert counts == sorted(counts, reverse=True)


def test_recipes_empty_list(client):
    response = client.post("/recipes", json={"ingredients": []})
    assert_error(response, 400, "EMPTY_INGREDIENT_LIST")


def test_recipes_invalid_request(client):
    response = client.post("/recipes", json={"ingredients": "egg"})  # should be a list
    assert_error(response, 400, "INVALID_REQUEST")


# ----- Health check and other errors -----

def test_health_ok(client, monkeypatch):
    monkeypatch.setattr(app_module, "check_ollama", lambda: ("ok", "ready"))
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_health_when_ollama_is_down(client, monkeypatch):
    monkeypatch.setattr(app_module, "check_ollama", lambda: ("unreachable", "unknown"))
    response = client.get("/health")
    assert response.status_code == 503

    body = response.get_json()
    assert body["status"] == "degraded"
    assert body["ollama"] == "unreachable"


def test_unknown_address(client):
    assert_error(client.get("/nope"), 404, "NOT_FOUND")


def test_wrong_request_type(client):
    assert_error(client.get("/upload"), 405, "METHOD_NOT_ALLOWED")


def test_unexpected_crash_still_returns_standard_json(client, monkeypatch):
    def explode(ingredients):
        raise RuntimeError("simulated bug")

    monkeypatch.setattr(app_module, "find_recipes", explode)
    response = client.post("/recipes", json={"ingredients": ["egg"]})
    assert_error(response, 500, "INTERNAL_ERROR")