import logging
import pymupdf as fitz  # PyMuPDF
import numpy as np
from pathlib import Path
from services.ollama_service import ollama_service

logger = logging.getLogger(__name__)

# Global model cache to avoid re-loading weights on every request
_sentence_transformer_model = None


def get_embedding_model(model_name: str = "all-MiniLM-L6-v2"):
    """Load SentenceTransformer model lazily and cache instance."""
    global _sentence_transformer_model
    if _sentence_transformer_model is None:
        try:
            from sentence_transformers import SentenceTransformer

            logger.info(f"Loading SentenceTransformer model '{model_name}'...")
            _sentence_transformer_model = SentenceTransformer(model_name)
            logger.info("SentenceTransformer model loaded successfully.")
        except Exception as e:
            logger.warning(
                f"SentenceTransformer could not be loaded ({e}). Using TF-IDF/statistical semantic similarity as backup."
            )
            _sentence_transformer_model = None
    return _sentence_transformer_model


class RAGService:
    """Retrieval-Augmented Generation service for PDF notes."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def extract_text_from_pdf(self, pdf_path: str) -> dict:
        """Extract text from PDF using PyMuPDF (fitz), tracking page numbers."""
        pages_data = []
        full_text_list = []

        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)

            for page_num in range(total_pages):
                page = doc.load_page(page_num)
                page_text = page.get_text("text").strip()
                if page_text:
                    pages_data.append(
                        {
                            "page": page_num + 1,  # 1-indexed for students
                            "text": page_text,
                        }
                    )
                    full_text_list.append(page_text)

            doc.close()
            return {
                "page_count": total_pages,
                "pages": pages_data,
                "full_text": "\n\n".join(full_text_list),
            }
        except Exception as e:
            logger.error(f"Error reading PDF with PyMuPDF: {e}")
            raise ValueError(f"Could not read PDF: {str(e)}")

    def chunk_document(self, pages_data: list) -> list:
        """Split extracted pages into overlapping chunks with page metadata."""
        chunks = []
        chunk_id = 0

        for page_info in pages_data:
            page_num = page_info["page"]
            text = page_info["text"]

            # Break text into paragraphs or sentences first
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            current_chunk = ""

            for p in paragraphs:
                if len(current_chunk) + len(p) <= self.chunk_size:
                    current_chunk += (" " if current_chunk else "") + p
                else:
                    if current_chunk:
                        chunks.append(
                            {
                                "id": chunk_id,
                                "page": page_num,
                                "text": current_chunk.strip(),
                            }
                        )
                        chunk_id += 1
                        # Retain overlap from end of current chunk
                        overlap_text = current_chunk[-self.chunk_overlap :]
                        current_chunk = overlap_text + " " + p
                    else:
                        # Paragraph itself is longer than chunk_size, split by slicing
                        for i in range(0, len(p), self.chunk_size - self.chunk_overlap):
                            slice_text = p[i : i + self.chunk_size]
                            chunks.append(
                                {
                                    "id": chunk_id,
                                    "page": page_num,
                                    "text": slice_text.strip(),
                                }
                            )
                            chunk_id += 1
                        current_chunk = ""

            if current_chunk.strip():
                chunks.append(
                    {
                        "id": chunk_id,
                        "page": page_num,
                        "text": current_chunk.strip(),
                    }
                )
                chunk_id += 1

        return chunks

    def compute_embeddings(self, texts: list):
        """Generate dense vector embeddings using Sentence Transformers."""
        model = get_embedding_model()
        if model is not None:
            try:
                embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
                return embeddings
            except Exception as e:
                logger.warning(f"Error encoding with SentenceTransformer: {e}")

        # Robust TF-IDF cosine similarity fallback if PyTorch or GPU/CPU environment issues occur
        from sklearn.feature_extraction.text import TfidfVectorizer

        vectorizer = TfidfVectorizer(stop_words="english")
        tfidf_mat = vectorizer.fit_transform(texts)
        return tfidf_mat

    def retrieve_relevant_chunks(
        self, query: str, chunks: list, top_k: int = 4
    ) -> list:
        """Retrieve top-k most relevant chunks using cosine similarity."""
        if not chunks:
            return []

        chunk_texts = [c["text"] for c in chunks]

        model = get_embedding_model()
        if model is not None:
            try:
                # Dense embedding retrieval
                query_emb = model.encode([query], convert_to_numpy=True, normalize_embeddings=True)[0]
                chunk_embs = model.encode(chunk_texts, convert_to_numpy=True, normalize_embeddings=True)

                # Cosine similarity for normalized vectors is simply dot product
                similarities = np.dot(chunk_embs, query_emb)
                top_indices = np.argsort(similarities)[::-1][:top_k]

                results = []
                for idx in top_indices:
                    results.append(
                        {
                            "id": chunks[idx]["id"],
                            "page": chunks[idx]["page"],
                            "text": chunks[idx]["text"],
                            "score": float(similarities[idx]),
                        }
                    )
                return results
            except Exception as e:
                logger.warning(f"Dense retrieval failed, using TF-IDF fallback: {e}")

        # TF-IDF fallback retrieval
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        vectorizer = TfidfVectorizer(stop_words="english")
        matrix = vectorizer.fit_transform(chunk_texts + [query])
        query_vec = matrix[-1]
        chunk_vecs = matrix[:-1]

        sims = cosine_similarity(chunk_vecs, query_vec).flatten()
        top_indices = np.argsort(sims)[::-1][:top_k]

        results = []
        for idx in top_indices:
            results.append(
                {
                    "id": chunks[idx]["id"],
                    "page": chunks[idx]["page"],
                    "text": chunks[idx]["text"],
                    "score": float(sims[idx]),
                }
            )
        return results

    def answer_question(self, query: str, chunks: list, top_k: int = 4) -> dict:
        """End-to-end RAG: retrieve chunks, pass to Ollama, return answer + sources."""
        relevant = self.retrieve_relevant_chunks(query, chunks, top_k=top_k)

        # Check if top score is basically zero (irrelevant)
        if not relevant or (relevant and relevant[0].get("score", 0) <= 0.05):
            return {
                "answer": "The uploaded notes do not contain enough information to answer this question.",
                "sources": [],
            }

        answer = ollama_service.answer_document_question(query, relevant)
        pages = sorted(list(set(r["page"] for r in relevant)))

        return {
            "answer": answer,
            "sources": [{"page": p} for p in pages],
            "retrieved_chunks": relevant,
        }


rag_service = RAGService()
