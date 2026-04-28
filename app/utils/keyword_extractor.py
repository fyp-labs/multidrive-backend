import re
from typing import List, Optional

_STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "for", "from",
    "has", "have", "he", "her", "his", "how", "i", "if", "in", "into", "is", "it",
    "its", "me", "my", "no", "not", "of", "on", "or", "our", "she", "so", "than",
    "that", "the", "their", "them", "then", "there", "these", "they", "this",
    "those", "through", "to", "too", "us", "was", "we", "were", "what", "when",
    "where", "which", "while", "who", "whom", "why", "will", "with", "would",
    "you", "your", "yours", "do", "does", "did", "can", "could", "should",
    "about", "any", "all", "some", "such", "more", "most", "other", "over",
    "out", "up", "down", "off", "just", "very", "also",
})

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9'-]*")


def extract_keywords(query: str, max_keywords: Optional[int] = None) -> List[str]:
    """Extract dedup'd, lowercased, stopword-filtered keywords from a query."""
    if not query:
        return []

    seen: set[str] = set()
    keywords: List[str] = []

    for raw in _TOKEN_RE.findall(query):
        word = raw.lower().strip("-'")
        if len(word) < 2 or word in _STOPWORDS or word in seen:
            continue
        seen.add(word)
        keywords.append(word)
        if max_keywords is not None and len(keywords) >= max_keywords:
            break

    return keywords
