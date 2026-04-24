"""
Text extraction — v5.2.

Pipeline:
1. Docling (IBM) for structured document understanding (if available)
2. PyPDF2 basic text extraction for PDF
3. pytesseract OCR fallback for image-only PDFs (if available)
4. Thai text post-processing to fix spacing issues

Reference: https://github.com/DS4SD/docling
"""
import os
import re
import logging

logger = logging.getLogger(__name__)

# ─── Feature detection ───
_HAS_DOCLING = False
try:
    from docling.document_converter import DocumentConverter
    _HAS_DOCLING = True
    logger.info("Docling available — using advanced document understanding")
except ImportError:
    logger.warning("Docling not available — falling back to basic extraction")

_HAS_OCR = False
try:
    import pytesseract
    from pdf2image import convert_from_path
    _HAS_OCR = True
    logger.info("OCR available (pytesseract + pdf2image)")
except ImportError:
    logger.warning("OCR not available — PDF image extraction disabled")


def extract_text(filepath: str, filetype: str) -> str:
    """
    Extract text from a file.
    Uses Docling for PDF/DOCX (structured Markdown output).
    Falls back to basic extraction + OCR if needed.
    """
    try:
        if filetype in ("pdf", "docx") and _HAS_DOCLING:
            text = _extract_with_docling(filepath)
            if text and not text.startswith("["):
                return _postprocess_thai(text) if filetype == "pdf" else text
            # Docling returned nothing, try fallback
            if filetype == "pdf":
                return _extract_pdf_with_fallbacks(filepath)
            return text
        elif filetype == "pdf":
            return _extract_pdf_with_fallbacks(filepath)
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
                return _extract_pdf_with_fallbacks(filepath)
            elif filetype == "docx":
                return _extract_docx_basic(filepath)
        except:
            pass
        return f"[Extraction error: {str(e)}]"


def _extract_pdf_with_fallbacks(filepath: str) -> str:
    """PDF extraction with full fallback chain: PyPDF2 → OCR."""
    # Step 1: Try PyPDF2 text extraction
    text = _extract_pdf_basic(filepath)
    
    if text and not text.startswith("[No text"):
        return _postprocess_thai(text)
    
    # Step 2: Try OCR if text extraction failed
    if _HAS_OCR:
        logger.info(f"PyPDF2 found no text — trying OCR for {os.path.basename(filepath)}")
        ocr_text = _extract_pdf_ocr(filepath)
        if ocr_text and not ocr_text.startswith("["):
            return _postprocess_thai(ocr_text)
    
    return "[No text content found in PDF — file may be image-only and OCR is not available]"


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


def _extract_pdf_ocr(filepath: str) -> str:
    """OCR extraction using pytesseract for image-only PDFs."""
    try:
        images = convert_from_path(filepath, dpi=200, first_page=1, last_page=20)
        pages = []
        for i, img in enumerate(images):
            # Use Thai + English language for OCR
            text = pytesseract.image_to_string(img, lang='tha+eng')
            if text and text.strip():
                pages.append(f"--- Page {i+1} (OCR) ---\n{text.strip()}")
        
        if pages:
            logger.info(f"OCR: extracted {sum(len(p) for p in pages)} chars from {os.path.basename(filepath)}")
            return "\n\n".join(pages)
        
        return "[OCR found no text in PDF images]"
    except Exception as e:
        logger.error(f"OCR failed for {filepath}: {e}")
        return f"[OCR error: {str(e)}]"


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


# ─── THAI TEXT POST-PROCESSING ───

def _postprocess_thai(text: str) -> str:
    """Fix common Thai text spacing issues from PDF extraction.
    
    PDFs (especially from Canva, Figma, Illustrator, Word) often export
    Thai text with broken character spacing:
        ผ ่า น เ ข ้า ร อ บ  →  ผ่านเข้ารอบ
        S u b s c r i p t i o n  →  Subscription
    
    Strategy:
    1. Remove ALL spaces before Thai combining characters (vowels above/below, tone marks)
    2. Remove spaces between Thai consonants/vowels when in a Thai text block
    3. Collapse single-char-spaced English words too
    """
    if not text:
        return text
    
    original = text
    result = text
    
    # ── Step 1: ALWAYS remove spaces before Thai combining characters ──
    # These characters MUST attach to the preceding consonant — a space before
    # them is ALWAYS wrong. This includes:
    #   \u0E31 (sara am shortener - mai han akat)
    #   \u0E34-\u0E3A (sara i, sara ii, sara ue, sara uee, sara u, sara uu, phinthu)
    #   \u0E47-\u0E4E (maitaikhu, mai ek, mai tho, mai tri, mai chattawa, thanthakhat, nikhahit, yamakkan)
    #   \u0E32-\u0E33 (sara aa, sara am) — when preceded by Thai consonant + space
    combining_pattern = re.compile(r'(\S) ([\u0E31\u0E34-\u0E3A\u0E47-\u0E4E])')
    prev = None
    while prev != result:
        prev = result
        result = combining_pattern.sub(r'\1\2', result)
    
    # Sara aa (า) and sara am (ำ) after Thai consonant
    result = re.sub(r'([\u0E01-\u0E2E]) ([\u0E32\u0E33])', r'\1\2', result)
    
    # ── Step 2: Remove spaces between Thai characters in text blocks ──
    # Thai consonant range: \u0E01-\u0E2E
    # Thai vowels (non-combining): \u0E30, \u0E32, \u0E33, \u0E40-\u0E46
    thai_all = r'[\u0E01-\u0E4E]'
    
    # Pattern: any Thai char + single space + any Thai char
    thai_space = re.compile(f'({thai_all}) ({thai_all})')
    
    # Count if this text has significant Thai spacing issues
    matches = thai_space.findall(result)
    if len(matches) > 3:
        logger.info(f"Thai post-processing: fixing {len(matches)} spacing issues")
        prev = None
        while prev != result:
            prev = result
            result = thai_space.sub(r'\1\2', result)
    
    # ── Step 3: Fix spaced-out English/Latin characters ──
    # Pattern like: S u b s c r i p t i o n → Subscription
    # Detect: single letter + space + single letter, repeated 3+ times
    def fix_spaced_latin(match):
        return match.group(0).replace(' ', '')
    
    spaced_latin = re.compile(r'(?:[A-Za-z0-9] ){3,}[A-Za-z0-9]')
    result = spaced_latin.sub(fix_spaced_latin, result)
    
    # ── Step 4: Clean up excessive whitespace ──
    # Multiple spaces → single space (but preserve newlines)
    result = re.sub(r'[^\S\n]{2,}', ' ', result)
    
    if result != original:
        diff = len(original) - len(result)
        logger.info(f"Thai post-processing: removed {diff} extra characters ({diff*100//len(original)}% reduction)")
    
    return result

