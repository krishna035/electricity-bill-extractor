"""Provider adapter contract."""

from abc import ABC, abstractmethod

from bill_extractor.schema import empty_record


class ProviderParser(ABC):
    name = "Unknown"

    @abstractmethod
    def matches(self, text: str) -> bool:
        """Return whether this adapter owns the supplied bill text."""

    @abstractmethod
    def parse(self, text: str) -> dict[str, str | float | None]:
        """Extract direct values into the canonical schema."""

    @staticmethod
    def record() -> dict[str, str | float | None]:
        return empty_record()
