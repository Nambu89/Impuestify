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
    # Articles of common Spanish tax laws
    (
        r"\b(?:art(?:\.|ículo|iculo)?\s*)?\d+(?:\.\d+)?(?:\s*(?:bis|ter|quater|quinquies))?\s*(?:de\s+la\s+)?(?:LIRPF|LIVA|LGT|LIS|LISD|LISYD|LIP|LIIEE|LMV|LFTE|TRLITPAJD|TRLRHL|TRLIRNR|LIVMDH)\b",
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


# ── Fundamental laws whitelist ───────────────────────────────────────────────
#
# Spanish tax law has a handful of foundational statutes that every assistant
# response will cite (LIRPF, LIVA, LGT, LIS, etc.). The RAG chunk retrieval is
# topic-targeted: a chunk about deduction X may not contain the literal string
# "Ley 35/2006" even though it's about LIRPF. Flagging "Ley 35/2006" as
# unverified in that case is a false positive that destroys user trust — the
# user reads "I couldn't verify the basic income tax law" and assumes the
# whole answer is unreliable.
#
# The whitelist below treats these statutes as part of the implicit corpus
# that ALWAYS exists. It applies ONLY to category-level citations
# (ley/rd/real_decreto), NEVER to specific articles of those laws — an
# invented "Art. 999.99 LIRPF" must still flag if no chunk supports it.
_FUNDAMENTAL_LAWS_WHITELIST = frozenset({
    # Leyes fiscales fundamentales
    "ley 37/1992",        # LIVA
    "ley 35/2006",        # LIRPF
    "ley 27/2014",        # LIS
    "ley 58/2003",        # LGT
    "ley 20/1991",        # LIGIC (Canarias)
    "ley 29/1987",        # LISD
    "ley 19/1991",        # LIP
    "ley 38/1992",        # LIIEE
    "ley 49/2002",        # Régimen fiscal entidades sin fines lucrativos / mecenazgo
    "ley 19/1994",        # REF Canarias
    "ley 22/2009",        # Cesión tributos a CCAA
    "ley 11/2021",        # Medidas prevención fraude
    "ley 7/2024",         # Reforma fiscal microempresas + ahorro 2025
    # Reglamentos
    "rd 1624/1992",       # RIVA
    "rd 439/2007",        # RIRPF
    "rd 634/2015",        # RIS
    "rd 828/1995",        # RITPAJD
    "rd 1065/2007",       # RGAT
    "rd 1619/2012",       # Reglamento facturación
    # Reales Decretos Legislativos / Textos Refundidos
    "rd legislativo 1/1993",  # TR ITPAJD
    "rd legislativo 2/2004",  # TR LRHL (Haciendas Locales)
    "rd legislativo 5/2004",  # TR LIRNR
    "real decreto legislativo 1/1993",
    "real decreto legislativo 2/2004",
    "real decreto legislativo 5/2004",
    # Variantes "Real Decreto" sin abreviar
    "real decreto 1624/1992",
    "real decreto 439/2007",
    "real decreto 634/2015",
    "real decreto 828/1995",
    "real decreto 1065/2007",
    "real decreto 1619/2012",
})

# NOTE: bare siglas (e.g., "según la LIVA...") do NOT need a whitelist
# because the citation extractor's art_law pattern requires a leading
# number (\d+) before the sigla — "LIVA" alone never produces a Citation.
# So no false positive is possible for sigla-only references.


# Whitelist de articulos canonicos que el system prompt de TaxAgent cita
# explicitamente en sus plantillas. Estos articulos existen y son
# verificables contra el BOE, pero los chunks RAG pueden no contener su
# numero literal (e.g., el chunk dice "operacion no sujeta" sin citar el
# articulo). Sin esta whitelist, el verifier marca como unverified citas
# tipo "Art. 70 LIVA" cuando el chunk no lo escribe textualmente.
#
# Mantener en sincronia con las plantillas del system prompt en
# `app/agents/tax_agent.py` (secciones TEXTO LITERAL PARA FACTURAS y
# EJEMPLOS Y PRO TIP). Si se añade un articulo nuevo en el prompt,
# añadirlo aqui tras verificarlo en el BOE.
_CANONICAL_ARTICLES_WHITELIST = frozenset({
    # LIVA — localizacion servicios y operaciones especiales
    "art 21 liva",
    "art 25 liva",
    "art 69 liva",
    "art 69.uno liva",
    "art 69.uno.1 liva",
    "art 69.uno.2 liva",
    "art 69.dos liva",
    "art 69.dos.a liva",
    "art 69.dos.b liva",
    "art 69.dos.c liva",
    "art 69.dos.d liva",
    "art 69.dos.e liva",
    "art 69.dos.f liva",
    "art 69.dos.g liva",
    "art 69.dos.h liva",
    "art 69.dos.i liva",
    "art 69.dos.j liva",
    "art 69.dos.k liva",
    "art 69.dos.l liva",
    "art 70 liva",
    "art 70.dos liva",
    "art 84 liva",
    "art 84.uno liva",
    "art 84.uno.2 liva",
    "art 154 liva",
    "art 155 liva",
    "art 156 liva",
    "art 157 liva",
    "art 158 liva",
    "art 159 liva",
    "art 160 liva",
    "art 161 liva",
    "art 162 liva",
    "art 163 liva",
    # LIRPF — articulos clave citados en pro tips
    "art 68 lirpf",
    "art 68.4 lirpf",
    "art 96 lirpf",
    "art 81 lirpf",
    # RIRPF — dispensas y retenciones
    "art 95.6 rirpf",
    "art 95 rirpf",
    # LGSS — autonomos
    "art 38 lgss",
    "art 38 ter lgss",
})


def _is_fundamental_law_reference(citation: "Citation") -> bool:
    """
    True if the citation refers to a foundational Spanish tax statute or
    a canonical article documented in the TaxAgent system prompt. The model
    can safely cite these without requiring a RAG chunk that contains the
    exact numeric reference. Two whitelists:
      1. Law-level (ley/rd/real_decreto) → _FUNDAMENTAL_LAWS_WHITELIST.
      2. Article-level (art_law) → _CANONICAL_ARTICLES_WHITELIST,
         limited to articles the system prompt explicitly cites.

    For all other art_law citations (invented or rare articles), RAG chunk
    evidence is still required.
    """
    if citation.label in ("ley", "rd", "real_decreto"):
        return citation.normalized in _FUNDAMENTAL_LAWS_WHITELIST
    if citation.label == "art_law":
        norm = citation.normalized
        # The regex captures both "Art. 70 LIVA" and "70 LIVA" (when used in
        # compound like "Arts. 69 y 70 LIVA"). _normalize only adds "art "
        # prefix when the original had "Art./Artículo". So try both variants.
        candidates = {norm}
        if not norm.startswith("art "):
            candidates.add(f"art {norm}")
        for cand in candidates:
            if cand in _CANONICAL_ARTICLES_WHITELIST:
                return True
        return False
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
        # fundamental laws which are part of the implicit corpus.
        unverified: List[Citation] = []
        for c in citations:
            if _is_fundamental_law_reference(c):
                c.verified = True
                c.matched_chunk_id = "whitelist_fundamental_law"
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
                # Fall back to whitelist for fundamental laws (LIVA, LIRPF, etc.)
                # whose number may not literally appear in chunks targeted at a
                # specific article or deduction.
                if _is_fundamental_law_reference(c):
                    c.verified = True
                    c.matched_chunk_id = "whitelist_fundamental_law"
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
