"""Protocol for legal sources (BOE, BOPV, BON, ...).

Each source exposes a uniform interface so the citation enricher and
verifier can stay agnostic to which official gazette publishes a norm.

The protocol intentionally returns `Optional[bool]` for `is_vigent` so
that sources without a vigencia endpoint can answer `None` (unknown)
without lying. Callers treat `None` as "assume vigente" to avoid
false-positive derogation warnings.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class NormaSourceMetadata:
    """Source-agnostic snapshot of a norm. Fields beyond the essentials
    are stored in `extra` so each source can attach what it needs."""

    source_id: str  # "boe", "bopv", "static_url", ...
    norm_id: str  # the source-specific identifier
    titulo: str
    is_vigent: bool | None  # True / False / None (unknown)
    url_html: str | None
    fecha_disposicion: date | None = None
    fecha_vigencia: date | None = None
    extra: dict | None = None


@runtime_checkable
class LegalSource(Protocol):
    """Contract every legal-source plugin must satisfy."""

    source_id: str
    """Short identifier used in `norms.yaml` to bind a norm to a source."""

    async def fetch_norma(self, norm_id: str) -> NormaSourceMetadata | None:
        """Return metadata for `norm_id` or None if not retrievable."""
        ...

    async def is_vigent(self, norm_id: str) -> bool | None:
        """True/False/None (unknown). None = "do not flag as derogated"."""
        ...

    def get_url_html(self, norm_id: str) -> str | None:
        """Resolve the public HTML URL for the norm. May be a stable
        pattern (no network needed) or come from `fetch_norma`."""
        ...
