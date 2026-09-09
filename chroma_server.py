"""
ChromaDB Local Server for DocQuery AI
Runs a persistent ChromaDB instance on http://localhost:8000.
"""

import sys
import os

try:
    import chromadb
    from chromadb.config import Settings
    import uvicorn
except ImportError:
    print("=" * 60)
    print("ChromaDB is not installed in your Python environment.")
    print("To install, run:")
    print("    pip install chromadb")
    print("=" * 60)
    print("\nNote: DocQuery AI includes an automatic in-memory vector store fallback,")
    print("so the backend can run even without ChromaDB!\n")
    sys.exit(1)

def main():
    persist_dir = os.path.join(os.path.dirname(__file__), "chroma_data")
    os.makedirs(persist_dir, exist_ok=True)

    print(f"Starting ChromaDB server on port 8000...")
    print(f"Persistent storage directory: {persist_dir}")
    print("Press Ctrl+C to stop the server.\n")

    # Start chroma via its built-in CLI entrypoint
    from chromadb.cli.cli import app
    sys.argv = ["chroma", "run", "--path", persist_dir, "--port", "8000"]
    app()

if __name__ == "__main__":
    main()
