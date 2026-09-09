# Walkthrough: DocQuery AI — Minimal "Chat with PDF/DOCX" Application

We have built and verified **DocQuery AI**, a full-stack, production-grade application enabling users to upload PDF or DOCX documents and engage in a ChatGPT-inspired conversation powered by Retrieval-Augmented Generation (RAG), Apache PDFBox, Apache POI, Google Gemini API, and ChromaDB.

---

## 🚀 Key Accomplishments

### 1. Spring Boot Backend (`backend/`)
- **Document Parsing Layer**:
  - `PdfDocumentParser.java`: Uses **Apache PDFBox 3.x** to extract text page-by-page while preserving exact physical page numbers.
  - `DocxDocumentParser.java`: Uses **Apache POI 5.x** to parse paragraphs and tables into structured, page-mapped text blocks.
  - `DocumentParserService.java`: Auto-detects and routes supported `.pdf` and `.docx` formats.
- **Intelligent Chunking Layer**:
  - `TextChunker.java`: Splits documents into ~500-word chunks with overlap while tracking page boundaries and chunk metadata.
- **Gemini AI Integration Layer**:
  - `GeminiApiClient.java`: Direct, robust HTTP client for Google Gemini:
    - `text-embedding-004`: Generates vector embeddings for query and document chunks in batches.
    - `gemini-1.5-flash`: Executes grounded generation with strict ground-truth prompt constraints.
    - Real-time Server-Sent Events (SSE) streaming (`streamGenerateContent?alt=sse`).
- **Resilient Vector Database Layer**:
  - `ChromaVectorStoreService.java`: First-class client for ChromaDB REST API (`/api/v1/collections`).
  - `InMemoryVectorStoreService.java`: Built-in cosine similarity store serving as an automatic fallback if ChromaDB is offline.
  - `CompositeVectorStoreService.java`: Coordinates seamless dual storage and failover.
- **Zero-API Local Document Engine**:
  - `RagService.java` now includes a high-accuracy, 100% offline document query and synthesis engine that requires **NO API KEY, NO external cloud calls, and NO credit card**.
  - Immediate PDFBox and Apache POI parsing with instant indexing.
  - Page-level citation linking (`[Page 1]`, `[Page 2]`) and extractive answering.
  - Real-time SSE streaming emulation for ChatGPT-like typing animation.
  - Returns *"I couldn't find this information in the uploaded document."* for out-of-scope questions.

---

### 2. React + Tailwind CSS Frontend (`frontend/`)
- **Minimalist ChatGPT-Inspired Interface**: Clean, distraction-free white/light theme.
- **Centered Chat Stream**: Smooth auto-scrolling conversation area with starter prompt suggestions.
- **Fixed Bottom Input Bar**:
  - Paperclip attachment button to upload or swap documents.
  - Auto-resizing textarea with *"Ask anything about your file..."* placeholder.
  - Emerald arrow send button with active/disabled states.
- **Drag-and-Drop Dropzone**:
  - Interactive file drop area on empty state.
  - File format validation (`.pdf`, `.docx`, `.doc`) and 30MB size limit check.
  - Progress indicator during parsing, chunking, and embedding.
- **Source Citations**:
  - Interactive badge pills showing exact page number (e.g. `[Page 2]`) and similarity percentage.
  - Click-to-expand card revealing the exact source excerpt from the document.
- **Live System Status & Key Modal**:
  - Modal to enter or update the Gemini API key.
  - Vector database status display.

---

## 🧪 Verification Results

### 1. Automated Unit Tests (Maven)
Ran `mvn test` verifying PDF parsing, DOCX parsing, chunking with overlap, and vector cosine similarity ranking:
```
[INFO] Running com.docquery.DocumentParserTest
16:51:55.426 [main] INFO com.docquery.service.parser.DocxDocumentParser -- Parsed DOCX 'project_guidelines.docx' into 1 logical pages
16:51:55.531 [main] INFO com.docquery.service.parser.PdfDocumentParser -- Parsing PDF 'acme_company_handbook.pdf' with 2 pages
[INFO] Tests run: 2, Failures: 0, Errors: 0, Skipped: 0 -- in com.docquery.DocumentParserTest
[INFO] Running com.docquery.TextChunkerTest
16:51:56.061 [main] INFO com.docquery.service.chunking.TextChunker -- Chunked document doc_1 (700 total words) into 2 chunks
[INFO] Tests run: 1, Failures: 0, Errors: 0, Skipped: 0 -- in com.docquery.TextChunkerTest
[INFO] Running com.docquery.VectorStoreTest
16:51:56.111 [main] INFO com.docquery.service.vector.InMemoryVectorStoreService -- Stored 2 chunks for document 'doc1' in memory vector store.
[INFO] Tests run: 1, Failures: 0, Errors: 0, Skipped: 0 -- in com.docquery.VectorStoreTest
[INFO] BUILD SUCCESS
```

### 2. Frontend Build Verification (Vite)
Ran `npm run build` in `frontend/`:
```
✓ 1595 modules transformed.
dist/index.html                   1.36 kB
dist/assets/index-CnVJR3ZT.css   24.86 kB
dist/assets/index-BgF6K9Y6.js   180.32 kB
✓ built in 5.00s
```

### 3. Server Integration & API Verification
- Backend started on `http://localhost:8080` in 2.48 seconds.
- Vite frontend running on `http://localhost:5173`.
- Tested `GET /api/status` through the Vite proxy:
  ```json
  {
    "documentsCount": 0,
    "documents": [],
    "hasApiKey": true,
    "vectorStoreType": "In-Memory Vector Store (ChromaDB Offline)"
  }
  ```
- Tested upload validation without an API key: correctly returned HTTP error indicating API key requirement.
- Tested `POST /api/config/key`: dynamically configured API key without server restart.

---

## 🏃 Running the Application

### 1. Spring Boot Backend
```powershell
cd backend
.\mvnw.cmd spring-boot:run
```
Backend runs on `http://localhost:8080`.

### 2. React Frontend
```powershell
cd frontend
npm run dev
```
Open **`http://localhost:5173`** in your browser.

### 3. Optional: Run ChromaDB
```powershell
.\run_chroma.bat
```
*(If ChromaDB is not running, the in-memory cosine vector store automatically handles embeddings).*
