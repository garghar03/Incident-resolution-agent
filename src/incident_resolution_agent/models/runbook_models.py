from dataclasses import dataclass, field
from typing import Any


@dataclass
class FileIngestionRecord:
    file_path: str
    checksum: str
    size_bytes: int
    last_modified: str
    last_processed_offset: int
    chunk_ids: list[str] = field(default_factory=list)
    status: str = "ACTIVE"


@dataclass
class RunbookDocument:
    file_path: str
    title: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunbookChunk:
    chunk_id: str
    file_path: str
    title: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class IngestionResult:
    new_files: int = 0
    updated_files: int = 0
    appended_files: int = 0
    deleted_files: int = 0
    skipped_files: int = 0
    total_chunks_indexed: int = 0

    def __str__(self) -> str:
        return (
            "IngestionResult("
            f"new_files={self.new_files}, "
            f"updated_files={self.updated_files}, "
            f"appended_files={self.appended_files}, "
            f"deleted_files={self.deleted_files}, "
            f"skipped_files={self.skipped_files}, "
            f"total_chunks_indexed={self.total_chunks_indexed})"
        )


@dataclass
class RetrievedRunbookChunk:
    chunk_id: str
    text: str
    source: str
    title: str
    category: str | None
    score: float | None
    metadata: dict

@dataclass
class RunbookSearchRequest:
    query: str
    top_k: int = 3
    category: str | None = None
    insight_confidence: float = 0.0


@dataclass
class RunbookResult:
    matched_runbooks: list[str]
    confidence: float
    relevant_steps: list[str]
    cautions: list[str]
    source_documents: list[str]
    retrieved_chunks: list[str]
    summary: str
    fallback_used: bool = False
