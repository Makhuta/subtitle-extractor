import os
import logging
from app import app

logging.basicConfig(level=logging.DEBUG)

# Set default media path if not provided
if not os.environ.get("MEDIA_PATH"):
    os.environ["MEDIA_PATH"] = "/tmp/test_media"
    # Create the directory if it doesn't exist
    os.makedirs("/tmp/test_media", exist_ok=True)
    print(f"Media directory created at: {os.environ['MEDIA_PATH']}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
