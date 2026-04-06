"""
rag_engine.py
-------------
Lightweight RAG using TF-IDF + cosine similarity.
Replaces sentence-transformers (2GB+) with sklearn (tiny).
"""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def chunk_text(text: str, chunk_size: int = 800) -> list:
    chunks = []
    overlap = 100
    start = 0
    while start < len(text):
        chunk = text[start:start + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def retrieve_relevant_chunks(query: str, chunks: list, top_k: int = 5) -> list:
    """
    TF-IDF based retrieval — no model download, works on any machine.
    Returns the top_k most relevant chunks for the query.
    """
    if not chunks:
        return []

    top_k = min(top_k, len(chunks))

    try:
        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=10000,
        )
        # Fit on all chunks + query together
        all_texts   = chunks + [query]
        tfidf_matrix = vectorizer.fit_transform(all_texts)

        # Query vector is the last row
        query_vec   = tfidf_matrix[-1]
        chunk_vecs  = tfidf_matrix[:-1]

        # Cosine similarity between query and each chunk
        scores = cosine_similarity(query_vec, chunk_vecs).flatten()

        # Return top_k chunks sorted by score
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [chunks[i] for i in top_indices]

    except Exception as e:
        print(f"[rag_engine] Retrieval error: {e} — returning first {top_k} chunks")
        return chunks[:top_k]