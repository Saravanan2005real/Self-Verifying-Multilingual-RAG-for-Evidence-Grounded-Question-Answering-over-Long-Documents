import os
import re
import shutil
import logging
from pathlib import Path
from typing import Optional, List, Set
import numpy as np
from PIL import Image

from src.config import TESSERACT_CMD

logger = logging.getLogger(__name__)

__all__ = [
    "is_ocr_available",
    "is_tesseract_available",
    "extract_text_from_image",
    "get_ocr_engine_name",
    "sanitize_ocr_text",
    "find_tesseract_cmd"
]

# Lazy singleton for RapidOCR
_RAPID_OCR_INSTANCE = None

def get_rapid_ocr():
    """Lazy initialize RapidOCR engine."""
    global _RAPID_OCR_INSTANCE
    if _RAPID_OCR_INSTANCE is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _RAPID_OCR_INSTANCE = RapidOCR()
            logger.info("RapidOCR engine initialized successfully.")
        except Exception as e:
            logger.warning(f"Could not initialize RapidOCR: {e}")
            _RAPID_OCR_INSTANCE = False
    return _RAPID_OCR_INSTANCE if _RAPID_OCR_INSTANCE is not False else None

# Search candidate locations for Tesseract on Windows
CANDIDATE_TESSERACT_PATHS = [
    TESSERACT_CMD,
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
]

def find_tesseract_cmd() -> Optional[str]:
    """Check if tesseract binary is available in PATH or default Windows installation folders."""
    in_path = shutil.which("tesseract")
    if in_path:
        return in_path
    
    for path_str in CANDIDATE_TESSERACT_PATHS:
        if path_str and Path(path_str).is_file():
            return path_str
            
    return None

def is_tesseract_available() -> bool:
    """Return True if Tesseract OCR executable is detected."""
    return find_tesseract_cmd() is not None

def is_ocr_available() -> bool:
    """Return True if either Tesseract or RapidOCR is available."""
    if is_tesseract_available():
        return True
    try:
        import rapidocr_onnxruntime
        return True
    except ImportError:
        return False

def get_ocr_engine_name() -> str:
    """Return the name of the active local OCR engine."""
    if is_tesseract_available():
        return "Tesseract OCR"
    try:
        import rapidocr_onnxruntime
        return "RapidOCR (ONNX Local)"
    except ImportError:
        return "None"

# Common OCR correction dictionary for handwritten & technical notes
COMMON_OCR_CORRECTIONS = [
    (r"\b[aA]u[tT]umater\b|\b[aA]omata\b", "Automata"),
    (r"\bsholy\b|\bshdu\b", "study"),
    (r"\bcompehng\b|\bcompuerg\b|\bcomputey\b", "computing"),
    (r"\bmachirey\b|\bmeehire\b", "machines"),
    (r"\b&his\b", "This"),
    (r"\b[cC]onswet\b", "Construct"),
    (r"\b[hH]ranshm\b|\b[hH]ansihon\b|\btransihon\b", "transition"),
    (r"\b[pP]enote\b", "denote"),
    (r"\bbinal\b", "final"),
    (r"\b[sS]ravhng\b|\bstarhng\b|\b[sS]torbing\b", "starting"),
    (r"\b[sS]ral\b|\bsrate\b", "state"),
    (r"\b[sS]tates?\b", "states"),
    (r"\balphabe[t]?\b|\balpha\s+beh\b", "alphabet"),
    (r"\blangoage\b|\blmgog\b|\bbrgugl\b", "language"),
    (r"\bacapts\b|\bacoeptd\b", "accepts"),
    (r"\bsubseh\b|\b[sS]ubseb\b", "subset"),
    (r"\bhnite\b", "finite"),
    (r"\binhnite\b|\binbnite\b|\bihhhile\b|\bihsnihe\b", "infinite"),
    (r"\binleger\b|\bintgos\b", "integers"),
    (r"\bposihive\b", "positive"),
    (r"\b[sS]ewahial\b|\b[sS]euahial\b", "Sequential"),
    (r"\b[pP]ara\s+lle\b", "Parallel"),
    (r"\bedgey\b", "edges"),
    (r"\b[iI]nlermeliale\b|\b[iI]nermediale\b", "intermediate"),
    (r"\b[eE]liminabon\b", "elimination"),
    (r"\b[rR]emonigs\b|\bemongs\b", "removing"),
    (r"\baytey\b|\bafey\b", "after"),
    (r"\bfinalstaty\b", "final states"),
    (r"\b[lL]stale\s+vodey\b|\bvodey\b", "state nodes"),
    (r"\bo[tT]er\s+all\s+fen\b|\boTer\s+all\s+fen\b", "other than"),
    (r"\b[lL]-[aA]cample\b|\bbarampleg\b|\beamplein\b", "Example:"),
    (r"\bmou\s+rmow\b", "remove"),
    (r"\bpahm\b", "path"),
    (r"\bSRM\b", ""),
]

def is_readable_ocr_line(line: str) -> bool:
    """
    Verify that an OCR line contains readable prose rather than pure mathematical formula soup.
    A readable line must contain genuine words (at least one word >= 4 letters or two words >= 3 letters)
    and cannot be purely matrix variable equations (e.g., R13 + R32 = ...).
    """
    line = line.strip()
    if len(line) < 3:
        return False

    alphas = [c for c in line if c.isalpha()]
    if len(alphas) < 3:
        return False

    # Discard pure matrix variable formulas (e.g. lines that have '+' or '=' and no long words)
    long_words = re.findall(r"\b[a-zA-Z]{4,}\b", line)
    med_words = re.findall(r"\b[a-zA-Z]{3,}\b", line)

    has_math = bool(re.search(r"[\+\*\=\/]", line))
    # If it has math symbols but no real English words of length >= 4, it's formula soup
    if has_math and len(long_words) == 0:
        return False

    # Must have either at least 1 word of 4+ letters or 2 words of 3+ letters
    if len(long_words) >= 1 or len(med_words) >= 2:
        return True

    return False

def sanitize_ocr_text(raw_text: str) -> str:
    """
    Cleans raw OCR output:
    - Removes Chinese/Japanese/Korean/Cyrillic hallucinations on sketches
    - Strips scanner watermark tokens
    - Fixes frequent OCR confusions for academic/technical terms
    - Strips diagram arrow equation labels (e.g., R12 + Q1S*P2)
    - Retains coherent prose while filtering pure formula noise
    """
    if not raw_text or not raw_text.strip():
        return ""

    # 1. Remove non-Latin character sets (hallucinations from PP-OCR on non-text lines)
    t = re.sub(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af\u0600-\u06ff\u0400-\u04ff]", " ", raw_text)
    # 2. Remove scanner watermarks
    t = re.sub(r"(?i)scanned\s+by\s+camscanner[^\n]*", "", t)
    # 3. Strip graph arrow matrix algebraic soup
    t = re.sub(r"\b[A-Z]\d+[\+\*][A-Za-z0-9\+\*]*\b", " ", t)
    # 4. Apply domain and handwriting corrections
    for pat, repl in COMMON_OCR_CORRECTIONS:
        t = re.sub(pat, repl, t)
    # 5. Filter noise characters (allow alphanumeric, standard punctuation, math operators)
    t = re.sub(r"[^a-zA-Z0-9\s.,;:()\-–—'\"/=+\*<>_]", " ", t)

    # 6. Line-by-line quality validation
    clean_lines = []
    for line in t.splitlines():
        line = re.sub(r"[ \t]+", " ", line).strip()
        if not is_readable_ocr_line(line):
            continue
        # Strip isolated single characters (like stray ' d ', ' b ')
        line = re.sub(r"(?<!\S)[b-hj-zB-HJ-Z](?!\S)", " ", line)
        line = re.sub(r"[ \t]+", " ", line).strip()
        if len(line) >= 3:
            clean_lines.append(line)

    result = "\n".join(clean_lines).strip()
    return result

def extract_text_from_image(image: Image.Image, lang: str = "eng") -> str:
    """
    Perform local OCR on a PIL Image with image preprocessing and output sanitization.
    Uses Tesseract if available, falling back to RapidOCR.
    """
    # 1. Try Tesseract if installed
    if is_tesseract_available():
        try:
            import pytesseract
            cmd = find_tesseract_cmd()
            if cmd:
                pytesseract.pytesseract.tesseract_cmd = cmd
            if image.mode not in ("L", "RGB"):
                image = image.convert("RGB")
            text = pytesseract.image_to_string(image, lang=lang).strip()
            if text:
                return sanitize_ocr_text(text)
        except Exception as e:
            logger.warning(f"Tesseract OCR failed, attempting fallback: {e}")

    # 2. Try RapidOCR (Local ONNX) with OpenCV preprocessing
    engine = get_rapid_ocr()
    if engine is not None:
        try:
            # Preprocess image for OCR contrast enhancement
            try:
                import cv2
                img_np = np.array(image.convert("RGB"))
                gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                enhanced = clahe.apply(gray)
                ocr_input = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2RGB)
            except Exception:
                ocr_input = np.array(image.convert("RGB"))

            result, _ = engine(ocr_input)
            if not result:
                return ""

            valid_lines = []
            for item in result:
                if not item or len(item) < 3:
                    continue
                text_str = str(item[1]).strip()
                score = float(item[2])
                # Discard very low confidence predictions (noise/smudges)
                if score < 0.55 or not text_str:
                    continue
                valid_lines.append(text_str)

            raw_joined = "\n".join(valid_lines)
            return sanitize_ocr_text(raw_joined)
        except Exception as e:
            logger.error(f"RapidOCR execution error: {e}")
            return ""

    logger.warning("No functional OCR engine available to extract text from image.")
    return ""
