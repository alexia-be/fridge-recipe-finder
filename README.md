# Fridge Recipe Finder

Snap your fridge, get dinner ideas.

A small web app that looks at a photo of your fridge, works out which ingredients are in it, and suggests recipes ranked by how many of your ingredients each one uses. Everything runs on your own computer: the photo is analysed by a local AI model, is never sent over the internet, and is never saved to disk.

![Demo of Fridge Recipe Finder](docs/demo-Milestone-6.gif)

## How it works

1. You take a photo with your camera or upload a fridge photo on the web page. Camera video stays in your browser; only the single captured photo is sent to your local server.
2. The Flask backend checks the file (type, size, valid image), shrinks it, and sends it to a vision model running locally in [Ollama](https://ollama.com). The model answers with a list of ingredients as JSON.
3. The page shows the ingredients as an editable list, so you can remove wrong guesses and add missing items.
4. The backend matches your list against a local recipe file and returns recipes ranked by how many of your ingredients they use, showing which ingredients are missing.

**Privacy:** the photo is held in memory only while it is processed. It is not written to disk, and the log never contains image data or file names. If you use the camera, the video stays in your browser, and the camera switches off right after the photo is taken.

## Tech stack

| Part | What it uses |
|------|--------------|
| Backend | Python 3.10+, Flask |
| Frontend | Plain HTML, CSS and JavaScript (no framework) |
| Camera | The browser's built-in camera support (no extra libraries) |
| AI | Ollama with `qwen3-vl:8b-instruct` (Apache 2.0 license) |
| Image handling | Pillow |
| Recipes | Local file, `data/recipes.json` (no API key, works offline) |
| Tests | pytest |

Everything is free and open source. No API keys or `.env` file are needed.

Developed and tested on Windows 11 with 32 GB RAM and an NVIDIA RTX 4060 (8 GB).

## Setup (Windows, PowerShell)

**1. Install the tools** (skip any you already have):

- Python 3.10 or newer from [python.org](https://www.python.org/downloads/). Tick **Add python.exe to PATH** in the installer.
- Git from [git-scm.com](https://git-scm.com/download/win).
- Ollama from [ollama.com/download](https://ollama.com/download).

**2. Download the model** (about 6 GB, one time only):

```powershell
ollama pull qwen3-vl:8b-instruct
```

**3. Get the code and install the packages:**

```powershell
git clone https://github.com/alexia-be/fridge-recipe-finder.git
cd fridge-recipe-finder
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell says running scripts is disabled, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and try the activate command again.

**4. Make sure Ollama is running.** You should see the llama icon in the system tray. If not, open **Ollama** from the Start menu.

**5. Start the app:**

```powershell
python app.py
```

Open <http://127.0.0.1:5000> in your browser.

## Using the app

1. Click **Use camera**, allow camera access when your browser asks, point the camera at your fridge and click **Take photo**. Or choose a fridge photo (JPG, PNG or WebP, up to 5 MB) and click **Upload photo**. The first photo after starting takes longest, because the model has to load.
2. Check the ingredient list. Click **×** to remove a wrong item, or type a new one and press Enter.
3. Click **Find recipes** to see matching recipes, best match first.

## API

| Method | Address | What it does |
|--------|---------|--------------|
| GET | `/` | The web page |
| POST | `/upload` | Takes a photo, returns the detected ingredients |
| POST | `/recipes` | Takes an ingredient list, returns ranked recipes |
| GET | `/health` | Reports whether the app, Ollama and the model are ready |

The examples use `curl.exe` (the `.exe` matters in PowerShell, where plain `curl` is something else).

### POST /upload

The web page's camera sends its captured photo to this same address, so photos from the camera and from a file are handled identically.

```powershell
curl.exe -F "photo=@fridge.jpg" http://127.0.0.1:5000/upload
```

```json
{
  "ingredients": [
    "egg",
    "milk",
    "tomato",
    "onion",
    "cheese"
  ]
}
```

### POST /recipes

```powershell
Set-Content $env:TEMP\body.json '{"ingredients": ["egg", "tomato", "onion", "cheese"]}'
curl.exe -X POST -H "Content-Type: application/json" -d "@$env:TEMP\body.json" http://127.0.0.1:5000/recipes
```

The response is shortened here. `matched` lists what you have, `missing` what you still need.

```json
{
  "ingredients": ["egg", "tomato", "onion", "cheese"],
  "recipes": [
    {
      "instructions": "Beat the eggs, cook the chopped tomato and onion, pour the eggs over, add cheese and fold.",
      "matched": ["egg", "tomato", "onion", "cheese"],
      "missing": [],
      "name": "Tomato Omelette"
    }
  ]
}
```

### GET /health

```powershell
curl.exe -i http://127.0.0.1:5000/health
```

Everything ready, HTTP 200:

```json
{
  "app": "ok",
  "model": "ready",
  "ollama": "ok",
  "status": "ok"
}
```

Ollama not running, HTTP 503:

```json
{
  "app": "ok",
  "model": "unknown",
  "ollama": "unreachable",
  "status": "degraded"
}
```

### Errors

Every error uses the same JSON shape, a proper HTTP status code, and a message a non-technical user can understand:

```json
{
  "error": {
    "code": "OLLAMA_UNAVAILABLE",
    "message": "The local AI (Ollama) isn't running. Please start Ollama and try again."
  }
}
```

| Code | HTTP | Meaning |
|------|------|---------|
| `NO_FILE` | 400 | No photo was chosen |
| `BAD_FILE_TYPE` | 415 | Not a JPG, PNG or WebP image |
| `FILE_TOO_LARGE` | 413 | Photo is over 5 MB |
| `IMAGE_INVALID` | 400 | File is empty, corrupted or not really an image |
| `OLLAMA_UNAVAILABLE` | 503 | Ollama is not running |
| `MODEL_NOT_FOUND` | 503 | The model has not been downloaded |
| `TIMEOUT` | 504 | The model took too long to answer |
| `OLLAMA_ERROR` | 502 | Ollama returned an unexpected error |
| `BAD_MODEL_OUTPUT` | 502 | The model's answer was not valid JSON |
| `NO_INGREDIENTS` | 422 | The model found no food in the photo |
| `INVALID_REQUEST` | 400 | The ingredient list sent to `/recipes` was malformed |
| `EMPTY_INGREDIENT_LIST` | 400 | The ingredient list was empty |
| `NOT_FOUND` | 404 | Unknown address |
| `METHOD_NOT_ALLOWED` | 405 | Wrong kind of request for that address |
| `INTERNAL_ERROR` | 500 | An unexpected bug (details are in the log) |

## Logging

The app writes to `logs/app.log` (ignored by Git) and to the terminal. It records what happened, when, and how long it took, but never image data or file names:

```
2026-10-17 14:03:11,512 INFO Photo received: image/jpeg, 2318450 bytes
2026-10-17 14:03:19,044 INFO Detected 12 ingredients in 7.5 s
```

To read the latest lines: `Get-Content logs\app.log -Tail 20`

## Running the tests

```powershell
pip install -r requirements-dev.txt
pytest
```

The tests use a fake Ollama, so they run in seconds and don't need the model. They cover the error cases above, recipe ranking, and the health check. The camera feature runs in the browser, so it was tested by hand and is not covered by pytest.

## Project structure

```
fridge-recipe-finder/
├── app.py                 # routes (web addresses) and error handling
├── vision.py              # talks to Ollama and returns the ingredient list
├── recipes.py             # matches ingredients to recipes
├── logging_setup.py       # log file setup
├── requirements.txt       # packages the app needs
├── requirements-dev.txt   # extra packages for tests
├── pytest.ini             # pytest settings
├── data/
│   └── recipes.json       # the local recipe dataset
├── templates/
│   └── index.html         # the web page
├── static/
│   ├── style.css          # how it looks
│   └── app.js             # what it does in the browser, including the camera
├── tests/
│   └── test_app.py        # automated tests
├── docs/
│   └── demo-Milestone-6.gif           # demo recording
├── LICENSE
└── README.md
```

## Troubleshooting

| What you see | Likely cause | What to do |
|--------------|--------------|------------|
| "Running scripts is disabled" when activating `.venv` | PowerShell's default security setting | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then activate again |
| `python` is not recognized | Python is not on PATH | Reinstall Python with **Add python.exe to PATH** ticked, then open a new PowerShell |
| `ModuleNotFoundError` | `.venv` is not active, or packages are missing | Activate `.venv`, then run `pip install -r requirements.txt` |
| "The local AI (Ollama) isn't running" | Ollama is not started | Open **Ollama** from the Start menu or run `ollama serve`. `curl.exe http://localhost:11434` should reply `Ollama is running` |
| "The AI model hasn't been downloaded yet" | Model missing | Run `ollama pull qwen3-vl:8b-instruct`, then check with `ollama list` |
| "The AI took too long to answer" | First request loads the model, or no GPU | Try again. Run `ollama ps` and check the **PROCESSOR** column. Try a smaller photo |
| "The AI gave an answer we couldn't read" | The model's answer was not valid JSON | Try again. Check `vision.py` uses `qwen3-vl:8b-instruct`, not the `qwen3-vl:8b` "thinking" edition, which can run out of room before it writes its answer |
| "We couldn't spot any food" | Unclear photo | Use a closer, brighter photo |
| "Camera access was blocked" | Camera permission was denied | Click the lock icon in the address bar, set **Camera** to **Allow**, and reload. Or upload a file instead |
| "No camera was found" | No webcam, or the browser can't see it | Upload a file instead, or plug in a webcam and reload |
| "The camera is being used by another program" | Another app, such as a video call, has the camera | Close that program and try again |
| "The camera isn't available here" | Browsers only allow the camera on `localhost` / `127.0.0.1` | Open the app at `http://127.0.0.1:5000`, not at your computer's network address |
| Port 5000 already in use | Another program uses it | Close it, or change the port in `app.py` (`app.run(debug=True, port=5001)`) |
| The page behaves like an old version | An old server is still running, or the browser cached old files | Stop the old server with Ctrl+C, restart it, then press Ctrl+F5 in the browser |
| Anything else | | Check `http://127.0.0.1:5000/health`, then read the end of `logs\app.log` |

## Known limitations

- **Model accuracy:** a small local model can miss items, use vague names (such as "meat" or "soda"), occasionally name things that aren't there, and give slightly different answers each run. This is why the ingredient list is editable.
- **Image size:** photos are shrunk to 1024 pixels on the longest side before analysis, so small or hidden items may be missed.
- **Speed:** it depends on your hardware. The first photo after starting is slowest while the model loads, and running without a GPU is much slower.
- **Small recipe set:** `data/recipes.json` holds 10 recipes. Matching uses exact ingredient names with simple plural handling, so "pepper" does not match "bell pepper". Pantry staples such as salt and oil are not included.
- **Camera:** it needs a webcam and your permission, and browsers only allow it on `localhost` / `127.0.0.1`, so opening the app from another device on your network won't give camera access. A laptop webcam is hard to point at a fridge, so file upload is kept as a fallback.
- **Setup size:** the model needs about 6 GB of disk space. Internet is only needed for setup, because the recipes are local.
- **Local demo only:** it runs on Flask's development server with no login, so it is not meant to be hosted.
- **English only.**

## License

MIT. See [LICENSE](LICENSE).