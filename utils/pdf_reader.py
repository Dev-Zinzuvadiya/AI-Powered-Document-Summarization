"""PDF text extraction with upload and document-size limits."""

from __future__ import annotations

from io import BytesIO
from typing import Any

from pypdf import PdfReader
from utils.helpers import save_uploaded_text

MAX_PDF_PAGES = 2000


def read_pdf(upload: Any) -> str:
    """Extract readbable text from an uploaded PDF."""
    raw = save_uploaded_text(upload)

    try:
        reader = PdfReader(BytesIO(raw))

        if reader.is_encrypted:
            raise ValueError("This PDF is password-protected and cannot be read.")

        if len(reader.pages) > MAX_PDF_PAGES:
            raise ValueError(f"PDF has more than {MAX_PDF_PAGES} pages.")

        text = "\n\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Could not read this PDF: {exc}") from exc

    if not text:
        raise ValueError(
            "No selectable text as found in the PDF. Scabbed PDFs beed OCR."
        )

    return text
