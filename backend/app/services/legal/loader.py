"""YAML loaders for the legal-norms registry.

Loads + validates the YAML data files under `backend/data/legal/`:
    - norms.yaml
    - articles.yaml
    - invoice_templates.yaml

Validation errors are raised as `LegalDataError` so callers can decide
whether to fail-fast (production) or degrade gracefully (tests).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Tuple

import yaml
from pydantic import ValidationError

from app.services.legal.models import (
    ArticlesCatalog,
    InvoiceTemplatesCatalog,
    NormsCatalog,
)

logger = logging.getLogger(__name__)


class LegalDataError(RuntimeError):
    """Raised when YAML data is missing or malformed."""


# Default location relative to this file's package root.
# backend/app/services/legal/loader.py → up 4 levels → backend/, then data/legal/
_DEFAULT_DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "legal"


def _read_yaml(path: Path) -> dict:
    if not path.is_file():
        raise LegalDataError(f"Legal data file not found: {path}")
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        raise LegalDataError(f"Invalid YAML in {path.name}: {exc}") from exc
    if not isinstance(data, dict):
        raise LegalDataError(f"{path.name} must contain a YAML mapping at root")
    return data


def load_norms(path: Path | None = None) -> NormsCatalog:
    """Load and validate norms.yaml."""
    file = path or _DEFAULT_DATA_DIR / "norms.yaml"
    raw = _read_yaml(file)
    try:
        return NormsCatalog.model_validate(raw)
    except ValidationError as exc:
        raise LegalDataError(f"Validation failed for {file.name}: {exc}") from exc


def load_articles(path: Path | None = None) -> ArticlesCatalog:
    """Load and validate articles.yaml."""
    file = path or _DEFAULT_DATA_DIR / "articles.yaml"
    raw = _read_yaml(file)
    try:
        return ArticlesCatalog.model_validate(raw)
    except ValidationError as exc:
        raise LegalDataError(f"Validation failed for {file.name}: {exc}") from exc


def load_invoice_templates(path: Path | None = None) -> InvoiceTemplatesCatalog:
    """Load and validate invoice_templates.yaml."""
    file = path or _DEFAULT_DATA_DIR / "invoice_templates.yaml"
    raw = _read_yaml(file)
    try:
        return InvoiceTemplatesCatalog.model_validate(raw)
    except ValidationError as exc:
        raise LegalDataError(f"Validation failed for {file.name}: {exc}") from exc


def load_all(
    data_dir: Path | None = None,
) -> Tuple[NormsCatalog, ArticlesCatalog, InvoiceTemplatesCatalog]:
    """Convenience: load the three catalogs from one directory.

    Raises:
        LegalDataError if any file is missing/invalid.
    """
    base = data_dir or _DEFAULT_DATA_DIR
    norms = load_norms(base / "norms.yaml")
    articles = load_articles(base / "articles.yaml")
    templates = load_invoice_templates(base / "invoice_templates.yaml")
    logger.info(
        "Legal registry loaded: %d norms, %d articles, %d invoice templates",
        len(norms.norms),
        len(articles.articles),
        len(templates.templates),
    )
    return norms, articles, templates
