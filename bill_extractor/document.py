"""Document loading, text extraction, OCR fallback, and bill segmentation."""

import re
from io import BytesIO

import fitz

from bill_extractor.models import DocumentPage
from bill_extractor.ocr import extract_page_text


BILL_START = re.compile(
    r"HT\s+BILL\s+FOR\s+THE\s+MONTH|YOUR\s+DETAILS[\s\S]{0,120}?CONTRACT\s+DEMAND|"
    r"E[\s\u2010-\u2015-]*ELECTRICITY\s+BILL\s*:",
    re.I,
)


def extract_pages(data: bytes, filename: str, use_ocr: bool = True) -> tuple[list[DocumentPage], dict[int, str]]:
    """Extract page text and OCR only pages that have no useful text layer."""
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "pdf"
    filetype = "pdf" if extension == "pdf" else extension
    warnings: dict[int, str] = {}
    pages: list[DocumentPage] = []
    with fitz.open(stream=BytesIO(data), filetype=filetype) as document:
        for index, page in enumerate(document):
            text = page.get_text("text", sort=True)
            used_ocr = False
            # Sparse selectable-text pages (for example a continuation page
            # containing only the generated-bill footer) do not benefit from
            # OCR. Scanned pages have no text and normally contain a raster
            # image, so they still take the OCR path.
            needs_ocr = len(text.strip()) < 80 and (
                not text.strip() or bool(page.get_image_info())
            )
            if use_ocr and needs_ocr:
                try:
                    text_page = page.get_textpage_ocr(language="eng", dpi=300, full=True)
                    text = page.get_text("text", textpage=text_page, sort=True)
                    used_ocr = bool(text.strip())
                except (RuntimeError, ValueError):
                    try:
                        text = extract_page_text(page)
                        used_ocr = bool(text.strip())
                    except (ImportError, RuntimeError, ValueError) as exc:
                        warnings[index + 1] = f"Page {index + 1} OCR failed: {exc}"
            pages.append(DocumentPage(index + 1, text, used_ocr))
    return pages, warnings


def segment_bills(pages: list[DocumentPage]) -> list[list[DocumentPage]]:
    """Split a document containing multiple bills while retaining attachment pages."""
    segments: list[list[DocumentPage]] = []
    current: list[DocumentPage] = []
    for page in pages:
        is_start = bool(BILL_START.search(page.text))
        if is_start and current:
            segments.append(current)
            current = []
        current.append(page)
    if current:
        segments.append(current)
    return segments
