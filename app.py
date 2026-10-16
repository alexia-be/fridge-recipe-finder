# app.py - the entry point of our web app
from flask import Flask

# Create the Flask application object
app = Flask(__name__)


# A "route" connects a URL to a Python function.
# When someone visits "/", Flask runs home() and sends back its result.
@app.route("/")
def home():
    return "Hello from Fridge Recipe Finder!"


# This runs only when we start the file directly (python app.py)
if __name__ == "__main__":
    # debug=True auto-restarts the server when you edit code
    app.run(debug=True)