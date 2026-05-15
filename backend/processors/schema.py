"""Standard extraction result schema -- v10.0.0.

Single output shape no matter which processor ran (local/llamaparse/ai_ingest/ocr).
Downstream consumers (upload_worker, organizer, vector_search) see one type.

Lab pattern G: 'Standard Output Schema' (HANDOFF section 2 G).
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ExtractionResult(BaseModel):
    """Result of one extract_text() call.

    `text` is the canonical extracted content for downstream use (search,
    summarize). `markdown` is the same content with structural markers
    preserved -- callers that prefer markdown (Drive push, MCP responses)
    can use it; for legacy upload_worker we copy text into both.

    Cost fields are *estimates* used for admin stats and budget guards,
    never user-facing. `processor_used` is "local" | "llamaparse" |
    "ai_ingest" | "ocr" | "vault".
    """

    text: str = ""
    markdown: str = ""

    processor_used: str = "local"
    fallback_used: Optional[str] = None  # name of fallback if primary failed
    processing_time_seconds: float = 0.0
    cost_cents_estimate: int = 0

    # Truthful diagnostics -- TC-1 / v9.4.0 contract: empty/error is reported,
    # never silently swallowed.
    status: str = "ok"        # "ok" | "empty" | "error"
    error_message: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)

    # Pass-through metadata that processors can populate. Stored as JSON in
    # files.extraction_metadata (created in Phase 5 migration).
    metadata: dict = Field(default_factory=dict)

    def is_useful(self) -> bool:
        """True if we have non-empty content that downstream can index."""
        return self.status == "ok" and bool(self.text.strip())

    @classmethod
    def empty(cls, processor: str, reason: str) -> "ExtractionResult":
        return cls(
            processor_used=processor,
            status="empty",
            warnings=[reason],
        )

    @classmethod
    def error(cls, processor: str, error: str) -> "ExtractionResult":
        return cls(
            processor_used=processor,
            status="error",
            error_message=error,
        )
