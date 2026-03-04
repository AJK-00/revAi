import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# Load embedding model once (important)
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

def chunk_text(text, chunk_size=800):
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunks.append(text[i:i + chunk_size])
    return chunks


def embed_chunks(chunks):
    embeddings = embedding_model.encode(chunks)
    return np.array(embeddings).astype("float32")


def build_faiss_index(embeddings):
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    return index


def retrieve_relevant_chunks(query, chunks, index, top_k=5):
    query_embedding = embedding_model.encode([query]).astype("float32")
    distances, indices = index.search(query_embedding, top_k)

    return [chunks[i] for i in indices[0]]