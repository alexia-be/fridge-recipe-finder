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