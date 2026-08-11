"""Shared extraction models."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DocumentPage:
    number: int
    text: str
    used_ocr: bool = False


@dataclass
class BillRecord:
    values: dict[str, str | float | None]
    provider: str
    filename: str
    pages: list[int]
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "filename": self.filename,
            "pages": ", ".join(str(page) for page in self.pages),
            **self.values,
            "warnings": " | ".join(self.warnings),
        }
