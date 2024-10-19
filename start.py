import os
from app import app  # Import the Flask app from your main app file (e.g., app.py or main.py)

if __name__ == "__main__":
    # Get the port from environment variable (default to 8000 if not set)
    port = int(os.environ.get("PORT", 8000))
    # Bind to host 0.0.0.0 and the fetched port
    app.run(host="0.0.0.0", port=port)
