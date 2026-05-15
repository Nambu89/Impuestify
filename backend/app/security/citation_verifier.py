"""
Citation verifier — fact-checks legal citations in LLM responses against the
RAG chunks that were actually retrieved for that query.

Stanford 2025 study found 17-33% of legal citations in RAG systems are
hallucinated (ghost references). For a fiscal advice product this is critical:
a fake "Art. 68.4 LIRPF" can mislead users into wrong tax decisions.

Strategy:
  1. Extract every legal citation pattern from the response (Art. X, Ley X/Y,
     RD X/Y, NF X/Y, BOE codes, AEAT consultations).
  2. For each citation, verify it appears verbatim (modulo formatting) in at
     least one of the retrieved RAG chunks.
  3. Citations not found are FLAGGED (not stripped — user still sees them) and
     a warning footer is appended.

Trade-offs:
  - We do NOT silently strip citations; the user must see what was claimed and
    the warning side-by-side. Hiding citations would be more dangerous.
  - We use a tolerant comparison (whitespace normalize, accent-insensitive,
    article variants like "Art." / "Artículo" / "art" all map together).
  - False-positive rate is acceptable: the warning text says "no he podido
    verificar esta cita en mis fuentes — contrasta con el BOE", which is
    safe wording even when the cite is real but the RAG chunk used different
    phrasing.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ── Citation patterns ────────────────────────────────────────────────────────

# Match orders matter: more specific first.
_CITATION_PATTERNS: List[Tuple[str, str]] = [
    # Articles of common Spanish tax laws.
    # `(?<![\d/])` lookbehind prevents capturing years used in law
    # references (e.g. "Ley 58/2003 LGT" must NOT yield "2003 LGT" as
    # an article — that's the year, captured separately by the `ley`
    # pattern). The `(?<![\d/])` blocks numbers preceded by another
    # digit or a slash.
    (
        r"(?<![\d/])\b(?:art(?:\.|ículo|iculo)?\s*)?\d+(?:\.\d+)?(?:\s*(?:bis|ter|quater|quinquies))?\s*(?:de\s+la\s+)?(?:LIRPF|LIVA|LGT|LIS|LISD|LISYD|LIP|LIIEE|LMV|LFTE|TRLITPAJD|TRLRHL|TRLIRNR|LIVMDH)\b",
        "art_law",
    ),
    # Generic numeric law/RD references
    (r"\bLey\s+\d+\s*/\s*\d{2,4}\b", "ley"),
    (r"\bRD(?:\.|[-\s]+Ley|[-\s]+Legislativo)?\s+\d+\s*/\s*\d{2,4}\b", "rd"),
    (r"\bReal\s+Decreto(?:\s+(?:Ley|Legislativo))?\s+\d+\s*/\s*\d{2,4}\b", "real_decreto"),
    # Norma foral (provincias forales)
    (r"\b(?:Norma\s+Foral|NF)\s+\d+\s*/\s*\d{2,4}\b", "norma_foral"),
    # Decreto Foral
    (r"\b(?:Decreto\s+Foral|DF)\s+\d+\s*/\s*\d{2,4}\b", "decreto_foral"),
    # AEAT/DGT consultations (e.g. V0773-22)
    (r"\bV\d{4}-\d{2}\b", "consulta_dgt"),
    # BOE references (BOE núm. X de fecha)
    (r"\bBOE\s+(?:núm|num|n\.º|n°|n)\s*\.?\s*\d+\b", "boe"),
]

_COMPILED_PATTERNS = [
    (re.compile(pattern, re.IGNORECASE | re.UNICODE), label)
    for pattern, label in _CITATION_PATTERNS
]


# ── Authoritative legal registry (data-driven) ───────────────────────────────
#
# Substitutes the previous hardcoded whitelists `_FUNDAMENTAL_LAWS_WHITELIST`
# and `_CANONICAL_ARTICLES_WHITELIST`. The registry loads known norms +
# canonical articles from YAML files in `backend/data/legal/`, validated
# with pydantic at startup. Maintainers add new norms by editing YAML, not
# Python. Future migration to a SQL table is a single-file change.
#
# Behaviour: the verifier asks the registry whether a citation refers to
# a known legal reference (norm OR canonical article). If yes, it is
# considered verified without requiring RAG chunk evidence. Invented or
# unknown citations still require chunk support, preserving the safety
# net against hallucinations.
def _is_known_legal_reference(citation: "Citation") -> bool:
    """True if the citation refers to a vigent norm or canonical article
    in the legal registry (data-driven via YAML)."""
    # Lazy import avoids circular dependency at module load time.
    from app.services.legal import get_legal_registry
    registry = get_legal_registry()

    if citation.label in ("ley", "rd", "real_decreto"):
        return registry.is_known_norm(citation.normalized)
    if citation.label == "art_law":
        return registry.is_known_article(citation.normalized)
    return False


# ── Normalization ────────────────────────────────────────────────────────────

# Map common article abbreviations so "Art. 68" and "Artículo 68" compare equal.
# Trailing \b would fail on "Art." (period is non-word, next is non-word, so no
# word boundary). Drop trailing \b and rely on \.? to swallow the period.
_ARTICLE_ABBR = re.compile(r"\b(?:art(?:[ií]culo)?)\.?", re.IGNORECASE | re.UNICODE)
_WS = re.compile(r"\s+")


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def _normalize(text: str) -> str:
    """Lowercase, strip accents, collapse whitespace, normalize 'art.' variants."""
    if not text:
        return ""
    normalized = _strip_accents(text.lower())
    normalized = _ARTICLE_ABBR.sub("art", normalized)
    normalized = _WS.sub(" ", normalized)
    return normalized.strip()


# ── Public API ───────────────────────────────────────────────────────────────


@dataclass
class Citation:
    text: str           # the original matched substring (for display)
    label: str          # category: art_law, ley, rd, etc.
    normalized: str     # normalized form for matching
    verified: bool = False
    matched_chunk_id: Optional[str] = None


@dataclass
class VerificationResult:
    citations: List[Citation] = field(default_factory=list)
    unverified: List[Citation] = field(default_factory=list)
    has_unverified: bool = False
    warning_footer: Optional[str] = None
    annotated_response: Optional[str] = None


def extract_citations(text: str) -> List[Citation]:
    """Extract all legal citations from `text`. Deduplicates by normalized form."""
    if not text:
        return []
    seen = set()
    citations: List[Citation] = []
    for pattern, label in _COMPILED_PATTERNS:
        for match in pattern.finditer(text):
            raw = match.group(0).strip()
            norm = _normalize(raw)
            key = (label, norm)
            if key in seen:
                continue
            seen.add(key)
            citations.append(Citation(text=raw, label=label, normalized=norm))
    return citations


def verify_citations(
    response_text: str,
    rag_chunks: Iterable[dict],
) -> VerificationResult:
    """
    Verify citations in the LLM response against the retrieved RAG chunks.

    Args:
        response_text: the LLM-generated answer.
        rag_chunks: iterable of dicts with at least a 'text' key. Optional 'id'
            is recorded on the Citation for tracing. Other shapes are tolerated:
            'content', 'chunk_text' will also be tried.

    Returns:
        VerificationResult with citations classified verified/unverified and a
        warning_footer string ready to append to the response when needed.
    """
    citations = extract_citations(response_text)
    if not citations:
        return VerificationResult(citations=[], unverified=[], has_unverified=False)

    # Build a single normalized corpus from the chunks for fast lookup.
    chunk_index: List[Tuple[str, str]] = []  # (chunk_id, normalized_text)
    for chunk in rag_chunks or []:
        text = chunk.get("text") or chunk.get("content") or chunk.get("chunk_text") or ""
        chunk_id = chunk.get("id") or chunk.get("chunk_id") or "unknown"
        if text:
            chunk_index.append((chunk_id, _normalize(text)))

    if not chunk_index:
        # No retrieval evidence: every citation is unverified, EXCEPT
        # those known by the legal registry (vigent norms / canonical
        # articles from `backend/data/legal/`).
        unverified: List[Citation] = []
        for c in citations:
            if _is_known_legal_reference(c):
                c.verified = True
                c.matched_chunk_id = "legal_registry"
            else:
                c.verified = False
                unverified.append(c)
    else:
        unverified: List[Citation] = []
        for c in citations:
            matched = False
            for chunk_id, norm_text in chunk_index:
                if c.normalized in norm_text:
                    c.verified = True
                    c.matched_chunk_id = chunk_id
                    matched = True
                    break
            if not matched:
                # Fall back to the legal registry: a citation whose
                # number isn't literally in the retrieved chunks is
                # still valid if it refers to a vigent norm or canonical
                # article in the catalog.
                if _is_known_legal_reference(c):
                    c.verified = True
                    c.matched_chunk_id = "legal_registry"
                else:
                    unverified.append(c)

    has_unverified = bool(unverified)
    warning_footer = _build_warning_footer(unverified) if has_unverified else None
    annotated = _annotate_response(response_text, unverified) if has_unverified else None

    if has_unverified:
        logger.warning(
            "Citation verifier flagged %d unverified citation(s): %s",
            len(unverified),
            [c.text for c in unverified],
        )

    return VerificationResult(
        citations=citations,
        unverified=unverified,
        has_unverified=has_unverified,
        warning_footer=warning_footer,
        annotated_response=annotated,
    )


def _build_warning_footer(unverified: List[Citation]) -> str:
    if not unverified:
        return ""
    if len(unverified) == 1:
        cite_list = f"**{unverified[0].text}**"
        intro = "esta referencia normativa"
    else:
        cite_list = ", ".join(f"**{c.text}**" for c in unverified)
        intro = "estas referencias normativas"
    return (
        f"\n\n> ⚠️ No he podido verificar {intro} en mis fuentes documentales: "
        f"{cite_list}. Contrasta directamente con el BOE o tu asesor antes de "
        f"actuar sobre ellas."
    )


def _annotate_response(response_text: str, unverified: List[Citation]) -> str:
    """
    Append the warning footer to the response. We do NOT modify the body — the
    user sees the original claim plus the warning, never silent stripping.
    """
    if not unverified:
        return response_text
    return response_text + _build_warning_footer(unverified)
