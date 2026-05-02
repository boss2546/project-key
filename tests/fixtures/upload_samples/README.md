# Upload Samples — Test Fixtures (v7.5.0)

Generated test files for upload-resilience tests.

## Regenerate
```bash
python tests/fixtures/upload_samples/generate_fixtures.py
```

## Files
- `sample.png` — PNG with Thai+EN text (OCR test)
- `sample_blank.png` — blank PNG (no text → ocr_failed)
- `sample_xss.png` — PNG with "alert(1)" text (XSS-via-OCR sanity)
- `sample.pdf` — minimal PDF for basic upload test
- `empty.pdf` — 0-byte (EMPTY_FILE skip code)
- `big_text.txt` (or .pdf if reportlab installed) — 150K chars with `UNIQUE_MARKER_NNN` per page (chunker test)
- `sample.xlsx` — 3 sheets + formula (Phase 3)
- `sample.pptx` — 2 slides + speaker notes (Phase 3)
- `sample_safe.html` — clean HTML
- `sample_xss.html` — `<script>` + `<style>` (security strip test)
- `sample.json` — nested structure
- `sample.rtf` — basic rich text
- `sample.xyz` — unsupported extension
- `empty.txt` — 0-byte text

## Why .gitignore
Binary files (PNG, XLSX, PPTX, PDF) are not committed — regenerate before tests.
