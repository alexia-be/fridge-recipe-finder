// ----- Find the page elements we need -----
const fileInput = document.getElementById("photo");
const uploadBtn = document.getElementById("upload-btn");
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

// ----- Step 1: upload the photo -----
uploadBtn.addEventListener("click", async () => {
  if (!fileInput.files[0]) {
    showMessage("Please choose a photo first.", true);
    return;
  }

  const formData = new FormData();
  formData.append("photo", fileInput.files[0]);

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
});

// ----- Step 2: the editable ingredient list -----

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

// ----- Step 3: find recipes for the edited list -----
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