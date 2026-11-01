"""Text-only, explicitly selected document ingestion. Never executes imported content."""
from __future__ import annotations

import csv
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile, BadZipFile

MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_TEXT_CHARS = 120_000
MAX_CHUNKS = 100
SUPPORTED = {".txt", ".md", ".csv", ".json", ".pdf", ".docx"}


def extract(path: str | Path) -> str:
    file = Path(path).expanduser()
    if file.suffix.lower() not in SUPPORTED:
        raise ValueError("Unsupported format. Choose TXT, MD, CSV, JSON, PDF or DOCX")
    if not file.is_file() or file.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("File missing or larger than 8 MB")
    if file.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(str(file), strict=True)
        if len(reader.pages) > 100:
            raise ValueError("PDF has over 100 pages")
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
            if sum(map(len, parts)) > MAX_TEXT_CHARS:
                raise ValueError("Document exceeds 120,000 extracted characters")
        text = "\n".join(parts)
    elif file.suffix.lower() == ".docx":
        try:
            with ZipFile(file) as z:
                info = z.getinfo("word/document.xml")
                if info.file_size > 4_000_000:
                    raise ValueError("DOCX expanded document too large")
                root = ET.fromstring(z.read(info))
                ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
                text = "\n".join(" ".join(t.text or "" for t in p.iter(ns + "t")) for p in root.iter(ns + "p"))
        except (BadZipFile, KeyError) as e:
            raise ValueError("Invalid DOCX file") from e
    else:
        text = file.read_text(encoding="utf-8-sig", errors="replace")
    if not text.strip():
        raise ValueError("No extractable text (image-only PDFs need OCR, not included)")
    if len(text) > MAX_TEXT_CHARS:
        raise ValueError("Document exceeds 120,000 extracted characters")
    return text


def chunks(text: str, max_chars: int = 1200, overlap: int = 160) -> list[str]:
    if max_chars <= overlap or overlap < 0:
        raise ValueError("Invalid chunk settings")
    text = re.sub(r"\r\n?", "\n", text).strip()
    result = []
    start = 0
    while start < len(text):
        result.append(text[start:start + max_chars])
        if len(result) > MAX_CHUNKS:
            raise ValueError("Document has too many memory chunks")
        if start + max_chars >= len(text):
            break
        start += max_chars - overlap
    return result
