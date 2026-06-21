try:
    from langchain_chroma import Chroma
    from langchain_huggingface import HuggingFaceEmbeddings
except Exception:
    # Fallback stubs for environments without these packages (tests/local runs)
    class HuggingFaceEmbeddings:
        def __init__(self, model_name: str):
            self.model_name = model_name

    class Chroma:
        def __init__(self, collection_name: str, embedding_function=None, persist_directory: str | None = None):
            self.collection_name = collection_name
            self.embedding_function = embedding_function
            self.persist_directory = persist_directory

        def similarity_search_with_score(self, query: str, k: int = 3, filter: dict | None = None):
            return []

from incident_resolution_agent.models.runbook_models import RetrievedRunbookChunk


class RunbookRetriever:
    """
    Low-level deterministic retriever.

    Responsibility:
    - Connect to existing Chroma vector store
    - Run similarity search
    - Apply optional metadata filtering
    - Return retrieved chunks

    This class does not call any LLM.
    """

    def __init__(
        self,
        persist_directory: str,
        collection_name: str = "runbooks",
        embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model_name

        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model_name
        )

        self.vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=persist_directory,
        )

    def search(
        self,
        query: str,
        top_k: int = 3,
        category: str | None = None,
    ) -> list[RetrievedRunbookChunk]:
        if not query or not query.strip():
            return []

        metadata_filter = self._build_filter(category)

        results = self.vector_store.similarity_search_with_score(
            query=query,
            k=top_k,
            filter=metadata_filter,
        )

        return [
            self._to_retrieved_chunk(document=doc, score=score)
            for doc, score in results
        ]

    def _build_filter(self, category: str | None) -> dict | None:
        if not category or category.upper() == "UNKNOWN":
            return None

        return {"category": category.upper()}

    def _to_retrieved_chunk(self, document, score: float | None) -> RetrievedRunbookChunk:
        metadata = document.metadata or {}

        return RetrievedRunbookChunk(
            chunk_id=metadata.get("chunk_id", ""),
            text=document.page_content,
            source=metadata.get("source", metadata.get("file_path", "unknown")),
            title=metadata.get("title", "Unknown Runbook"),
            category=metadata.get("category"),
            score=score,
            metadata=metadata,
        )
