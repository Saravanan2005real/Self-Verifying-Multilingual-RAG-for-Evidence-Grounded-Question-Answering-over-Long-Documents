import re
import logging
from typing import Tuple, List, Dict, Any, Optional
import langdetect
from langdetect import DetectorFactory
from langdetect.lang_detect_exception import LangDetectException

logger = logging.getLogger(__name__)

# Enforce deterministic results from langdetect
DetectorFactory.seed = 0

# Mapping of common ISO 639-1 language codes to human-readable names
LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "bn": "Bengali",
    "mr": "Marathi",
    "gu": "Gujarati",
    "kn": "Kannada",
    "ml": "Malayalam",
    "pa": "Punjabi",
    "ur": "Urdu",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "zh-cn": "Chinese",
    "ar": "Arabic",
    "ru": "Russian",
    "ja": "Japanese",
}

# Regex patterns for distinct linguistic scripts (deterministic identification)
SCRIPT_PATTERNS = {
    "hi": re.compile(r"[\u0900-\u097F]"),  # Devanagari (Hindi, Marathi)
    "ta": re.compile(r"[\u0B80-\u0BFF]"),  # Tamil
    "te": re.compile(r"[\u0C00-\u0C7F]"),  # Telugu
    "bn": re.compile(r"[\u0980-\u09FF]"),  # Bengali
    "kn": re.compile(r"[\u0C80-\u0CFF]"),  # Kannada
    "ml": re.compile(r"[\u0D00-\u0D7F]"),  # Malayalam
    "gu": re.compile(r"[\u0A80-\u0AFF]"),  # Gujarati
    "pa": re.compile(r"[\u0A00-\u0A7F]"),  # Gurmukhi (Punjabi)
    "ur": re.compile(r"[\u0600-\u06FF]"),  # Arabic / Urdu script
}

def get_language_name(code: str) -> str:
    """Return human-friendly name for an ISO 639-1 language code."""
    return LANGUAGE_NAMES.get(code.lower(), code.upper())

def detect_script(text: str, min_char_threshold: int = 12) -> Optional[str]:
    """
    Check if text contains substantial characters from a distinctive script (e.g. Tamil, Telugu, Hindi).
    Returns the language code if threshold is met, else None.
    """
    for lang, pattern in SCRIPT_PATTERNS.items():
        matches = pattern.findall(text)
        if len(matches) >= min_char_threshold:
            return lang
    return None

def clean_prose_for_detection(text: str) -> str:
    """
    Filter out math formulas, isolated variables (q0, delta, epsilon), numbers,
    punctuation, and single-letter tokens to isolate real linguistic prose words.
    """
    # Remove math symbols, brackets, arrows, and numbers
    text_clean = re.sub(r"[\d\(\)\[\]\{\}\=\+\-\*\/\<\>\→\⇒\δ\ε\Φ\Σ\_\:\;\,\.\?\!\@\#\$\%\^\&\|\\]+", " ", text)
    # Split into words and only keep tokens with length >= 2
    words = [w for w in text_clean.split() if len(w) >= 2]
    return " ".join(words).strip()

def detect_text_language(
    text: str,
    default: str = "en",
    min_length: int = 50,
    confidence_threshold: float = 0.85
) -> Tuple[str, float]:
    """
    Detect language for a text block using:
    1. Distinctive script detection (100% confidence for Indic scripts like Hindi, Tamil, Telugu).
    2. Prose filtering (removes formulas and single-letter noise).
    3. High-confidence langdetect with probability thresholding.
    Returns (lang_code, confidence).
    """
    if not text or not text.strip():
        return default, 0.0

    # 1. Check for distinctive non-Latin scripts first
    script_lang = detect_script(text)
    if script_lang:
        return script_lang, 1.0

    # 2. Extract clean prose
    prose = clean_prose_for_detection(text)
    if len(prose) < min_length:
        return default, 0.0

    # 3. Detect with confidence thresholding
    try:
        probabilities = langdetect.detect_langs(prose)
        if probabilities:
            best = probabilities[0]
            if best.prob >= confidence_threshold:
                return best.lang, float(best.prob)
            else:
                logger.debug(f"Weak language detection ({best.lang}: {best.prob:.2f}) rejected for text: {prose[:40]}...")
                return default, float(best.prob)
        return default, 0.0
    except LangDetectException:
        return default, 0.0
    except Exception as e:
        logger.debug(f"Language detection exception: {e}")
        return default, 0.0

def detect_language(text: str, default: str = "en") -> str:
    """Backward-compatible simple language detection."""
    lang, _ = detect_text_language(text, default=default)
    return lang

def analyze_document_languages(
    text_blocks: List[str],
    default_lang: str = "en",
    min_presence_ratio: float = 0.08
) -> Dict[str, Any]:
    """
    Aggregate language evidence across the entire document:
    1. Only evaluates clean, substantial prose blocks (ignoring formulas, noise, short fragments).
    2. Computes total volume (characters) per language.
    3. Eliminates weak false-positive languages that account for less than min_presence_ratio (e.g. < 8%).
    4. Calculates actual calculated percentages.
    5. Formats a clear, professional summary string.
    """
    lang_char_counts: Dict[str, int] = {}
    total_analyzed_chars = 0

    # Decompose multi-paragraph blocks or pages into distinct paragraphs
    paragraphs = []
    for block in text_blocks:
        if not block:
            continue
        for p in re.split(r"\n\s*\n", block):
            p_str = p.strip()
            if len(p_str) >= 20:
                paragraphs.append(p_str)

    for block in paragraphs:
        # Check script first (for Indic scripts: Tamil, Telugu, Hindi, etc.)
        script_lang = detect_script(block, min_char_threshold=10)
        if script_lang:
            char_count = len(block.strip())
            lang_char_counts[script_lang] = lang_char_counts.get(script_lang, 0) + char_count
            total_analyzed_chars += char_count
            continue

        # Clean prose for Latin/other languages
        prose = clean_prose_for_detection(block)
        if len(prose) < 50:
            continue

        try:
            probs = langdetect.detect_langs(prose)
            if probs:
                best = probs[0]
                if best.prob >= 0.85:
                    count = len(prose)
                    lang_char_counts[best.lang] = lang_char_counts.get(best.lang, 0) + count
                    total_analyzed_chars += count
        except Exception:
            continue

    # If insufficient clean text was found to evaluate, default to English
    if total_analyzed_chars == 0 or not lang_char_counts:
        return {
            "primary_language": default_lang,
            "detected_languages": [default_lang],
            "language_breakdown": {default_lang: 100.0},
            "is_multilingual": False,
            "summary_display": f"{get_language_name(default_lang)} ({default_lang})"
        }

    # Calculate actual percentage per detected language
    percentages = {
        lang: (count / total_analyzed_chars) * 100.0
        for lang, count in lang_char_counts.items()
    }

    # Filter out weak/insignificant languages below the minimum threshold (e.g. < 8%)
    significant_langs = {
        lang: pct for lang, pct in percentages.items()
        if pct >= (min_presence_ratio * 100.0)
    }

    # If filtering eliminated everything, keep the top single language
    if not significant_langs:
        top_lang = max(percentages.items(), key=lambda x: x[1])[0]
        significant_langs = {top_lang: 100.0}

    # Re-normalize percentages of significant languages so they total 100%
    sum_sig = sum(significant_langs.values())
    normalized_breakdown = {
        lang: round((pct / sum_sig) * 100.0, 1)
        for lang, pct in significant_langs.items()
    }

    # Sort descending by proportion
    sorted_breakdown = dict(sorted(normalized_breakdown.items(), key=lambda x: x[1], reverse=True))
    primary_lang = list(sorted_breakdown.keys())[0]
    is_multilingual = len(sorted_breakdown) > 1

    # Format user-facing display string
    if not is_multilingual or sorted_breakdown[primary_lang] >= 90.0:
        summary_display = f"{get_language_name(primary_lang)} ({primary_lang})"
    else:
        parts = [
            f"{get_language_name(lang)} ({lang}) — {pct:.0f}%"
            for lang, pct in sorted_breakdown.items()
        ]
        summary_display = ", ".join(parts)

    return {
        "primary_language": primary_lang,
        "detected_languages": list(sorted_breakdown.keys()),
        "language_breakdown": sorted_breakdown,
        "is_multilingual": is_multilingual,
        "summary_display": summary_display
    }
