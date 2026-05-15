"""The LegalNormsRegistry — authoritative lookup of known norms/articles.

Pattern: Protocol + concrete YAML-backed implementation. Future
migration to a SQL-backed registry only requires a new implementation;
callers depend on the Protocol.

Thread-safe: singleton via `lru_cache`. Reload via `reset_legal_registry()`.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

from app.services.legal.citation_parser import (
    ParsedArticleCitation,
    ParsedNormCitation,
    parse_article_citation,
    parse_norm_citation,
    split_compound_article_citation,
)
from app.services.legal.loader import (
    LegalDataError,
    load_all,
)
from app.services.legal.models import (
    ArticlesCatalog,
    CanonicalArticle,
    InvoiceTemplate,
    InvoiceTemplatesCatalog,
    LegalNorm,
    NormsCatalog,
)

logger = logging.getLogger(__name__)


@runtime_checkable
class LegalNormsRegistry(Protocol):
    """Contract for the legal-norms lookup service.

    Any future replacement (Turso table, BOE API, etc.) only needs to
    implement this interface. Callers (citation_verifier, tax_agent)
    depend on the protocol, not on a concrete impl.
    """

    def is_known_norm(self, normalized_citation: str, as_of: Optional[date] = None) -> bool:
        """True if the citation refers to a vigent norm in the catalog."""
        ...

    def is_known_article(
        self,
        normalized_citation: str,
        as_of: Optional[date] = None,
    ) -> bool:
        """True if the citation refers to a vigent canonical article."""
        ...

    def get_norm(self, sigla_or_id: str) -> Optional[LegalNorm]:
        """Return the LegalNorm matching by sigla, full_id, or alias."""
        ...

    def get_article(self, law: str, article: str, subarticle: Optional[str] = None) -> Optional[CanonicalArticle]:
        """Return the canonical article if present."""
        ...

    def get_invoice_template(self, key: str) -> Optional[InvoiceTemplate]:
        """Return the invoice template by key."""
        ...

    def all_invoice_templates(self) -> list[InvoiceTemplate]:
        """Return every template — used to render system prompt section."""
        ...


# ── Concrete YAML implementation ─────────────────────────────────────────


class YamlLegalNormsRegistry:
    """File-backed registry. Loads YAMLs from a directory on construction.

    Performance: catalog stays in memory; lookups are dict-based O(1).
    """

    def __init__(
        self,
        norms_catalog: NormsCatalog,
        articles_catalog: ArticlesCatalog,
        templates_catalog: InvoiceTemplatesCatalog,
    ):
        self._norms_by_sigla: dict[str, LegalNorm] = {}
        self._norms_by_alias: dict[str, LegalNorm] = {}
        self._norms_by_type_number_year: dict[tuple[str, int, int], LegalNorm] = {}
        self._articles_index: dict[tuple[str, str, Optional[str]], CanonicalArticle] = {}
        self._templates_by_key: dict[str, InvoiceTemplate] = {}

        self._build_norm_indexes(norms_catalog)
        self._build_article_indexes(articles_catalog)
        self._build_template_indexes(templates_catalog)

    @classmethod
    def from_directory(cls, data_dir: Path | None = None) -> "YamlLegalNormsRegistry":
        """Load all YAMLs from `data_dir` (or default `backend/data/legal/`)."""
        norms, articles, templates = load_all(data_dir)
        return cls(norms, articles, templates)

    # ── Index builders ──

    def _build_norm_indexes(self, catalog: NormsCatalog) -> None:
        for norm in catalog.norms:
            self._norms_by_sigla[norm.sigla.upper()] = norm
            for alias in norm.aliases:
                self._norms_by_alias[alias.lower().strip()] = norm
            self._norms_by_alias[norm.full_id.lower().strip()] = norm
            parsed = parse_norm_citation(norm.full_id.lower())
            if parsed is not None:
                key = (parsed.norm_type, parsed.number, _normalise_year(parsed.year))
                self._norms_by_type_number_year[key] = norm

    def _build_article_indexes(self, catalog: ArticlesCatalog) -> None:
        for art in catalog.articles:
            key = (art.law.upper(), art.article, art.subarticle)
            self._articles_index[key] = art

    def _build_template_indexes(self, catalog: InvoiceTemplatesCatalog) -> None:
        for tpl in catalog.templates:
            self._templates_by_key[tpl.key] = tpl

    # ── Public lookup ──

    def is_known_norm(self, normalized_citation: str, as_of: Optional[date] = None) -> bool:
        norm = self._resolve_norm(normalized_citation)
        if norm is None:
            return False
        return norm.is_vigent_on(as_of or date.today())

    def is_known_article(self, normalized_citation: str, as_of: Optional[date] = None) -> bool:
        # Try direct parse first, then compound forms.
        for parsed in _iter_article_candidates(normalized_citation):
            if self._article_is_known(parsed, as_of):
                return True
        return False

    def get_norm(self, sigla_or_id: str) -> Optional[LegalNorm]:
        return self._resolve_norm(sigla_or_id)

    def get_article(self, law: str, article: str, subarticle: Optional[str] = None) -> Optional[CanonicalArticle]:
        return self._articles_index.get((law.upper(), article, subarticle))

    def get_invoice_template(self, key: str) -> Optional[InvoiceTemplate]:
        return self._templates_by_key.get(key)

    def all_invoice_templates(self) -> list[InvoiceTemplate]:
        return list(self._templates_by_key.values())

    # ── Helpers ──

    def _resolve_norm(self, citation: str) -> Optional[LegalNorm]:
        cleaned = citation.lower().strip()
        if cleaned.upper() in self._norms_by_sigla:
            return self._norms_by_sigla[cleaned.upper()]
        if cleaned in self._norms_by_alias:
            return self._norms_by_alias[cleaned]
        parsed = parse_norm_citation(cleaned)
        if parsed is not None:
            key = (parsed.norm_type, parsed.number, _normalise_year(parsed.year))
            return self._norms_by_type_number_year.get(key)
        return None

    def _article_is_known(
        self,
        parsed: ParsedArticleCitation,
        as_of: Optional[date],
    ) -> bool:
        # Try exact subarticle match first, then walk up to broader entries.
        target = as_of or date.today()
        candidates = [parsed.subarticle]
        if parsed.subarticle:
            # "Uno.1" → also try "Uno", None
            parts = parsed.subarticle.split(".")
            for i in range(len(parts) - 1, 0, -1):
                candidates.append(".".join(parts[:i]))
            candidates.append(None)
        else:
            candidates = [None]
        for sub in candidates:
            art = self._articles_index.get((parsed.law.upper(), parsed.article, sub))
            if art and art.is_vigent_on(target):
                return True
        return False


def _iter_article_candidates(normalized: str):
    """Yield possible parses of the citation, including compound forms."""
    parsed = parse_article_citation(normalized)
    if parsed:
        yield parsed
    compound = split_compound_article_citation(normalized)
    for p in compound:
        if p is not None:
            yield p


def _normalise_year(year: int) -> int:
    """Two-digit years → 4-digit (best-effort)."""
    if year < 100:
        return 1900 + year if year >= 70 else 2000 + year
    return year


# ── Singleton accessor ───────────────────────────────────────────────────


@lru_cache(maxsize=1)
def get_legal_registry(data_dir: Optional[str] = None) -> LegalNormsRegistry:
    """Return the singleton registry. Lazy-loaded.

    On YAML errors logs the problem and returns a degraded empty
    registry — the citation verifier will still work, just without the
    canonical whitelist. This avoids crashing the whole app on a
    malformed YAML deploy.
    """
    try:
        path = Path(data_dir) if data_dir else None
        return YamlLegalNormsRegistry.from_directory(path)
    except LegalDataError as exc:
        logger.error(
            "Legal registry failed to load (%s). Falling back to empty registry; "
            "all citations will require RAG chunk evidence.",
            exc,
        )
        return _empty_registry()


def reset_legal_registry() -> None:
    """Clear the singleton — useful for tests and hot-reload."""
    get_legal_registry.cache_clear()


def _empty_registry() -> "YamlLegalNormsRegistry":
    """Build an empty registry — used as fallback on YAML errors."""
    from app.services.legal.models import (
        ArticlesCatalog,
        InvoiceTemplatesCatalog,
        NormsCatalog,
    )
    return YamlLegalNormsRegistry(
        NormsCatalog(norms=[]),
        ArticlesCatalog(articles=[]),
        InvoiceTemplatesCatalog(templates=[]),
    )
