"""
Vector search module (RAGFlow-inspired).
Uses TF-IDF + cosine similarity for lightweight semantic search.
No external model download required.

Reference: RAGFlow
- Intelligent chunking
- Relevance scoring
- Context assembly from relevant chunks
"""
import os
import re
import math
import logging
from collections import Counter

logger = logging.getLogger(__name__)

# In-memory index
_index = {}  # file_id -> list of chunk dicts
_idf = {}    # term -> idf score
_total_docs = 0


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


def index_file(file_id: str, filename: str, text: str, cluster_title: str = ""):
    """Index a file's text for search."""
    global _total_docs, _idf

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

    _index[file_id] = chunk_data
    _total_docs += len(chunks)

    # Rebuild IDF across all indexed chunks
    _rebuild_idf()
    logger.info(f"Indexed {len(chunks)} chunks for {filename}")


def _rebuild_idf():
    """Rebuild IDF scores across all indexed documents."""
    global _idf
    doc_freq = Counter()
    total = 0
    for file_chunks in _index.values():
        for chunk in file_chunks:
            unique_terms = set(chunk["tokens"])
            for term in unique_terms:
                doc_freq[term] += 1
            total += 1

    if total == 0:
        _idf = {}
        return

    _idf = {term: math.log(total / (1 + freq)) for term, freq in doc_freq.items()}


def search(query: str, n_results: int = 8, file_ids: list = None) -> list[dict]:
    """
    Search indexed documents using TF-IDF cosine similarity.
    Returns relevant chunks with metadata and relevance scores.
    """
    if not _index:
        return []

    query_tokens = _tokenize(query)
    query_tf = _compute_tf(query_tokens)

    # Compute query TF-IDF vector
    query_tfidf = {t: tf * _idf.get(t, 0) for t, tf in query_tf.items()}

    scored = []
    for file_id, chunks in _index.items():
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
                d_val = chunk["tf"].get(term, 0) * _idf.get(term, 0)
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


def is_available() -> bool:
    """Always available since it's pure Python."""
    return True
