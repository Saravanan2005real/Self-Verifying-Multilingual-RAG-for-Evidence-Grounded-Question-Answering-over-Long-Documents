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
MIN_CHUNK_WORDS = int(os.getenv("MIN_CHUNK_WORDS", "250"))
TARGET_CHUNK_WORDS = int(os.getenv("TARGET_CHUNK_WORDS", "450"))
MAX_CHUNK_WORDS = int(os.getenv("MAX_CHUNK_WORDS", "750"))
CHUNK_OVERLAP_WORDS = int(os.getenv("CHUNK_OVERLAP_WORDS", "40"))

# Ollama & Llama 3.2 Semantic Chunking Parameters
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
SEMANTIC_MODEL = os.getenv("SEMANTIC_MODEL", "llama3.2")
SEMANTIC_CHUNKING_ENABLED = os.getenv("SEMANTIC_CHUNKING_ENABLED", "true").lower() in ("true", "1", "yes")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "30"))

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
