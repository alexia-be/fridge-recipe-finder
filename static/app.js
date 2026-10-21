// ----- Find the page elements we need -----
const fileInput = document.getElementById("photo");
const uploadBtn = document.getElementById("upload-btn");
const cameraBtn = document.getElementById("camera-btn");
const cameraSection = document.getElementById("camera-section");
const video = document.getElementById("video");
const snapBtn = document.getElementById("snap-btn");
const cancelCameraBtn = document.getElementById("cancel-camera-btn");
const canvas = document.getElementById("canvas");
const statusEl = document.getElementById("status");
const spinner = document.getElementById("spinner");

const ingredientSection = document.getElementById("ingredient-section");
const ingredientList = document.getElementById("ingredient-list");
const newIngredient = document.getElementById("new-ingredient");
const addBtn = document.getElementById("add-btn");
const findBtn = document.getElementById("find-btn");
const recipesDiv = document.getElementById("recipes");

// The current ingredient list lives in this variable
let ingredients = [];
// The camera stream, while the camera is on
let cameraStream = null;

// ----- Small helpers -----

// Show a message. Pass true for an error (shown in red).
function showMessage(text, isError = false) {
  statusEl.textContent = text;
  statusEl.className = isError ? "error" : "";
}

// Show or hide the spinner, and block the buttons while we wait
function setLoading(isLoading, text = "") {
  spinner.hidden = !isLoading;
  uploadBtn.disabled = isLoading;
  cameraBtn.disabled = isLoading;
  findBtn.disabled = isLoading;
  if (isLoading) showMessage(text);
}

// Send a request and return the JSON answer.
// If anything goes wrong, throw an Error with a friendly message.
async function callServer(url, options) {
  let response;
  try {
    response = await fetch(url, options);
  } catch (err) {
    throw new Error("Could not reach the app. Is the server running?");
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    // Our server sends errors as {"error": {"code": ..., "message": ...}}
    throw new Error(data && data.error ? data.error.message : "Something went wrong. Please try again.");
  }
  return data;
}

// ----- Analyse a photo (from a file or from the camera) -----
async function analyzePhoto(photo, filename) {
  const formData = new FormData();
  formData.append("photo", photo, filename);

  setLoading(true, "Looking at your photo... the first time can take a minute.");
  try {
    const data = await callServer("/upload", { method: "POST", body: formData });
    ingredients = data.ingredients;
    renderIngredients();
    ingredientSection.hidden = false;
    recipesDiv.textContent = "";  // clear any old results
    showMessage("Check the list below: remove anything wrong and add anything missing.");
  } catch (err) {
    showMessage(err.message, true);
  } finally {
    setLoading(false);  // always runs, so the buttons never get stuck
  }
}

// ----- Option 2: upload a file -----
uploadBtn.addEventListener("click", () => {
  const file = fileInput.files[0];
  if (!file) {
    showMessage("Please choose a photo first.", true);
    return;
  }
  stopCamera();  // in case the camera preview is open
  analyzePhoto(file, file.name);
});

// ----- Option 1: take a photo with the camera -----

// Turn the camera on and show the live preview
async function startCamera() {
  // Some browsers (or non-local addresses) don't allow camera access at all
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    showMessage("The camera isn't available here. Please upload a photo instead.", true);
    return;
  }
  try {
    // Ask permission and prefer the back camera if there is one
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment" },
      audio: false,
    });
    video.srcObject = cameraStream;
    cameraSection.hidden = false;
    cameraBtn.hidden = true;
    showMessage("");
  } catch (err) {
    showMessage(cameraErrorMessage(err), true);
  }
}

// Turn each camera error into a message a non-technical user can follow
function cameraErrorMessage(err) {
  if (err.name === "NotAllowedError") {
    return "Camera access was blocked. Allow the camera in your browser, or upload a photo instead.";
  }
  if (err.name === "NotFoundError") {
    return "No camera was found. Please upload a photo instead.";
  }
  if (err.name === "NotReadableError") {
    return "The camera is being used by another program. Close it and try again.";
  }
  return "Could not start the camera. Please upload a photo instead.";
}

// Turn the camera off (this also switches off the camera light)
function stopCamera() {
  if (cameraStream) {
    cameraStream.getTracks().forEach((track) => track.stop());
    cameraStream = null;
  }
  video.srcObject = null;
  cameraSection.hidden = true;
  cameraBtn.hidden = false;
}

// Grab the current video frame, turn it into a JPEG and analyse it
snapBtn.addEventListener("click", () => {
  if (!video.videoWidth) {
    showMessage("The camera isn't ready yet. Please wait a moment and try again.", true);
    return;
  }
  // Draw the current frame onto the hidden canvas
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext("2d").drawImage(video, 0, 0);
  stopCamera();  // the picture is taken, so switch the camera off

  canvas.toBlob((blob) => {
    if (!blob) {
      showMessage("Could not capture the photo. Please try again.", true);
      return;
    }
    analyzePhoto(blob, "camera.jpg");
  }, "image/jpeg", 0.9);
});

cameraBtn.addEventListener("click", startCamera);
cancelCameraBtn.addEventListener("click", stopCamera);

// ----- The editable ingredient list -----

// Redraw the list from the `ingredients` variable
function renderIngredients() {
  ingredientList.textContent = "";
  ingredients.forEach((name, index) => {
    const li = document.createElement("li");
    li.textContent = name + " ";

    const removeBtn = document.createElement("button");
    removeBtn.textContent = "×";
    removeBtn.setAttribute("aria-label", "Remove " + name);
    removeBtn.addEventListener("click", () => {
      ingredients.splice(index, 1);  // remove this one item
      renderIngredients();
    });

    li.appendChild(removeBtn);
    ingredientList.appendChild(li);
  });
}

// Add the typed ingredient (ignore blanks and duplicates)
function addIngredient() {
  const name = newIngredient.value.trim().toLowerCase();
  if (name && !ingredients.includes(name)) {
    ingredients.push(name);
    renderIngredients();
  }
  newIngredient.value = "";
  newIngredient.focus();
}

addBtn.addEventListener("click", addIngredient);
newIngredient.addEventListener("keydown", (event) => {
  if (event.key === "Enter") addIngredient();  // Enter works too
});

// ----- Find recipes for the edited list -----
findBtn.addEventListener("click", async () => {
  setLoading(true, "Finding recipes...");
  try {
    const data = await callServer("/recipes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ingredients }),
    });
    renderRecipes(data.recipes);
    showMessage(data.recipes.length ? "" : "No matching recipes. Try adding more ingredients.");
  } catch (err) {
    showMessage(err.message, true);
  } finally {
    setLoading(false);
  }
});

// Build one card per recipe
function renderRecipes(recipes) {
  recipesDiv.textContent = "";
  recipes.forEach((recipe) => {
    const card = document.createElement("div");
    card.className = "recipe";

    const title = document.createElement("h3");
    title.textContent = recipe.name;

    const have = document.createElement("p");
    have.textContent = "You have: " + recipe.matched.join(", ");

    const missing = document.createElement("p");
    missing.textContent = recipe.missing.length
      ? "Missing: " + recipe.missing.join(", ")
      : "You have everything!";

    card.append(title, have, missing);
    recipesDiv.appendChild(card);
  });
}