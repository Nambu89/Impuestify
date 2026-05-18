"""Enrich assistant markdown answers with hyperlinks to the official BOE.

Detects legal citations in the LLM-generated markdown (`Ley 37/1992`,
`RD 1624/1992`, `Art. 69 LIVA`, …) and replaces them with markdown links
to the corresponding `url_html_consolidada` in BOE.

Design choices:
- **Backend-side enrichment**: invoked once per response, after the
  citation verifier, before sending the SSE final chunk. The frontend
  only needs to render the markdown links — no extra HTTP requests per
  citation.
- **Conservative**: any citation that is NOT a known norm in the
  registry is left untouched. Invented citations (`Ley 99/2099`) don't
  produce bogus links — they stay as plain text.
- **Idempotent**: never replaces inside an existing markdown link or
  fenced code block. Re-running on already-enriched text is a no-op.
- **Stateless**: needs only the `LegalNormsRegistry` instance. No DB.

Coverage:
- Law-level (`ley`, `rd`, `real_decreto`): linked to the norm's
  `url_html_consolidada`.
- Article-level (`art_law`): linked to the parent law's URL (since the
  consolidated text contains all articles; deeper anchor fragments could
  be added if BOE exposes them in metadata — they don't for now).
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.legal.registry import LegalNormsRegistry

logger = logging.getLogger(__name__)


# Reuse the citation patterns from the verifier so detection is identical.
# Order matters: more specific first.
_PATTERN_ART_LAW = re.compile(
    r"(?<![\d/\(\[])"
    r"\b(?:art(?:\.|ículo|iculo)?\s*)?(?P<art>\d+(?:\.\d+)?(?:\s*(?:bis|ter|quater|quinquies))?)"
    r"\s*(?:de\s+la\s+)?(?P<law_sigla>LIRPF|LIVA|LGT|LIS|LISD|LISYD|LIP|LIIEE|LMV|LFTE|TRLITPAJD|TRLRHL|TRLIRNR|LIVMDH|LIGIC|RIVA|RIRPF|RIS|RGAT|RITPAJD)\b",
    re.IGNORECASE,
)

_PATTERN_LEY = re.compile(
    r"\b(?P<full>Ley\s+(?P<num>\d+)\s*/\s*(?P<year>\d{2,4}))\b",
    re.IGNORECASE,
)

_PATTERN_RD = re.compile(
    r"\b(?P<full>RD(?:\.|[-\s]+Ley|[-\s]+Legislativo)?\s+(?P<num>\d+)\s*/\s*(?P<year>\d{2,4}))\b",
    re.IGNORECASE,
)

_PATTERN_REAL_DECRETO = re.compile(
    r"\b(?P<full>Real\s+Decreto(?:\s+(?:Ley|Legislativo))?\s+(?P<num>\d+)\s*/\s*(?P<year>\d{2,4}))\b",
    re.IGNORECASE,
)


# Markdown protection: skip inside fenced code blocks and existing links.
_FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`]+`")
_MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\([^\)]+\)")


class CitationEnricher:
    """Enrich markdown text with links to BOE consolidated norms."""

    def __init__(self, registry: LegalNormsRegistry):
        self._registry = registry

    def enrich_markdown(self, text: str) -> str:
        """Return `text` with known legal citations turned into markdown links.

        Citations whose norm is not in the registry are left intact.
        Existing markdown links and code blocks are not touched.
        """
        if not text:
            return text

        # Identify regions to PROTECT (existing links + code) by replacing
        # them with placeholders, process the rest, then restore.
        protected: list[str] = []

        def _protect(match: re.Match) -> str:
            placeholder = f"\x00P{len(protected)}\x00"
            protected.append(match.group(0))
            return placeholder

        # Order matters: fenced code → inline code → markdown links.
        safe = _FENCED_CODE_RE.sub(_protect, text)
        safe = _INLINE_CODE_RE.sub(_protect, safe)
        safe = _MARKDOWN_LINK_RE.sub(_protect, safe)

        # Apply enrichment patterns. Specific (art_law) first so we don't
        # eat the law-number tail of "Art. 21 LIVA" as a "Ley 21/...".
        safe = _PATTERN_ART_LAW.sub(self._replace_art_law, safe)
        safe = _PATTERN_REAL_DECRETO.sub(self._replace_norm_full, safe)
        safe = _PATTERN_RD.sub(self._replace_norm_full, safe)
        safe = _PATTERN_LEY.sub(self._replace_norm_full, safe)

        # Restore protected regions.
        def _restore(match: re.Match) -> str:
            idx = int(match.group(1))
            return protected[idx]

        return re.sub(r"\x00P(\d+)\x00", _restore, safe)

    # ── Replacement helpers ──

    def _replace_art_law(self, match: re.Match) -> str:
        """Replace `Art. X LIVA` → `[Art. X LIVA](https://www.boe.es/...)`.

        Links to the parent law's URL (BOE doesn't expose per-article
        anchors in metadata). Citation stays plain text if the law isn't
        in the registry."""
        full = match.group(0)
        sigla = match.group("law_sigla").upper()
        norm = self._registry.get_norm(sigla)
        url = self._url_for_norm(norm)
        if url is None:
            return full
        return f"[{full}]({url})"

    def _replace_norm_full(self, match: re.Match) -> str:
        """Replace `Ley 37/1992` / `RD 1624/1992` / `Real Decreto X/Y` with
        a markdown link. Unknown norms pass through unchanged."""
        full = match.group("full")
        norm = self._registry.get_norm(full)
        url = self._url_for_norm(norm)
        if url is None:
            return full
        return f"[{full}]({url})"

    def _url_for_norm(self, norm) -> str | None:
        """Resolve the public URL for a norm via the registry, which
        delegates to the right LegalSource plugin (boe, bopv, …)."""
        if norm is None:
            return None
        return self._registry.get_url_html(norm)


# ── Singleton accessor ───────────────────────────────────────────────────


_enricher: CitationEnricher | None = None


def get_citation_enricher() -> CitationEnricher:
    """Lazy singleton — same registry instance as the rest of the app."""
    global _enricher
    if _enricher is None:
        from app.services.legal import get_legal_registry

        _enricher = CitationEnricher(get_legal_registry())
    return _enricher


def reset_citation_enricher() -> None:
    """Test helper: drop cached enricher so the next call rebuilds it."""
    global _enricher
    _enricher = None
