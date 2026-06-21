import json
from typing import Any

from incident_resolution_agent.models.runbook_models import (
    RetrievedRunbookChunk,
    RunbookResult,
    RunbookSearchRequest,
)


class RunbookRetrievalAgent:
    """
    Higher-level runtime agent.

    Responsibility:
    - Decide whether category filtering should be used
    - Call RunbookRetriever
    - Synthesize retrieved chunks into RunbookResult
    - Fallback safely if no chunks or LLM failure

    This class can work with or without an LLM.
    If llm is None, it returns a deterministic fallback from chunks.
    """

    def __init__(
        self,
        retriever,
        llm: Any | None = None,
        category_filter_min_confidence: float = 0.65,
    ):
        self.retriever = retriever
        self.llm = llm
        self.category_filter_min_confidence = category_filter_min_confidence

    def search(self, request: RunbookSearchRequest) -> RunbookResult:
        category_filter = (
            request.category
            if self._should_use_category_filter(request)
            else None
        )

        chunks = self.retriever.search(
            query=request.query,
            top_k=request.top_k,
            category=category_filter,
        )

        if not chunks:
            return self._fallback_no_chunks(request)

        if self.llm is None:
            return self._fallback_from_chunks(chunks)

        prompt = self._build_prompt(request, chunks)

        try:
            response = self.llm.invoke(prompt)
            response_text = self._extract_response_text(response)
            parsed = self._parse_json_response(response_text)
            self._validate_response(parsed)
            return self._to_runbook_result(parsed, chunks)

        except Exception:
            return self._fallback_from_chunks(chunks)

    def _should_use_category_filter(self, request: RunbookSearchRequest) -> bool:
        if not request.category:
            return False

        if request.category.upper() == "UNKNOWN":
            return False

        return request.insight_confidence >= self.category_filter_min_confidence

    def _build_prompt(
        self,
        request: RunbookSearchRequest,
        chunks: list[RetrievedRunbookChunk],
    ) -> str:
        chunks_text = self._format_chunks(chunks)

        return f"""
You are a runbook retrieval assistant for production incident response.

Your job:
Extract useful troubleshooting guidance from retrieved runbook chunks.

Rules:
- Use only the retrieved chunks.
- Do not invent steps.
- Preserve cautions if present.
- Do not claim final root cause.
- Return only valid JSON.

Incident/runbook query:
{request.query}

Issue category:
{request.category}

Retrieved chunks:
{chunks_text}

Return JSON exactly in this format:
{{
  "matched_runbooks": ["runbook title"],
  "confidence": 0.0,
  "relevant_steps": ["step 1", "step 2"],
  "cautions": ["caution 1"],
  "summary": "short summary"
}}
"""

    def _format_chunks(self, chunks: list[RetrievedRunbookChunk]) -> str:
        formatted = []

        for index, chunk in enumerate(chunks, start=1):
            formatted.append(
                f"""
[Chunk {index}]
chunk_id: {chunk.chunk_id}
title: {chunk.title}
source: {chunk.source}
category: {chunk.category}
score: {chunk.score}

content:
{chunk.text}
"""
            )

        return "\n".join(formatted)

    def _extract_response_text(self, response: Any) -> str:
        if isinstance(response, str):
            return response

        if hasattr(response, "content"):
            return response.content

        return str(response)

    def _parse_json_response(self, response_text: str) -> dict:
        response_text = response_text.strip()

        if response_text.startswith("```json"):
            response_text = response_text.replace("```json", "").replace("```", "").strip()

        elif response_text.startswith("```"):
            response_text = response_text.replace("```", "").strip()

        return json.loads(response_text)

    def _validate_response(self, data: dict) -> None:
        required_fields = [
            "matched_runbooks",
            "confidence",
            "relevant_steps",
            "cautions",
            "summary",
        ]

        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        confidence = float(data["confidence"])

        if confidence < 0.0 or confidence > 1.0:
            raise ValueError("Confidence must be between 0 and 1")

        if not isinstance(data["matched_runbooks"], list):
            raise ValueError("matched_runbooks must be a list")

        if not isinstance(data["relevant_steps"], list):
            raise ValueError("relevant_steps must be a list")

        if not isinstance(data["cautions"], list):
            raise ValueError("cautions must be a list")

    def _to_runbook_result(
        self,
        data: dict,
        chunks: list[RetrievedRunbookChunk],
    ) -> RunbookResult:
        return RunbookResult(
            matched_runbooks=data["matched_runbooks"],
            confidence=float(data["confidence"]),
            relevant_steps=data["relevant_steps"],
            cautions=data["cautions"],
            source_documents=self._unique_sources(chunks),
            retrieved_chunks=self._chunk_ids(chunks),
            summary=data["summary"],
            fallback_used=False,
        )

    def _fallback_no_chunks(self, request: RunbookSearchRequest) -> RunbookResult:
        return RunbookResult(
            matched_runbooks=[],
            confidence=0.0,
            relevant_steps=[
                "No matching runbook was found. Expand the query or check a general incident troubleshooting guide."
            ],
            cautions=[],
            source_documents=[],
            retrieved_chunks=[],
            summary=f"No relevant runbook chunks were found for query: {request.query}",
            fallback_used=True,
        )

    def _fallback_from_chunks(
        self,
        chunks: list[RetrievedRunbookChunk],
    ) -> RunbookResult:
        matched_runbooks = self._unique_titles(chunks)
        source_documents = self._unique_sources(chunks)
        chunk_ids = self._chunk_ids(chunks)

        relevant_steps = [
            "Review the retrieved runbook chunks for diagnosis and resolution steps."
        ]

        for chunk in chunks:
            snippet = self._first_meaningful_line(chunk.text)
            if snippet:
                relevant_steps.append(f"{chunk.title}: {snippet}")

        return RunbookResult(
            matched_runbooks=matched_runbooks,
            confidence=0.50,
            relevant_steps=relevant_steps,
            cautions=[],
            source_documents=source_documents,
            retrieved_chunks=chunk_ids,
            summary="Relevant runbook chunks were found, but AI summarization was not used or failed.",
            fallback_used=True,
        )

    def _unique_titles(self, chunks: list[RetrievedRunbookChunk]) -> list[str]:
        seen = []
        for chunk in chunks:
            if chunk.title and chunk.title not in seen:
                seen.append(chunk.title)
        return seen

    def _unique_sources(self, chunks: list[RetrievedRunbookChunk]) -> list[str]:
        seen = []
        for chunk in chunks:
            if chunk.source and chunk.source not in seen:
                seen.append(chunk.source)
        return seen

    def _chunk_ids(self, chunks: list[RetrievedRunbookChunk]) -> list[str]:
        return [
            chunk.chunk_id
            for chunk in chunks
            if chunk.chunk_id
        ]

    def _first_meaningful_line(self, text: str) -> str:
        for line in text.splitlines():
            line = line.strip()

            if not line:
                continue

            if line.startswith("#"):
                continue

            return line[:180]

        return ""
