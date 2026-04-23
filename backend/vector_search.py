"""
Vector search module (RAGFlow-inspired) — MVP v2 with Hybrid Search.
Supports: TF-IDF semantic search + keyword exact match + hybrid combination.
No external model download required.
"""
import os
import re
import math
import logging
from collections import Counter

logger = logging.getLogger(__name__)

# In-memory index — per-user isolation (v5.1)
_user_indexes = {}  # user_id -> {file_id -> list of chunk dicts}
_user_idf = {}      # user_id -> {term -> idf score}
_user_doc_counts = {}  # user_id -> int


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """
    Split text into overlapping chunks (RAGFlow-style intelligent chunking).
    Tries to split on paragraph boundaries first, then sentences.
    """
    if not text or len(text) < chunk_size:
        return [text] if text else []

    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current_chunk) + len(para) + 2 <= chunk_size:
            current_chunk = (current_chunk + "\n\n" + para).strip()
        else:
            if current_chunk:
                chunks.append(current_chunk)
            if len(para) > chunk_size:
                sentences = _split_sentences(para)
                sub_chunk = ""
                for sent in sentences:
                    if len(sub_chunk) + len(sent) + 1 <= chunk_size:
                        sub_chunk = (sub_chunk + " " + sent).strip()
                    else:
                        if sub_chunk:
                            chunks.append(sub_chunk)
                        sub_chunk = sent
                if sub_chunk:
                    current_chunk = sub_chunk
                else:
                    current_chunk = ""
            else:
                current_chunk = para

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    sentences = re.split(r'(?<=[.!?\n])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def _tokenize(text: str) -> list[str]:
    """Simple tokenizer for both Thai and English text."""
    text = text.lower()
    # Split on whitespace and punctuation, keep Thai chars together
    tokens = re.findall(r'[a-z0-9]+|[\u0E00-\u0E7F]+', text)
    return tokens


def _compute_tf(tokens: list[str]) -> dict:
    """Compute term frequency."""
    counts = Counter(tokens)
    total = len(tokens)
    return {t: c / total for t, c in counts.items()} if total > 0 else {}


def index_file(file_id: str, filename: str, text: str, cluster_title: str = "", user_id: str = ""):
    """Index a file's text for search (per-user isolated)."""
    if not user_id:
        user_id = "__global__"  # fallback for legacy

    if user_id not in _user_indexes:
        _user_indexes[user_id] = {}
        _user_doc_counts[user_id] = 0

    chunks = chunk_text(text)
    if not chunks:
        return

    chunk_data = []
    for i, chunk in enumerate(chunks):
        tokens = _tokenize(chunk)
        tf = _compute_tf(tokens)
        chunk_data.append({
            "text": chunk,
            "tokens": tokens,
            "tf": tf,
            "chunk_index": i,
            "filename": filename,
            "file_id": file_id,
            "cluster": cluster_title
        })

    _user_indexes[user_id][file_id] = chunk_data
    _user_doc_counts[user_id] = sum(len(c) for c in _user_indexes[user_id].values())

    # Rebuild IDF for this user
    _rebuild_idf(user_id)
    logger.info(f"Indexed {len(chunks)} chunks for {filename} (user={user_id[:8]}..)")


def _rebuild_idf(user_id: str):
    """Rebuild IDF scores for a specific user's documents."""
    index = _user_indexes.get(user_id, {})
    doc_freq = Counter()
    total = 0
    for file_chunks in index.values():
        for chunk in file_chunks:
            unique_terms = set(chunk["tokens"])
            for term in unique_terms:
                doc_freq[term] += 1
            total += 1

    if total == 0:
        _user_idf[user_id] = {}
        return

    _user_idf[user_id] = {term: math.log(total / (1 + freq)) for term, freq in doc_freq.items()}


def search(query: str, n_results: int = 8, file_ids: list = None, user_id: str = "") -> list[dict]:
    """
    Search indexed documents using TF-IDF cosine similarity.
    Returns relevant chunks with metadata and relevance scores.
    Per-user isolated (v5.1).
    """
    if not user_id:
        user_id = "__global__"

    index = _user_indexes.get(user_id, {})
    idf = _user_idf.get(user_id, {})

    if not index:
        return []

    query_tokens = _tokenize(query)
    query_tf = _compute_tf(query_tokens)

    # Compute query TF-IDF vector
    query_tfidf = {t: tf * idf.get(t, 0) for t, tf in query_tf.items()}

    scored = []
    for file_id, chunks in index.items():
        if file_ids and file_id not in file_ids:
            continue
        for chunk in chunks:
            # Compute chunk TF-IDF and cosine similarity
            score = 0
            chunk_norm = 0
            query_norm = 0

            all_terms = set(list(query_tfidf.keys()) + list(chunk["tf"].keys()))
            for term in all_terms:
                q_val = query_tfidf.get(term, 0)
                d_val = chunk["tf"].get(term, 0) * idf.get(term, 0)
                score += q_val * d_val
                chunk_norm += d_val ** 2
                query_norm += q_val ** 2

            chunk_norm = math.sqrt(chunk_norm) if chunk_norm > 0 else 1
            query_norm = math.sqrt(query_norm) if query_norm > 0 else 1
            cosine = score / (chunk_norm * query_norm) if score > 0 else 0

            scored.append({
                "text": chunk["text"],
                "file_id": chunk["file_id"],
                "filename": chunk["filename"],
                "chunk_index": chunk["chunk_index"],
                "cluster": chunk["cluster"],
                "distance": 1 - cosine,
                "relevance": cosine
            })

    # Sort by relevance (highest first)
    scored.sort(key=lambda x: x["relevance"], reverse=True)
    return scored[:n_results]


# ═══════════════════════════════════════════
# MVP v2 — Hybrid Search
# ═══════════════════════════════════════════

def keyword_search(query: str, n_results: int = 8, file_ids: list = None, user_id: str = "") -> list[dict]:
    """
    Keyword-based search — exact/partial term matching.
    Good for proper nouns, specific terms, codes.
    Per-user isolated (v5.1).
    """
    if not user_id:
        user_id = "__global__"

    index = _user_indexes.get(user_id, {})
    if not index:
        return []

    query_tokens = _tokenize(query)
    query_lower = query.lower()

    scored = []
    for file_id, chunks in index.items():
        if file_ids and file_id not in file_ids:
            continue
        for chunk in chunks:
            # Count exact token matches
            chunk_tokens_set = set(chunk["tokens"])
            matches = sum(1 for qt in query_tokens if qt in chunk_tokens_set)

            # Check substring matches in original text
            text_lower = chunk["text"].lower()
            substring_bonus = 0.3 if query_lower in text_lower else 0

            if matches == 0 and substring_bonus == 0:
                continue

            token_score = matches / max(len(query_tokens), 1)
            final_score = min(token_score + substring_bonus, 1.0)

            scored.append({
                "text": chunk["text"],
                "file_id": chunk["file_id"],
                "filename": chunk["filename"],
                "chunk_index": chunk["chunk_index"],
                "cluster": chunk["cluster"],
                "distance": 1 - final_score,
                "relevance": final_score
            })

    scored.sort(key=lambda x: x["relevance"], reverse=True)
    return scored[:n_results]


def hybrid_search(
    query: str,
    n_results: int = 8,
    file_ids: list = None,
    alpha: float = 0.6,
    user_id: str = "",
) -> list[dict]:
    """
    Hybrid search combining semantic (TF-IDF) and keyword matching.
    alpha controls the balance: 1.0 = pure semantic, 0.0 = pure keyword.
    Per-user isolated (v5.1).
    """
    semantic_results = search(query, n_results=n_results * 2, file_ids=file_ids, user_id=user_id)
    keyword_results = keyword_search(query, n_results=n_results * 2, file_ids=file_ids, user_id=user_id)

    # Merge results by chunk identity (file_id + chunk_index)
    merged = {}

    for r in semantic_results:
        key = f"{r['file_id']}:{r['chunk_index']}"
        merged[key] = {
            **r,
            "semantic_score": r["relevance"],
            "keyword_score": 0,
            "search_mode": "semantic"
        }

    for r in keyword_results:
        key = f"{r['file_id']}:{r['chunk_index']}"
        if key in merged:
            merged[key]["keyword_score"] = r["relevance"]
            merged[key]["search_mode"] = "hybrid"
        else:
            merged[key] = {
                **r,
                "semantic_score": 0,
                "keyword_score": r["relevance"],
                "search_mode": "keyword"
            }

    # Compute hybrid score
    for key, item in merged.items():
        item["relevance"] = (
            alpha * item["semantic_score"] +
            (1 - alpha) * item["keyword_score"]
        )
        item["distance"] = 1 - item["relevance"]

    results = sorted(merged.values(), key=lambda x: x["relevance"], reverse=True)
    return results[:n_results]


def is_available() -> bool:
    """Always available since it's pure Python."""
    return True

