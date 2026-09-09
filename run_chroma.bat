@echo off
echo ============================================================
echo Starting ChromaDB for DocQuery AI on port 8000
echo ============================================================
python -m pip install chromadb >nul 2>&1
python chroma_server.py
pause
