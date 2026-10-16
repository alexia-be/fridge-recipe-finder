// Find the page elements we need
const fileInput = document.getElementById("photo");
const button = document.getElementById("upload-btn");
const status = document.getElementById("status");

// Run this when the button is clicked
button.addEventListener("click", async () => {
  status.className = "";
  status.textContent = "Uploading...";

  // Put the chosen file in a "form" package for sending
  const formData = new FormData();
  formData.append("photo", fileInput.files[0]);

  try {
    // Send it to our Flask /upload route
    const response = await fetch("/upload", { method: "POST", body: formData });
    const data = await response.json();

    if (!response.ok) {
      // Our server sent an error in the standard shape
      status.className = "error";
      status.textContent = data.error.message;
    } else {
      status.textContent = "Got it: " + data.filename + " (" + data.bytes + " bytes)";
    }
  } catch (err) {
    // The server could not be reached at all
    status.className = "error";
    status.textContent = "Could not reach the app. Is the server running?";
  }
});

// ----- Milestone 3: show recipes for the sample ingredients -----
const recipeBtn = document.getElementById("recipe-btn");
const recipesDiv = document.getElementById("recipes");

recipeBtn.addEventListener("click", async () => {
  recipesDiv.textContent = "Loading recipes...";

  try {
    const response = await fetch("/recipes");
    const data = await response.json();

    if (!response.ok) {
      recipesDiv.textContent = data.error.message;
      return;
    }

    recipesDiv.textContent = "";  // clear the loading text

    const intro = document.createElement("p");
    intro.textContent = "Using: " + data.ingredients.join(", ");
    recipesDiv.appendChild(intro);

    // Build one card per recipe
    data.recipes.forEach((recipe) => {
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
  } catch (err) {
    recipesDiv.textContent = "Could not reach the app. Is the server running?";
  }
});