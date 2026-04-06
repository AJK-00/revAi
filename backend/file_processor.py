"""
file_processor.py
-----------------
Parses uploaded files into clean text chunks.
Linux-compatible — no python-magic, no Windows paths.

Parsers:
  PDF  → pdfplumber (text) → pytesseract OCR (scanned PDF fallback)
  PPTX → python-pptx
  DOCX → python-docx
  XLSX → openpyxl
  TXT/MD/CSV → built-in read
"""

import os
import sys
from pathlib import Path

UPLOAD_DIR = "/tmp/revai_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

SUPPORTED  = {".pdf", ".pptx", ".ppt", ".docx", ".doc", ".txt", ".csv", ".md", ".xlsx"}
CHUNK_SIZE = 1000
OVERLAP    = 100


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

def save_upload(file_bytes: bytes, filename: str) -> str:
    """Save uploaded bytes to disk. Returns the saved path."""
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED:
        raise ValueError(f"Unsupported file type '{ext}'. Supported: {sorted(SUPPORTED)}")
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(file_bytes)
    print(f"[file_processor] Saved: {path}")
    return path


def extract_text_chunks(file_path: str) -> list:
    """Parse a file and return a list of text chunk strings."""
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
        raise ValueError(f"No parser for extension: {ext}")

    chunks = _split_into_chunks(raw, CHUNK_SIZE, OVERLAP)
    print(f"[file_processor] Done — {len(chunks)} chunks.")
    return chunks


# ─────────────────────────────────────────────
# PDF — text-first, OCR fallback
# ─────────────────────────────────────────────

def _parse_pdf(path: str) -> str:
    import pdfplumber

    pages_text = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text and text.strip():
                pages_text.append(f"[Page {i+1}]\n{text.strip()}")

    if pages_text:
        print(f"[file_processor] PDF: {len(pages_text)} pages via pdfplumber.")
        return "\n\n".join(pages_text)

    # Scanned PDF — try OCR
    print("[file_processor] No selectable text — attempting OCR...")
    return _ocr_pdf(path)


def _ocr_pdf(path: str) -> str:
    """OCR fallback for scanned PDFs using pdf2image + pytesseract."""
    try:
        import pytesseract
        from pdf2image import convert_from_path
        from PIL import Image  # noqa
    except ImportError as e:
        raise ImportError(f"OCR dependencies missing: {e}") from e

    # On Railway/Linux, tesseract is at /usr/bin/tesseract (installed via nixpacks)
    # No path override needed — pytesseract finds it automatically on Linux
    images = convert_from_path(path, dpi=200)
    print(f"[file_processor] OCR: {len(images)} page(s).")

    ocr_pages = []
    for i, img in enumerate(images):
        text = pytesseract.image_to_string(img, lang="eng").strip()
        if text:
            ocr_pages.append(f"[Page {i+1} — OCR]\n{text}")

    if not ocr_pages:
        raise ValueError("OCR produced no text. PDF may be image-only or corrupted.")

    return "\n\n".join(ocr_pages)


# ─────────────────────────────────────────────
# Other parsers
# ─────────────────────────────────────────────

def _parse_pptx(path: str) -> str:
    from pptx import Presentation
    prs    = Presentation(path)
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
    doc   = Document(path)
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
    wb   = openpyxl.load_workbook(path, data_only=True)
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
    chunks = []
    start  = 0
    while start < len(text):
        chunk = text[start : start + size].strip()
        if chunk:
            chunks.append(chunk)
        start += size - overlap
    return chunks