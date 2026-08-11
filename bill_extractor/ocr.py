"""Portable OCR fallback for scanned PDFs and image uploads."""

from functools import lru_cache

import fitz


@lru_cache(maxsize=1)
def _engine():
    from rapidocr import RapidOCR

    return RapidOCR(params={"Global.log_level": "critical"})


def extract_page_text(page: fitz.Page) -> str:
    """Run offline OCR and reconstruct reading-order lines from detected boxes."""
    # Image documents are represented at 72 DPI by PyMuPDF. Rendering at 144
    # DPI preserves small table text and minus signs that disappear at 72 DPI.
    pixmap = page.get_pixmap(dpi=144, alpha=False)
    result = _engine()(pixmap.tobytes("png"))
    if result.boxes is None or not result.txts:
        return ""

    items: list[tuple[float, float, float, str]] = []
    for box, value in zip(result.boxes, result.txts):
        center_y = sum(float(point[1]) for point in box) / len(box)
        left_x = min(float(point[0]) for point in box)
        height = max(float(point[1]) for point in box) - min(float(point[1]) for point in box)
        items.append((center_y, left_x, max(height, 1.0), value.strip()))
    items.sort(key=lambda item: (item[0], item[1]))

    groups: list[list[tuple[float, float, float, str]]] = []
    for item in items:
        if not groups:
            groups.append([item])
            continue
        prior = groups[-1]
        prior_y = sum(entry[0] for entry in prior) / len(prior)
        prior_height = sum(entry[2] for entry in prior) / len(prior)
        if abs(item[0] - prior_y) <= max(item[2], prior_height) * 0.65:
            prior.append(item)
        else:
            groups.append([item])

    return "\n".join(
        " ".join(entry[3] for entry in sorted(group, key=lambda entry: entry[1]) if entry[3])
        for group in groups
    )
