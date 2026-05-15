"""Ingestion processors — v10.0.0.

Sub-modules:
  - routing: file-type -> processor decision (Decision dataclass + feature flags)
  - safety:  threading lock, retry-with-backoff, lazy semaphore
  - llamaparse: PDF parsing via LlamaParse cloud (opt-in via env)
  - schema: ExtractionResult Pydantic model

Imported lazily -- no side effects on import.
"""
