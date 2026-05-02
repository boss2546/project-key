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
    """Extract text from a file.

    Supported (v7.5.0):
      - pdf, docx (Docling structured + PyPDF2/python-docx fallbacks)
      - txt, md (encoding-tolerant)
      - png, jpg, jpeg, webp (Tesseract OCR — Thai+English)
      - csv (treated as txt)

    Returns extracted text. Error markers are wrapped in `[brackets]` so
    downstream `compute_content_hash()` skips hashing them (avoids
    false-positive matches between failed extractions).
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
        elif filetype in ("txt", "md", "csv"):
            return _extract_txt(filepath)
        elif filetype in ("png", "jpg", "jpeg", "webp"):
            return _extract_image_ocr(filepath)
        elif filetype == "xlsx":
            return _extract_xlsx(filepath)
        elif filetype == "pptx":
            return _extract_pptx(filepath)
        elif filetype == "html":
            return _extract_html(filepath)
        elif filetype == "json":
            return _extract_json(filepath)
        elif filetype == "rtf":
            return _extract_rtf(filepath)
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
            elif filetype in ("png", "jpg", "jpeg", "webp"):
                return _extract_image_ocr(filepath)
        except Exception:
            pass
        return f"[Extraction error: {str(e)}]"


def _extract_image_ocr(filepath: str) -> str:
    """OCR text from png/jpg/jpeg/webp via pytesseract (Thai + English).

    v7.5.0: รองรับ image upload จริง (ก่อนหน้านี้ png/jpg ถูกตั้งใน allowed_types
    แต่ extraction.py reject กลับเป็น "[Unsupported file type]" → orphan ใน DB)

    Returns:
      - Extracted text (post-processed for Thai) ถ้าเจอ
      - "[Image: no text detected]" ถ้า OCR สำเร็จแต่ไม่มี text
      - "[Image: OCR not available]" ถ้า pytesseract / tesseract binary หาย
      - "[OCR error: ...]" ถ้า exception อื่น
    """
    if not _HAS_OCR:
        return "[Image: OCR not available]"
    try:
        from PIL import Image
        img = Image.open(filepath)
        # Convert mode if needed (RGBA / palette → RGB for tesseract)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        text = pytesseract.image_to_string(img, lang="tha+eng")
        if text and text.strip():
            logger.info(f"Image OCR: extracted {len(text)} chars from {os.path.basename(filepath)}")
            return _postprocess_thai(text.strip())
        return "[Image: no text detected]"
    except Exception as e:
        logger.error(f"Image OCR failed for {filepath}: {e}")
        return f"[OCR error: {str(e)}]"


def _extract_pdf_with_fallbacks(filepath: str) -> str:
    """PDF extraction with full fallback chain: encrypted check → PyPDF2 → OCR.

    v7.5.0: detects encrypted PDF early so caller can flag extraction_status.
    """
    # v7.5.0 — short-circuit for encrypted PDFs (specific marker for downstream)
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(filepath)
        if reader.is_encrypted:
            logger.info(f"PDF encrypted: {os.path.basename(filepath)}")
            return "[PDF encrypted: password-protected — unlock before re-uploading]"
    except Exception:
        # If we can't even open the file, fall through to normal error handling
        pass

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


def classify_extraction_status(text: str) -> str:
    """v7.5.0 — derive extraction_status from extracted_text content.

    Maps the [bracket-marker] convention used by extract_text() back into the
    short status enum stored in the DB. Single source of truth for status
    classification — used by upload, reprocess, and migration paths.

    Returns one of: ok | empty | encrypted | ocr_failed | unsupported
    """
    if not text or not text.strip():
        return "empty"
    if not text.startswith("["):
        return "ok"
    lower = text.lower()
    if "encrypted" in lower or "password-protected" in lower:
        return "encrypted"
    if "no text detected" in lower or "no text content" in lower or "ocr found no text" in lower:
        return "ocr_failed"
    if "unsupported file type" in lower:
        return "unsupported"
    if "ocr error" in lower or "extraction error" in lower:
        return "ocr_failed"
    return "ok"  # safe default — unknown bracket marker shouldn't block


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
    from .llm import call_llm_pro
    
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
    from .llm import call_llm_pro
    
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
        result = await call_llm_pro(system_prompt, user_prompt, temperature=0.1, max_tokens=16384)
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



# ─── v7.5.0 — Phase 3: more format extractors ────────────────────────


def _extract_xlsx(filepath: str) -> str:
    """Extract text from xlsx (Excel) — flatten all sheets to markdown tables.

    Multi-sheet decision (Q): flatten ทุก sheet เป็นไฟล์เดียว (per user choice).
    Uses data_only=True so formulas resolve to cached values (not formula text).
    read_only=True for memory efficiency on big workbooks.
    """
    try:
        from openpyxl import load_workbook
    except ImportError:
        return "[xlsx extractor unavailable: install openpyxl]"
    try:
        wb = load_workbook(filepath, data_only=True, read_only=True)
        sections = []
        for sheet in wb.worksheets:
            sections.append(f"## Sheet: {sheet.title}")
            rows_md = []
            for row in sheet.iter_rows(values_only=True):
                cells = [str(c) if c is not None else "" for c in row]
                if any(c.strip() for c in cells):
                    rows_md.append("| " + " | ".join(cells) + " |")
            if rows_md:
                sections.append("\n".join(rows_md))
            else:
                sections.append("_(empty sheet)_")
        return "\n\n".join(sections) if sections else "[Empty workbook]"
    except Exception as e:
        logger.error(f"xlsx extraction failed for {filepath}: {e}")
        return f"[Extraction error: {str(e)}]"


def _extract_pptx(filepath: str) -> str:
    """Extract text + speaker notes from pptx (PowerPoint).

    Each slide → "## Slide N: <title>" section with body bullets + notes.
    """
    try:
        from pptx import Presentation
    except ImportError:
        return "[pptx extractor unavailable: install python-pptx]"
    try:
        prs = Presentation(filepath)
        sections = []
        for i, slide in enumerate(prs.slides, start=1):
            # Title
            title = ""
            try:
                if slide.shapes.title and slide.shapes.title.text:
                    title = slide.shapes.title.text.strip()
            except Exception:
                pass
            sections.append(f"## Slide {i}" + (f": {title}" if title else ""))
            # Body text (skip title shape — already captured)
            body_lines = []
            for shape in slide.shapes:
                if not shape.has_text_frame:
                    continue
                if hasattr(slide.shapes, "title") and shape == slide.shapes.title:
                    continue
                for para in shape.text_frame.paragraphs:
                    line = para.text.strip()
                    if line:
                        body_lines.append(f"- {line}")
            if body_lines:
                sections.append("\n".join(body_lines))
            # Speaker notes
            try:
                if slide.has_notes_slide:
                    notes = slide.notes_slide.notes_text_frame.text.strip()
                    if notes:
                        sections.append(f"**Notes:** {notes}")
            except Exception:
                pass
        return "\n\n".join(sections) if sections else "[Empty presentation]"
    except Exception as e:
        logger.error(f"pptx extraction failed for {filepath}: {e}")
        return f"[Extraction error: {str(e)}]"


def _extract_html(filepath: str) -> str:
    """Extract plain text from HTML — STRIPS <script> and <style> tags.

    Security: HTML may contain <script>alert(1)</script> XSS payloads. Even
    though we don't render the output to a browser, we DO send it to LLM
    summary + vector index, so injected text could pollute downstream context.
    BeautifulSoup .decompose() removes the entire tag tree.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return "[html extractor unavailable: install beautifulsoup4]"
    try:
        # Try common encodings
        content = None
        for enc in ("utf-8", "utf-8-sig", "cp874", "tis-620", "latin-1"):
            try:
                with open(filepath, "r", encoding=enc) as f:
                    content = f.read()
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        if content is None:
            return "[Could not decode HTML file]"
        soup = BeautifulSoup(content, "html.parser")
        # Security: remove script/style/iframe (XSS + side-channel)
        for tag in soup(["script", "style", "iframe", "object", "embed", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        # Collapse excessive whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text if text.strip() else "[HTML had no extractable text]"
    except Exception as e:
        logger.error(f"html extraction failed for {filepath}: {e}")
        return f"[Extraction error: {str(e)}]"


def _extract_json(filepath: str) -> str:
    """Pretty-print JSON for readable extracted_text.

    Falls back to raw text if JSON malformed (some "JSON" files are JSON5
    or have trailing commas — still useful as text input).
    """
    try:
        import json as _json
        for enc in ("utf-8", "utf-8-sig"):
            try:
                with open(filepath, "r", encoding=enc) as f:
                    raw = f.read()
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        else:
            return "[Could not decode JSON file]"
        try:
            data = _json.loads(raw)
            return _json.dumps(data, indent=2, ensure_ascii=False)
        except _json.JSONDecodeError:
            # Malformed JSON — return raw text (still useful)
            return raw if raw.strip() else "[Empty JSON file]"
    except Exception as e:
        logger.error(f"json extraction failed for {filepath}: {e}")
        return f"[Extraction error: {str(e)}]"


def _extract_rtf(filepath: str) -> str:
    """Strip RTF control codes → plain text via striprtf."""
    try:
        from striprtf.striprtf import rtf_to_text
    except ImportError:
        return "[rtf extractor unavailable: install striprtf]"
    try:
        for enc in ("utf-8", "latin-1", "cp1252"):
            try:
                with open(filepath, "r", encoding=enc) as f:
                    content = f.read()
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        else:
            return "[Could not decode RTF file]"
        text = rtf_to_text(content, errors="ignore")
        return text.strip() if text.strip() else "[RTF had no extractable text]"
    except Exception as e:
        logger.error(f"rtf extraction failed for {filepath}: {e}")
        return f"[Extraction error: {str(e)}]"
