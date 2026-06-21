from pathlib import Path

from incident_resolution_agent.models.runbook_models import RunbookSearchRequest
from incident_resolution_agent.rag.retrieval.runbook_retrieval_agent import RunbookRetrievalAgent
from incident_resolution_agent.rag.retrieval.runbook_retriever import RunbookRetriever


def main() -> None:
    project_root = Path(__file__).parent
    chroma_path = project_root / "app" / "vector_store" / "chroma"

    retriever = RunbookRetriever(
        persist_directory=str(chroma_path),
        collection_name="runbooks",
        embedding_model_name="sentence-transformers/all-MiniLM-L6-v2",
    )

    agent = RunbookRetrievalAgent(
        retriever=retriever,
        llm=None,  # Add your LLM later. Fallback mode works without LLM.
    )

    request = RunbookSearchRequest(
        query="DB connection pool exhaustion Hikari SQLTransientConnectionException",
        top_k=3,
        category="DATABASE",
        insight_confidence=0.87,
    )

    result = agent.search(request)

    print("\nMatched Runbooks:")
    for item in result.matched_runbooks:
        print(f"- {item}")

    print("\nRelevant Steps:")
    for step in result.relevant_steps:
        print(f"- {step}")

    print("\nSources:")
    for source in result.source_documents:
        print(f"- {source}")

    print("\nSummary:")
    print(result.summary)

    print("\nFallback Used:")
    print(result.fallback_used)


if __name__ == "__main__":
    main()
