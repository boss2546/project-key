"""
Text extraction using Docling (IBM) for structured document understanding.
Fallback to basic extraction if Docling fails.

Reference: https://github.com/DS4SD/docling
- Understands document layout, headings, tables, lists
- Exports to structured Markdown preserving document hierarchy
"""
import os
import logging

logger = logging.getLogger(__name__)

# Try importing Docling
_HAS_DOCLING = False
try:
    from docling.document_converter import DocumentConverter
    _HAS_DOCLING = True
    logger.info("Docling available — using advanced document understanding")
except ImportError:
    logger.warning("Docling not available — falling back to basic extraction")


def extract_text(filepath: str, filetype: str) -> str:
    """
    Extract text from a file.
    Uses Docling for PDF/DOCX (structured Markdown output).
    Falls back to basic extraction if Docling unavailable.
    """
    try:
        if filetype in ("pdf", "docx") and _HAS_DOCLING:
            return _extract_with_docling(filepath)
        elif filetype == "pdf":
            return _extract_pdf_basic(filepath)
        elif filetype == "docx":
            return _extract_docx_basic(filepath)
        elif filetype in ("txt", "md"):
            return _extract_txt(filepath)
        else:
            return f"[Unsupported file type: {filetype}]"
    except Exception as e:
        logger.error(f"Extraction failed for {filepath}: {e}")
        # Try fallback
        try:
            if filetype == "pdf":
                return _extract_pdf_basic(filepath)
            elif filetype == "docx":
                return _extract_docx_basic(filepath)
        except:
            pass
        return f"[Extraction error: {str(e)}]"


def _extract_with_docling(filepath: str) -> str:
    """
    Extract text using Docling — produces structured Markdown.
    Preserves headings, tables, lists, and document hierarchy.
    """
    logger.info(f"Docling: processing {os.path.basename(filepath)}")
    converter = DocumentConverter()
    result = converter.convert(filepath)

    # Export to Markdown (preserves structure)
    md_text = result.document.export_to_markdown()

    if md_text and md_text.strip():
        logger.info(f"Docling: extracted {len(md_text)} chars from {os.path.basename(filepath)}")
        return md_text.strip()

    return "[No text content found]"


# ─── FALLBACK EXTRACTORS ───

def _extract_pdf_basic(filepath: str) -> str:
    """Fallback PDF extraction using PyPDF2."""
    from PyPDF2 import PdfReader
    reader = PdfReader(filepath)
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text and text.strip():
            pages.append(f"--- Page {i+1} ---\n{text.strip()}")
    return "\n\n".join(pages) if pages else "[No text content found in PDF]"


def _extract_docx_basic(filepath: str) -> str:
    """Fallback DOCX extraction using python-docx."""
    from docx import Document
    doc = Document(filepath)
    paragraphs = []
    for para in doc.paragraphs:
        if para.text.strip():
            # Preserve heading structure
            if para.style.name.startswith('Heading'):
                level = para.style.name.replace('Heading ', '').strip()
                try:
                    hashes = '#' * int(level)
                except ValueError:
                    hashes = '##'
                paragraphs.append(f"{hashes} {para.text.strip()}")
            else:
                paragraphs.append(para.text.strip())
    # Extract tables as markdown
    for table in doc.tables:
        rows = []
        for i, row in enumerate(table.rows):
            cells = [cell.text.strip() for cell in row.cells]
            rows.append("| " + " | ".join(cells) + " |")
            if i == 0:
                rows.append("| " + " | ".join(["---"] * len(cells)) + " |")
        if rows:
            paragraphs.append("\n".join(rows))
    return "\n\n".join(paragraphs) if paragraphs else "[No text content found in DOCX]"


def _extract_txt(filepath: str) -> str:
    """Extract text from TXT/MD files with encoding fallback."""
    encodings = ['utf-8', 'utf-8-sig', 'cp874', 'tis-620', 'latin-1']
    for enc in encodings:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                text = f.read()
            return text.strip() if text.strip() else "[Empty file]"
        except (UnicodeDecodeError, UnicodeError):
            continue
    return "[Could not decode file]"
