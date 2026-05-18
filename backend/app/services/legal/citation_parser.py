"""Parse a normalized citation string into (law, article, subarticle).

The citation_verifier extracts citations with a regex and produces a
`Citation` object whose `normalized` field looks like:
    "art 69.dos.d liva"
    "art 70 liva"
    "70 liva"               (compound citation second part)
    "ley 37/1992"
    "rd 1624/1992"

This module turns those strings into structured tuples that the
registry can look up. Pure function, no side effects, easy to test.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Tuple

# Recognises forms like:
#   "art 69 liva"             → article=69, subarticle=None, law=LIVA
#   "art 69.dos.d liva"       → article=69, subarticle="dos.d", law=LIVA
#   "art 84.uno.2 liva"       → article=84, subarticle="uno.2", law=LIVA
#   "art 95.6 rirpf"          → article=95, subarticle="6", law=RIRPF
#   "70 liva"                 → article=70 (no "art" prefix accepted)
#
# The "art " prefix is optional because the citation extractor may
# capture compound forms ("69 y 70 liva") yielding just "70 liva".
_ART_LAW_RE = re.compile(
    r"^(?:art\s+)?"  # optional "art "
    r"(?P<article>\d+(?:\s*bis|\s*ter|\s*quater|\s*quinquies)?)"
    r"(?:\.(?P<subarticle>[^\s]+))?"  # optional .uno.2 / .dos.d / .6
    r"\s+"
    r"(?P<law>lirpf|liva|lgt|lis|lisd|lisyd|lip|liiee|lmv|lfte|"
    r"trlitpajd|trlrhl|trlirnr|livmdh|ligic|"
    r"riva|rirpf|ris|rgat|ritpajd)$",
    re.IGNORECASE,
)


_LAW_NUMBER_RE = re.compile(
    r"^(?P<type>ley|rd|rd[-\s]*ley|rd[-\s]*legislativo|"
    r"real\s+decreto(?:\s+ley|\s+legislativo)?|norma\s+foral|nf|"
    r"decreto\s+foral|df)"
    r"\s+(?P<number>\d+)\s*/\s*(?P<year>\d{2,4})$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ParsedArticleCitation:
    """An article citation parsed into its components.

    Example: "art 69.dos.d liva" → law='LIVA' article='69' subarticle='Dos.d'
    """

    law: str  # uppercase sigla
    article: str  # numeric part, e.g. "69"
    subarticle: Optional[str]  # canonical case, e.g. "Dos.d", "Uno.1", "6"


@dataclass(frozen=True)
class ParsedNormCitation:
    """A law/RD citation parsed into its components.

    Example: "ley 37/1992" → norm_type='ley' number=37 year=1992
    """

    norm_type: str  # 'ley', 'rd', 'rd_legislativo', 'norma_foral', etc.
    number: int
    year: int


def parse_article_citation(normalized: str) -> Optional[ParsedArticleCitation]:
    """Parse an art_law citation. Returns None if it doesn't match."""
    m = _ART_LAW_RE.match(normalized.strip())
    if not m:
        return None
    sub = m.group("subarticle")
    sub_canonical = _canonicalise_subarticle(sub) if sub else None
    # Preserve the canonical form "31 bis" with the space (matches the
    # articulado oficial); collapse only multi-space runs.
    article = re.sub(r"\s+", " ", m.group("article")).strip()
    return ParsedArticleCitation(
        law=m.group("law").upper(),
        article=article,
        subarticle=sub_canonical,
    )


def parse_norm_citation(normalized: str) -> Optional[ParsedNormCitation]:
    """Parse a ley/RD-style citation. Returns None if it doesn't match."""
    m = _LAW_NUMBER_RE.match(normalized.strip())
    if not m:
        return None
    raw_type = m.group("type").lower()
    norm_type = _canonicalise_norm_type(raw_type)
    return ParsedNormCitation(
        norm_type=norm_type,
        number=int(m.group("number")),
        year=int(m.group("year")),
    )


# ── Helpers ──────────────────────────────────────────────────────────────


# Mapping from regex-captured form → canonical norm_type used in YAML.
_NORM_TYPE_MAP = {
    "ley": "ley",
    "rd": "rd",
    "rd-ley": "rd",
    "rd ley": "rd",
    "rd-legislativo": "rd_legislativo",
    "rd legislativo": "rd_legislativo",
    "real decreto": "rd",
    "real decreto ley": "rd",
    "real decreto legislativo": "rd_legislativo",
    "norma foral": "norma_foral",
    "nf": "norma_foral",
    "decreto foral": "decreto_foral",
    "df": "decreto_foral",
}


def _canonicalise_norm_type(raw: str) -> str:
    key = re.sub(r"\s+", " ", raw.strip())
    return _NORM_TYPE_MAP.get(key, key.replace(" ", "_"))


# Subarticle canonical form keeps the Spanish-numeral case intact:
# "Uno", "Dos", "Tres", "Cuatro"... in TitleCase; numeric tail unchanged.
_SUB_TOKEN_CAP = {"uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez"}


def _canonicalise_subarticle(raw: str) -> str:
    """Normalise '.dos.d' / '.UNO.1' / '.6' to canonical form 'Dos.d' / 'Uno.1' / '6'."""
    parts = raw.split(".")
    out: list[str] = []
    for p in parts:
        if not p:
            continue
        if p.lower() in _SUB_TOKEN_CAP:
            out.append(p.capitalize())
        else:
            out.append(p)
    return ".".join(out)


def split_compound_article_citation(normalized: str) -> Tuple[Optional[ParsedArticleCitation], ...]:
    """Split compound citations like 'art 69 y 70 liva' into individuals.

    Returns a tuple of parsed articles. Empty tuple if no parse succeeds.
    """
    # Detect the law sigla at the end, then split numbers by 'y'/',' / '-'.
    norm = normalized.strip().lower()
    parts = re.split(r"\s+y\s+|,\s*|\s*-\s*", norm)
    if len(parts) <= 1:
        single = parse_article_citation(norm)
        return (single,) if single else ()

    # Try to extract the law sigla from the LAST part.
    last = parts[-1].strip()
    last_parsed = parse_article_citation(last)
    if not last_parsed:
        return ()

    law = last_parsed.law
    results: list[ParsedArticleCitation] = []
    for i, part in enumerate(parts[:-1]):
        # Re-attach the law sigla so the parser succeeds.
        prefixed = part.strip()
        # If the part already has the sigla, use it directly.
        if last_parsed.law.lower() in prefixed:
            parsed = parse_article_citation(prefixed)
        else:
            parsed = parse_article_citation(f"{prefixed} {law}")
        if parsed:
            results.append(parsed)
    results.append(last_parsed)
    return tuple(results)
