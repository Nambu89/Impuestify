"""Fixtures compartidos para los tests de reglas DefensIA (T1B-000).

Este conftest es el punto unico donde se definen las factories y los helpers
que usan todos los `test_R0xx_*.py`. Principios:

- Aislamiento absoluto entre tests: `reset_registry()` se ejecuta como autouse
  antes y despues de cada test, de modo que un test no puede contaminar el
  REGISTRY de otro (importante para paralelizacion del Grupo A).
- Factories minimas: `build_exp`, `build_brief`, `build_doc` permiten construir
  objetos Pydantic validos con defaults sensatos; el test solo sobreescribe lo
  que le interesa.
- Helper `load_rules()` para que cada test que necesite las reglas reales
  pueda activarlas explicitamente via `defensia_rules.load_all()`.
- Helper `patch_hoy()` para mockear `datetime.now(timezone.utc)` de forma
  determinista en tests de reglas con plazos.

No se hardcodea ninguna regla aqui — este archivo es puro scaffolding.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import pytest

from app.models.defensia import (
    Brief,
    DocumentoEstructurado,
    ExpedienteEstructurado,
    Fase,
    TipoDocumento,
    Tributo,
)
from app.services import defensia_rules
from app.services.defensia_rules_engine import REGISTRY, reset_registry


# ---------------------------------------------------------------------------
# Aislamiento del REGISTRY
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _aislar_registry():
    """Limpia el REGISTRY antes y despues de CADA test de la carpeta rules/.

    Esto garantiza:
    - Que un test que registre reglas no contamine a los siguientes.
    - Que los tests sean orden-independientes (paralelizables).
    - Que smoke tests que llaman a `load_all()` vean un registry reproducible.
    """
    reset_registry()
    yield
    reset_registry()


# ---------------------------------------------------------------------------
# Helpers publicos
# ---------------------------------------------------------------------------

@pytest.fixture
def load_rules():
    """Fixture callable que importa todas las reglas R001-R030.

    Uso::

        def test_algo(load_rules):
            load_rules()
            # en este punto REGISTRY contiene todas las reglas descubiertas
    """
    def _loader() -> None:
        defensia_rules.load_all()

    return _loader


@pytest.fixture
def build_doc():
    """Factory para `DocumentoEstructurado` con defaults sensatos.

    Uso::

        doc = build_doc(TipoDocumento.LIQUIDACION_PROVISIONAL, datos={"x": 1})
    """
    def _build(
        tipo: TipoDocumento,
        datos: Optional[dict[str, Any]] = None,
        *,
        doc_id: str = "doc-test-001",
        nombre_original: str = "documento_test.pdf",
        fecha_acto: Optional[datetime] = None,
        clasificacion_confianza: float = 1.0,
    ) -> DocumentoEstructurado:
        return DocumentoEstructurado(
            id=doc_id,
            nombre_original=nombre_original,
            tipo_documento=tipo,
            fecha_acto=fecha_acto,
            datos=datos or {},
            clasificacion_confianza=clasificacion_confianza,
        )

    return _build


@pytest.fixture
def build_exp():
    """Factory para `ExpedienteEstructurado` con defaults sensatos.

    Uso::

        exp = build_exp(
            tributo=Tributo.IRPF,
            fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
            docs=[doc1, doc2],
        )

    Parametros:
        tributo: enum Tributo. Default Tributo.IRPF.
        fase: enum Fase (se guarda en `fase_detectada`). Default INDETERMINADA.
        docs: lista de DocumentoEstructurado. Default [].
        ccaa: CCAA del expediente. Default "Madrid".
        user_id: acepta por compatibilidad con la firma del plan, pero el
            modelo actual NO tiene campo user_id — se ignora silenciosamente.
        exp_id: id del expediente. Default "exp-test-001".
    """
    def _build(
        tributo: Tributo = Tributo.IRPF,
        fase: Fase = Fase.INDETERMINADA,
        docs: Optional[list[DocumentoEstructurado]] = None,
        *,
        ccaa: str = "Madrid",
        user_id: str = "u1",  # noqa: ARG001 — compat con firma del plan
        exp_id: str = "exp-test-001",
        fase_confianza: float = 0.9,
    ) -> ExpedienteEstructurado:
        return ExpedienteEstructurado(
            id=exp_id,
            tributo=tributo,
            ccaa=ccaa,
            documentos=docs or [],
            fase_detectada=fase,
            fase_confianza=fase_confianza,
        )

    return _build


@pytest.fixture
def build_brief():
    """Factory para `Brief` con defaults sensatos.

    Uso::

        brief = build_brief("AEAT me ha denegado la deduccion por vivienda")
    """
    def _build(
        texto: str = "",
        *,
        chat_history: Optional[list[dict[str, str]]] = None,
        brief_id: Optional[str] = None,
        necesidad: str = "alegaciones",  # noqa: ARG001 — compat futuro
    ) -> Brief:
        return Brief(
            id=brief_id,
            texto=texto,
            chat_history=chat_history or [],
        )

    return _build


@pytest.fixture
def patch_hoy():
    """Helper para mockear `datetime.now(timezone.utc)` en tests deterministas.

    Uso::

        def test_plazo(patch_hoy, mocker):
            patch_hoy(mocker, datetime(2026, 4, 14, tzinfo=timezone.utc))
            # a partir de aqui `datetime.now(timezone.utc)` devuelve esa fecha
            # DENTRO de los modulos que la invoquen via `from datetime import
            # datetime` siempre que el test haga el patch en el path correcto.

    Nota: este helper es una ayuda generica. Cada regla que necesite mockear
    la fecha actual debe hacer el patch en su propio modulo, por ejemplo::

        mocker.patch(
            "app.services.defensia_rules.reglas_procedimentales.R003_prescripcion.datetime",
            wraps=datetime,
        ).now.return_value = fecha_congelada
    """
    def _patch(mocker, fecha: datetime):
        if fecha.tzinfo is None:
            fecha = fecha.replace(tzinfo=timezone.utc)

        class _FrozenDatetime(datetime):
            @classmethod
            def now(cls, tz=None):  # noqa: ARG003
                return fecha

        mocker.patch("datetime.datetime", _FrozenDatetime)
        return fecha

    return _patch


# ---------------------------------------------------------------------------
# Re-export de utilidades para facilitar imports en los tests
# ---------------------------------------------------------------------------

__all__ = [
    "Brief",
    "DocumentoEstructurado",
    "ExpedienteEstructurado",
    "Fase",
    "TipoDocumento",
    "Tributo",
    "REGISTRY",
    "defensia_rules",
    "reset_registry",
]
