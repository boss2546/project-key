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


# ─── TEXT POST-PROCESSING (LLM-powered) ───

async def cleanup_extracted_text(text: str, filename: str) -> str:
    """Use LLM to clean up broken PDF text extraction.
    
    PDF extractors often produce broken Thai text with:
    - Character spacing: ผ ่า น เ ข ้า ร อ บ
    - Private Use chars: \\uf70a instead of ่
    - Spaced Latin: S u b s c r i p t i o n
    
    LLM understands language context and fixes everything in one pass.
    """
    from .llm import call_llm
    
    if not text or len(text) < 50:
        return text
    
    # Check if text needs cleanup
    space_ratio = text.count(' ') / max(len(text), 1)
    has_private_use = any(0xF700 <= ord(c) <= 0xF7FF for c in text[:1000])
    
    if space_ratio < 0.25 and not has_private_use:
        logger.info(f"Text looks clean (space ratio {space_ratio:.1%}), skipping LLM cleanup")
        return text
    
    logger.info(f"LLM cleanup: {filename} ({len(text)} chars, space ratio {space_ratio:.1%})")
    
    # Process in chunks if text is very long
    max_chunk = 6000
    if len(text) > max_chunk:
        chunks = []
        for i in range(0, len(text), max_chunk):
            chunk = text[i:i + max_chunk]
            cleaned = await _llm_fix_chunk(chunk, filename)
            chunks.append(cleaned)
        result = "\n".join(chunks)
    else:
        result = await _llm_fix_chunk(text, filename)
    
    logger.info(f"LLM cleanup done: {len(text)} → {len(result)} chars")
    return result


async def _llm_fix_chunk(text: str, filename: str) -> str:
    """Send a chunk of broken text to LLM for cleanup."""
    from .llm import call_llm
    
    system_prompt = """คุณเป็นผู้เชี่ยวชาญในการแก้ไขข้อความที่ extract จาก PDF

กฎ:
1. แก้ไขข้อความที่ตัวอักษรถูกเว้นวรรคผิด เช่น "ผ ่า น เ ข ้า" → "ผ่านเข้า"
2. แก้ไขตัวอักษร Unicode Private Use Area (\\uf70a, \\uf70b ฯลฯ) ให้เป็นสระ/วรรณยุกต์ไทยที่ถูกต้อง
3. แก้ไขตัวอักษรภาษาอังกฤษที่ถูกเว้น เช่น "S u b s c r i p t i o n" → "Subscription"  
4. รักษาเนื้อหาและความหมายเดิมทั้งหมด ห้ามเพิ่ม/ลบ/แต่งเนื้อหา
5. รักษา line breaks และ formatting เดิม (เช่น --- Page 1 ---)
6. ถ้าข้อความปกติอยู่แล้ว ให้คืนตามเดิม
7. ตอบเฉพาะข้อความที่แก้ไขแล้วเท่านั้น ไม่ต้องมีคำอธิบาย"""

    user_prompt = f"แก้ไขข้อความที่ extract จาก {filename}:\n\n{text}"
    
    try:
        result = await call_llm(system_prompt, user_prompt, temperature=0.1, max_tokens=16384)
        return result.strip()
    except Exception as e:
        logger.error(f"LLM cleanup failed for {filename}: {e}")
        return text


def _postprocess_thai(text: str) -> str:
    """Legacy sync wrapper — basic regex cleanup only.
    For full cleanup, use async cleanup_extracted_text() instead.
    """
    if not text:
        return text
    # Basic: just remove spaces before Thai combining characters
    combining = re.compile(r'(\S) ([\u0E31\u0E34-\u0E3A\u0E47-\u0E4E])')
    prev = None
    result = text
    while prev != result:
        prev = result
        result = combining.sub(r'\1\2', result)
    # Collapse spaced Latin
    def fix_latin(m):
        return m.group(0).replace(' ', '')
    result = re.compile(r'(?:[A-Za-z0-9] ){3,}[A-Za-z0-9]').sub(fix_latin, result)
    result = re.sub(r'[^\S\n]{2,}', ' ', result)
    return result

