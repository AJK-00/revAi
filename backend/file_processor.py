"""
file_processor.py
-----------------
Parses uploaded files into clean text chunks.

Parser strategy:
  PDF  → pdfplumber (text-based) → pytesseract OCR fallback (scanned/image)
  PPTX → python-pptx
  DOCX → python-docx
  XLSX → openpyxl
  TXT/MD/CSV → built-in

OCR requires:
  pip install pytesseract pdf2image Pillow
  + Tesseract installed at: C:/Program Files/Tesseract-OCR/tesseract.exe
  + Poppler bin/ folder added to PATH (for pdf2image)
"""

import os
import pytesseract
from pathlib import Path
import magic  # pip install python-magic-bin

# ── Hardcoded paths — bypasses PATH issues entirely ──
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
os.environ["TESSDATA_PREFIX"] = r"C:\Program Files\tessdata"
os.environ["PATH"] += r";C:\Program Files\Tesseract-OCR;C:\Program Files\poppler-25.12.0\Library\bin"
UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

SUPPORTED = {".pdf", ".pptx", ".ppt", ".docx", ".doc", ".txt", ".csv", ".md", ".xlsx"}
CHUNK_SIZE = 1000   # characters per chunk
OVERLAP    = 100    # overlap between chunks

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB hard limit

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain", "text/csv", "text/markdown",
}

def validate_file(file_bytes: bytes, filename: str):
    # 1. Size check
    if len(file_bytes) > MAX_FILE_SIZE:
        raise ValueError(f"File too large. Max 20 MB.")
    
    # 2. MIME type check — read actual bytes, don't trust the extension
    detected = magic.from_buffer(file_bytes, mime=True)
    if detected not in ALLOWED_MIME_TYPES:
        raise ValueError(f"Blocked file type: {detected}")
    
    # 3. Filename sanitization — prevent path traversal
    safe_name = os.path.basename(filename)
    safe_name = "".join(c for c in safe_name if c.isalnum() or c in "._- ")
    if not safe_name:
        raise ValueError("Invalid filename.")
    
    return safe_name


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

def save_upload(file_bytes: bytes, filename: str) -> str:
    """Save uploaded bytes to disk. Returns the saved file path."""
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED:
        raise ValueError(
            f"Unsupported file type '{ext}'. Supported: {sorted(SUPPORTED)}"
        )
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(file_bytes)
    print(f"[file_processor] Saved: {path}")
    return path


def extract_text_chunks(file_path: str) -> list:
    """
    Parse a file and return a list of non-empty text chunk strings.
    Automatically picks the right parser by file extension.
    """
    ext = Path(file_path).suffix.lower()
    print(f"[file_processor] Parsing '{Path(file_path).name}' (ext={ext})")

    if ext == ".pdf":
        raw = _parse_pdf(file_path)
    elif ext in (".pptx", ".ppt"):
        raw = _parse_pptx(file_path)
    elif ext in (".docx", ".doc"):
        raw = _parse_docx(file_path)
    elif ext == ".xlsx":
        raw = _parse_xlsx(file_path)
    elif ext in (".txt", ".md", ".csv"):
        raw = _parse_text(file_path)
    else:
        raise ValueError(f"No parser available for extension: {ext}")

    chunks = _split_into_chunks(raw, CHUNK_SIZE, OVERLAP)
    print(f"[file_processor] Done — {len(chunks)} chunks extracted.")
    return chunks


# ─────────────────────────────────────────────
# PDF parser — text first, OCR fallback
# ─────────────────────────────────────────────

def _parse_pdf(path: str) -> str:
    """
    1. Try pdfplumber to extract selectable text (fast, accurate).
    2. If no text found (scanned/image PDF), fall back to OCR via
       pdf2image + pytesseract (slower but works on any PDF).
    """
    import pdfplumber

    pages_text = []

    # ── Pass 1: pdfplumber ──────────────────────
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text and text.strip():
                pages_text.append(f"[Page {i+1}]\n{text.strip()}")

    if pages_text:
        print(f"[file_processor] PDF: extracted text from {len(pages_text)} pages via pdfplumber.")
        return "\n\n".join(pages_text)

    # ── Pass 2: OCR fallback ────────────────────
    print("[file_processor] PDF has no selectable text — running OCR (this may take a moment)…")
    return _ocr_pdf(path)


def _ocr_pdf(path: str) -> str:
    """Convert each PDF page to an image and run Tesseract OCR on it."""
    try:
        from pdf2image import convert_from_path
    except ImportError:
        raise ImportError(
            "pdf2image is required for scanned PDFs. "
            "Run: pip install pdf2image\n"
            "Also ensure Poppler bin/ is in your system PATH."
        )

    from PIL import Image

    # convert_from_path needs Poppler on PATH
    images = convert_from_path(path, dpi=200)
    print(f"[file_processor] OCR: converted PDF to {len(images)} page image(s).")

    ocr_pages = []
    for i, img in enumerate(images):
        # pytesseract reads the PIL image directly
        text = pytesseract.image_to_string(img, lang="eng")
        text = text.strip()
        if text:
            ocr_pages.append(f"[Page {i+1} — OCR]\n{text}")
        print(f"[file_processor] OCR page {i+1}/{len(images)} done.")

    if not ocr_pages:
        raise ValueError(
            "OCR produced no text. The PDF may be corrupted or contain only non-text graphics."
        )

    return "\n\n".join(ocr_pages)


# ─────────────────────────────────────────────
# Other parsers
# ─────────────────────────────────────────────

def _parse_pptx(path: str) -> str:
    from pptx import Presentation
    prs = Presentation(path)
    slides = []
    for i, slide in enumerate(prs.slides, 1):
        texts = [
            shape.text.strip()
            for shape in slide.shapes
            if hasattr(shape, "text") and shape.text.strip()
        ]
        if texts:
            slides.append(f"[Slide {i}]\n" + "\n".join(texts))
    if not slides:
        raise ValueError("No text found in PowerPoint file.")
    return "\n\n".join(slides)


def _parse_docx(path: str) -> str:
    from docx import Document
    doc = Document(path)
    parts = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(
                cell.text.strip() for cell in row.cells if cell.text.strip()
            )
            if row_text:
                parts.append(row_text)
    if not parts:
        raise ValueError("No text found in Word document.")
    return "\n\n".join(parts)


def _parse_xlsx(path: str) -> str:
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)
    rows = []
    for sheet in wb.worksheets:
        rows.append(f"[Sheet: {sheet.title}]")
        for row in sheet.iter_rows(values_only=True):
            row_text = " | ".join(str(c) for c in row if c is not None)
            if row_text.strip():
                rows.append(row_text)
    if not rows:
        raise ValueError("No data found in Excel file.")
    return "\n".join(rows)


def _parse_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    if not text.strip():
        raise ValueError("File appears to be empty.")
    return text


# ─────────────────────────────────────────────
# Chunker
# ─────────────────────────────────────────────

def _split_into_chunks(text: str, size: int, overlap: int) -> list:
    """
    Split text into chunks of `size` chars with `overlap` char overlap
    so that context at chunk boundaries is not lost.
    """
    chunks = []
    start = 0
    while start < len(text):
        chunk = text[start : start + size].strip()
        if chunk:
            chunks.append(chunk)
        start += size - overlap
    return chunks