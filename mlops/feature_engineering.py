"""
mlops/feature_engineering.py
Extract numerical features from raw text content for ML classification.
"""
import re
import math
from typing import Dict, List


_SENSITIVE_KEYWORDS = [
    "password", "secret", "confidential", "private", "restricted",
    "classified", "proprietary", "token", "credential",
    "api_key", "access_key", "private_key", "ssn", "credit_card",
]

_REGEX_PATTERNS = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(
        r"\b(?:4[0-9]{3}|5[1-5][0-9]{2}|3[47][0-9]{2}|6011|65[0-9]{2})"
        r"[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}(?:[- ]?\d{3})?\b"
    ),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "phone": re.compile(r"\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "api_key": re.compile(
        r"\b(?:api[_-]?key|access[_-]?key|secret[_-]?key|auth[_-]?token)"
        r"\s*[=:]\s*[A-Za-z0-9+/._-]{20,}\b",
        re.IGNORECASE,
    ),
    "password": re.compile(r"\bpassword\s*[=:]\s*\S+\b", re.IGNORECASE),
    "secret": re.compile(r"\bsecret\s*[=:]\s*\S+\b", re.IGNORECASE),
}

FEATURE_NAMES: List[str] = [
    "char_count",
    "word_count",
    "line_count",
    "entropy",
    "digit_ratio",
    "upper_ratio",
    "special_char_ratio",
    "keyword_density",
    "pattern_match_count",
    "avg_word_length",
    "ssn_count",
    "credit_card_count",
    "email_count",
    "phone_count",
    "api_key_count",
    "password_count",
    "secret_count",
]


def _shannon_entropy(text: str) -> float:
    """Calculate normalised Shannon entropy of the text."""
    if not text:
        return 0.0
    freq: Dict[str, int] = {}
    for ch in text:
        freq[ch] = freq.get(ch, 0) + 1
    total = len(text)
    entropy = -sum((c / total) * math.log2(c / total) for c in freq.values())
    # Normalise to [0, 1] by dividing by log2(total unique chars)
    max_entropy = math.log2(len(freq)) if len(freq) > 1 else 1.0
    return entropy / max_entropy


def extract_features(content: str) -> List[float]:
    """
    Convert raw text content into a fixed-length feature vector.

    Returns
    -------
    list[float]
        A vector matching the order of FEATURE_NAMES.
    """
    if not content:
        return [0.0] * len(FEATURE_NAMES)

    content_lower = content.lower()
    chars = len(content)
    words = content.split()
    lines = content.splitlines()

    digit_count = sum(1 for c in content if c.isdigit())
    upper_count = sum(1 for c in content if c.isupper())
    special_count = sum(1 for c in content if not c.isalnum() and not c.isspace())
    avg_word_len = (sum(len(w) for w in words) / len(words)) if words else 0.0

    keyword_hits = sum(content_lower.count(kw) for kw in _SENSITIVE_KEYWORDS)
    keyword_density = keyword_hits / len(words) if words else 0.0

    pattern_counts = {name: len(pat.findall(content)) for name, pat in _REGEX_PATTERNS.items()}
    total_pattern_hits = sum(pattern_counts.values())

    return [
        float(chars),
        float(len(words)),
        float(len(lines)),
        _shannon_entropy(content),
        digit_count / chars if chars else 0.0,
        upper_count / chars if chars else 0.0,
        special_count / chars if chars else 0.0,
        keyword_density,
        float(total_pattern_hits),
        avg_word_len,
        float(pattern_counts["ssn"]),
        float(pattern_counts["credit_card"]),
        float(pattern_counts["email"]),
        float(pattern_counts["phone"]),
        float(pattern_counts["api_key"]),
        float(pattern_counts["password"]),
        float(pattern_counts["secret"]),
    ]
