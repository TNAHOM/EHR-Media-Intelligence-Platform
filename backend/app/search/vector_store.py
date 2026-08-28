from pathlib import Path
from typing import Any, cast

import chromadb
from app.core.config import settings
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer


class EmbeddingEngine:
    """Singleton embedding engine running sentence-transformers locally on CPU."""

    _model: SentenceTransformer | None = None

    @classmethod
    def get_model(cls) -> SentenceTransformer:
        if cls._model is None:
            cls._model = SentenceTransformer(settings.EMBEDDING_MODEL)
        return cls._model

    @classmethod
    def embed_text(cls, text: str) -> list[float]:
        model = cls.get_model()
        return model.encode(text, normalize_embeddings=True).tolist()  # type: ignore

    @classmethod
    def embed_batch(cls, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = cls.get_model()
        return model.encode(
            texts, normalize_embeddings=True, show_progress_bar=False
        ).tolist()  # type: ignore


class ChromaVectorStore:
    """Manages the persistent ChromaDB collection for clinical vector search."""

    COLLECTION_NAME = "ehr_clinical_records"

    def __init__(self):
        Path(settings.CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        # Using Cosine distance metric
        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert_records(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        if not ids:
            return
        self.collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=cast(Any, embeddings),
            metadatas=cast(Any, metadatas),
        )

    def query(
        self,
        query_embedding: list[float],
        where_filter: dict[str, Any] | None = None,
        top_k: int = 5,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if where_filter:
            kwargs["where"] = where_filter

        raw_res = self.collection.query(**kwargs)
        return cast(dict[str, Any], raw_res)

    def reset_collection(self) -> None:
        self.client.delete_collection(self.COLLECTION_NAME)
        self.collection = self.client.create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def count(self) -> int:
        return self.collection.count()


# Global vector store instance
vector_store = ChromaVectorStore()
