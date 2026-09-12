import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables if .env exists
load_dotenv()

# Root directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Storage Directories
DATA_DIR = BASE_DIR / os.getenv("DATA_DIR", "data")
UPLOADS_DIR = BASE_DIR / os.getenv("UPLOADS_DIR", "data/uploads")
PROCESSED_DIR = BASE_DIR / os.getenv("PROCESSED_DIR", "data/processed")

# Chunking Parameters
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))        # Target characters per chunk
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))  # Overlap characters between chunks

# OCR Parameters
# If text on a page has fewer characters than this threshold and images exist, OCR is triggered
OCR_CHAR_THRESHOLD = int(os.getenv("OCR_CHAR_THRESHOLD", "30"))
TESSERACT_CMD = os.getenv("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")

def ensure_directories():
    """Ensure all required runtime directories exist."""
    for directory in [DATA_DIR, UPLOADS_DIR, PROCESSED_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

# Run directory check on import
ensure_directories()
