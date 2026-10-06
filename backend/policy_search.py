"""
Simple policy search over the local knowledge base (sample_policies/).

How it works (TF-IDF + cosine similarity, written in plain Python):

1. Every policy file is split into small chunks (paragraphs).
2. Each chunk is turned into a TF-IDF vector:
      TF  = how often a word appears in the chunk
      IDF = how rare the word is across all chunks (rare words matter more)
3. The search query is turned into a vector the same way.
4. Chunks are ranked by cosine similarity (the angle between the vectors).

The index is rebuilt automatically when files in the folder change.
No vector database or external service is needed.
"""
import math
import re
from collections import Counter
from pathlib import Path

import config

POLICY_EXTENSIONS = {".txt", ".md"}
DISCLAIMER_MARKER = "FICTIONAL SAMPLE POLICY"

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "by", "can", "for", "from", "has", "have",
    "if", "in", "into", "is", "it", "its", "may", "must", "not", "of", "on", "or", "should", "such",
    "that", "the", "their", "then", "there", "these", "this", "to", "was", "were", "will", "with",
    "within", "which", "who", "when", "where", "what", "all", "any", "each", "other", "than", "also",
}


def tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in words if len(w) > 1 and w not in STOPWORDS]


def split_into_chunks(text: str) -> list[str]:
    """Split a document into paragraphs. Short headings are merged with the next paragraph."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks = []
    pending_heading = ""
    for paragraph in paragraphs:
        is_heading = len(paragraph) < 80 and "\n" not in paragraph and not paragraph.endswith(".")
        if is_heading:
            pending_heading = (pending_heading + "\n" + paragraph).strip()
            continue
        chunks.append((pending_heading + "\n" + paragraph).strip())
        pending_heading = ""
    if pending_heading:
        chunks.append(pending_heading)
    return chunks


def read_policy_title(path: Path, content: str) -> str:
    first_line = content.strip().splitlines()[0] if content.strip() else path.stem
    return first_line.removeprefix("Title:").strip() or path.stem


class PolicyIndex:
    def __init__(self, policy_dir: Path):
        self.policy_dir = Path(policy_dir)
        self.chunks: list[dict] = []  # {source, title, text, vector}
        self.idf: dict[str, float] = {}
        self._signature = None

    def _current_signature(self):
        if not self.policy_dir.is_dir():
            return ()
        return tuple(
            (p.name, p.stat().st_mtime, p.stat().st_size)
            for p in sorted(self.policy_dir.iterdir())
            if p.suffix.lower() in POLICY_EXTENSIONS
        )

    def refresh_if_needed(self):
        signature = self._current_signature()
        if signature != self._signature:
            self._build()
            self._signature = signature

    def _build(self):
        self.chunks = []
        if not self.policy_dir.is_dir():
            self.idf = {}
            return

        for path in sorted(self.policy_dir.iterdir()):
            if path.suffix.lower() not in POLICY_EXTENSIONS:
                continue
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue  # unreadable file: skip it instead of crashing
            title = read_policy_title(path, content)
            body = content.strip()
            if body.startswith("Title:"):
                body = body.split("\n", 1)[1] if "\n" in body else ""  # the title is indexed separately below
            for chunk_text in split_into_chunks(body):
                if chunk_text.startswith(DISCLAIMER_MARKER):
                    continue  # the "fictional sample" disclaimer is not useful as a search result
                # The document title is indexed with every chunk, so a paragraph can be
                # found by the topic of its document (e.g. "missing information").
                tokens = tokenize(title) + tokenize(chunk_text)
                self.chunks.append({"source": path.name, "title": title, "text": chunk_text, "tokens": tokens})

        # Document frequency: in how many chunks does each word appear?
        document_frequency = Counter()
        for chunk in self.chunks:
            document_frequency.update(set(chunk["tokens"]))

        total = len(self.chunks)
        self.idf = {word: math.log((1 + total) / (1 + df)) + 1 for word, df in document_frequency.items()}
        for chunk in self.chunks:
            chunk["vector"] = self._vectorize(chunk["tokens"])

    def _vectorize(self, tokens: list[str]) -> dict[str, float]:
        counts = Counter(tokens)
        vector = {word: count * self.idf.get(word, 0.0) for word, count in counts.items()}
        length = math.sqrt(sum(v * v for v in vector.values()))
        if length == 0:
            return {}
        return {word: value / length for word, value in vector.items()}

    def search(self, query: str, top_k: int = 3, min_score: float = 0.05, relative_cutoff: float = 0.0) -> list[dict]:
        """
        Return the best matching chunks.
        relative_cutoff: drop results scoring below this fraction of the best score
        (e.g. 0.7 keeps only results that are at least 70% as relevant as the top one).
        """
        self.refresh_if_needed()
        query_vector = self._vectorize(tokenize(query or ""))
        if not query_vector or not self.chunks:
            return []

        results = []
        for chunk in self.chunks:
            # Cosine similarity of two unit-length vectors = dot product.
            score = sum(value * chunk["vector"].get(word, 0.0) for word, value in query_vector.items())
            if score >= min_score:
                results.append({"source": chunk["source"], "title": chunk["title"], "excerpt": chunk["text"], "score": round(score, 3)})

        results.sort(key=lambda r: r["score"], reverse=True)
        if results and relative_cutoff:
            best_score = results[0]["score"]
            results = [r for r in results if r["score"] >= best_score * relative_cutoff]
        return results[:top_k]


_index = None


def get_index() -> PolicyIndex:
    """Return the shared index (created lazily, rebuilt if the folder path changed)."""
    global _index
    if _index is None or _index.policy_dir != Path(config.POLICY_DIR):
        _index = PolicyIndex(config.POLICY_DIR)
    return _index


def search_policies(query: str, top_k: int = 3, relative_cutoff: float = 0.0) -> list[dict]:
    """Search the policy knowledge base. Returns [] (never raises) if nothing is found."""
    try:
        return get_index().search(query, top_k=top_k, relative_cutoff=relative_cutoff)
    except Exception:
        return []


def list_policies() -> list[dict]:
    policy_dir = Path(config.POLICY_DIR)
    if not policy_dir.is_dir():
        return []
    policies = []
    for path in sorted(policy_dir.iterdir()):
        if path.suffix.lower() in POLICY_EXTENSIONS:
            content = path.read_text(encoding="utf-8", errors="replace")
            policies.append({"filename": path.name, "title": read_policy_title(path, content), "size_bytes": path.stat().st_size})
    return policies


def read_policy(filename: str) -> dict | None:
    """Read one policy file. Only plain file names inside the policy folder are allowed."""
    safe_name = Path(filename).name
    path = Path(config.POLICY_DIR) / safe_name
    if safe_name != filename or path.suffix.lower() not in POLICY_EXTENSIONS or not path.is_file():
        return None
    content = path.read_text(encoding="utf-8", errors="replace")
    return {"filename": safe_name, "title": read_policy_title(path, content), "size_bytes": path.stat().st_size, "content": content}
