"""Tests para DefensIA Writer Service (T2B-006).

Cubre selección de plantilla por fase + heurística TEAR, renderizado de
markdown con disclaimer duplicado, preservación de tildes y símbolos
(autoescape=False), manejo de expedientes sin argumentos y uso de modelos
Pydantic reales (ExpedienteEstructurado + ArgumentoVerificado).
"""
from __future__ import annotations

from datetime import date, datetime

import pytest

from app.models.defensia import (
    ArgumentoVerificado,
    Brief,
    DocumentoEstructurado,
    ExpedienteEstructurado,
    Fase,
    TipoDocumento,
    Tributo,
)
from app.services.defensia_writer_service import (
    DISCLAIMER_CANONICO,
    DefensiaWriterService,
    UMBRAL_TEAR_ABREVIADA_EUR,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def writer() -> DefensiaWriterService:
    return DefensiaWriterService()


def _build_expediente(
    fase: Fase,
    *,
    documentos: list[DocumentoEstructurado] | None = None,
    tributo: Tributo = Tributo.IRPF,
    ccaa: str = "Comunidad de Madrid",
) -> ExpedienteEstructurado:
    return ExpedienteEstructurado(
        id="exp-test-001",
        tributo=tributo,
        ccaa=ccaa,
        documentos=documentos or [],
        fase_detectada=fase,
        fase_confianza=0.92,
    )


def _build_argumento(
    *,
    regla_id: str = "R001",
    descripcion: str = "Motivación insuficiente del acto",
    cita_verificada: str = (
        "La Administración debe motivar los actos conforme al art. 102.2.c LGT."
    ),
    referencia: str = "Art. 102.2.c LGT",
    confianza: float = 0.91,
) -> ArgumentoVerificado:
    return ArgumentoVerificado(
        regla_id=regla_id,
        descripcion=descripcion,
        cita_verificada=cita_verificada,
        referencia_normativa_canonica=referencia,
        confianza=confianza,
        datos_disparo={"origen": "test"},
        impacto_estimado="Alto",
    )


def _build_documento(
    tipo: TipoDocumento = TipoDocumento.PROPUESTA_LIQUIDACION,
    *,
    nombre: str = "Propuesta liquidación IRPF 2023.pdf",
    fecha: datetime | None = None,
) -> DocumentoEstructurado:
    return DocumentoEstructurado(
        id="doc-001",
        nombre_original=nombre,
        tipo_documento=tipo,
        fecha_acto=fecha or datetime(2026, 3, 15),
        datos={},
        clasificacion_confianza=0.95,
    )


# ---------------------------------------------------------------------------
# 1-8. Selección de plantilla
# ---------------------------------------------------------------------------


def test_seleccionar_plantilla_por_fase_comprobacion_propuesta(writer):
    expediente = _build_expediente(Fase.COMPROBACION_PROPUESTA)
    assert writer.seleccionar_plantilla(expediente) == "alegaciones_verificacion.j2"


def test_seleccionar_plantilla_por_fase_comprobacion_post_alegaciones(writer):
    expediente = _build_expediente(Fase.COMPROBACION_POST_ALEGACIONES)
    assert (
        writer.seleccionar_plantilla(expediente)
        == "alegaciones_comprobacion_limitada.j2"
    )


@pytest.mark.parametrize(
    "fase",
    [
        Fase.SANCIONADOR_INICIADO,
        Fase.SANCIONADOR_PROPUESTA,
        Fase.SANCIONADOR_IMPUESTA,
    ],
)
def test_seleccionar_plantilla_por_fase_sancionador(writer, fase):
    expediente = _build_expediente(fase)
    assert writer.seleccionar_plantilla(expediente) == "alegaciones_sancionador.j2"


def test_seleccionar_plantilla_tear_abreviada_cuota_menor_6000(writer):
    expediente = _build_expediente(Fase.TEAR_INTERPUESTA)
    plantilla = writer.seleccionar_plantilla(
        expediente, cuota_estimada_eur=UMBRAL_TEAR_ABREVIADA_EUR - 0.01
    )
    assert plantilla == "reclamacion_tear_abreviada.j2"


def test_seleccionar_plantilla_tear_general_cuota_mayor_6000(writer):
    expediente = _build_expediente(Fase.TEAR_INTERPUESTA)
    plantilla = writer.seleccionar_plantilla(
        expediente, cuota_estimada_eur=UMBRAL_TEAR_ABREVIADA_EUR + 500.0
    )
    assert plantilla == "reclamacion_tear_general.j2"


def test_seleccionar_plantilla_tear_ampliacion(writer):
    expediente = _build_expediente(Fase.TEAR_AMPLIACION_POSIBLE)
    assert writer.seleccionar_plantilla(expediente) == "ampliacion_tear.j2"


def test_seleccionar_plantilla_reposicion(writer):
    expediente = _build_expediente(Fase.REPOSICION_INTERPUESTA)
    assert (
        writer.seleccionar_plantilla(expediente) == "reclamacion_tear_abreviada.j2"
    )


def test_seleccionar_plantilla_fuera_de_alcance_fallback(writer):
    expediente = _build_expediente(Fase.FUERA_DE_ALCANCE)
    assert writer.seleccionar_plantilla(expediente) == "escrito_generico.j2"


# ---------------------------------------------------------------------------
# 9-10. Render markdown estructural + disclaimer
# ---------------------------------------------------------------------------


def test_render_escrito_devuelve_markdown_no_vacio(writer):
    expediente = _build_expediente(
        Fase.COMPROBACION_PROPUESTA,
        documentos=[_build_documento()],
    )
    argumentos = [_build_argumento()]
    output = writer.render_escrito(
        expediente,
        argumentos,
        brief=Brief(texto="Caso de ejemplo"),
        fecha_hoy=date(2026, 4, 14),
    )
    assert isinstance(output, str)
    assert len(output) > 100
    # Contiene al menos un heading markdown (# espacio).
    assert "# " in output


def test_render_incluye_disclaimer_dos_veces(writer):
    """Las plantillas oficiales embeben el disclaimer en header + footer."""
    expediente = _build_expediente(
        Fase.COMPROBACION_PROPUESTA,
        documentos=[_build_documento()],
    )
    output = writer.render_escrito(
        expediente,
        [_build_argumento()],
        brief=Brief(texto=""),
        fecha_hoy=date(2026, 4, 14),
    )
    assert output.count(DISCLAIMER_CANONICO) >= 2


# ---------------------------------------------------------------------------
# 11. Cita verificada integra en el output
# ---------------------------------------------------------------------------


def test_render_incluye_argumento_cita_verificada(writer):
    cita = "Texto del art. 102.2.c LGT integrado"
    argumento = _build_argumento(cita_verificada=cita)
    expediente = _build_expediente(
        Fase.COMPROBACION_PROPUESTA,
        documentos=[_build_documento()],
    )
    output = writer.render_escrito(
        expediente, [argumento], fecha_hoy=date(2026, 4, 14)
    )
    assert cita in output


# ---------------------------------------------------------------------------
# 12. Preservación de tildes
# ---------------------------------------------------------------------------


def test_render_preserva_tildes(writer):
    argumento = _build_argumento(
        descripcion="Motivación insuficiente",
        cita_verificada="La Administración debe motivar.",
    )
    expediente = _build_expediente(
        Fase.COMPROBACION_PROPUESTA,
        documentos=[_build_documento()],
    )
    output = writer.render_escrito(
        expediente, [argumento], fecha_hoy=date(2026, 4, 14)
    )
    assert "Motivación" in output
    assert "Administración" in output


# ---------------------------------------------------------------------------
# 13. autoescape=False (símbolos literales)
# ---------------------------------------------------------------------------


def test_render_autoescape_false(writer):
    cita = "Párrafo 2.º con símbolos < > &"
    argumento = _build_argumento(cita_verificada=cita)
    expediente = _build_expediente(
        Fase.COMPROBACION_PROPUESTA,
        documentos=[_build_documento()],
    )
    output = writer.render_escrito(
        expediente, [argumento], fecha_hoy=date(2026, 4, 14)
    )
    # Los caracteres aparecen tal cual, sin ser escapados a entidades HTML.
    assert "2.º" in output
    assert "<" in output
    assert ">" in output
    assert "&" in output
    assert "&lt;" not in output
    assert "&gt;" not in output
    assert "&amp;" not in output


# ---------------------------------------------------------------------------
# 14. Render sin argumentos no crashea y mantiene estructura
# ---------------------------------------------------------------------------


def test_render_sin_argumentos_no_crashea(writer):
    expediente = _build_expediente(
        Fase.COMPROBACION_PROPUESTA,
        documentos=[_build_documento()],
    )
    output = writer.render_escrito(
        expediente, argumentos=[], fecha_hoy=date(2026, 4, 14)
    )
    # Estructura mínima: header + suplico + footer.
    assert "# " in output
    assert "Suplico" in output
    # Disclaimer en header y footer aunque no haya argumentos.
    assert output.count(DISCLAIMER_CANONICO) >= 2


# ---------------------------------------------------------------------------
# 15. Dictamen: cita normativa viene del argumento, no hardcodeada
# ---------------------------------------------------------------------------


def test_render_dictamen_no_hardcode_articulos(writer):
    cita = "Según Art. 102 LGT, la motivación es obligatoria."
    argumento = _build_argumento(
        cita_verificada=cita,
        referencia="Art. 102 LGT",
    )
    expediente = _build_expediente(
        Fase.COMPROBACION_PROPUESTA,
        documentos=[_build_documento()],
    )
    output = writer.render_dictamen(
        expediente,
        [argumento],
        brief=Brief(texto="Recibí propuesta IRPF"),
        fecha_hoy=date(2026, 4, 14),
    )
    # La cita exacta aparece (viene del argumento, no del template).
    assert cita in output
    # El dictamen incluye la estructura de análisis DefensIA.
    assert "Dictamen" in output
    assert "R001" in output  # regla_id dinámico del argumento


# ---------------------------------------------------------------------------
# 16. Writer usa modelos Pydantic reales (no dicts)
# ---------------------------------------------------------------------------


def test_writer_usa_modelos_reales(writer):
    """Confirma que las plantillas acceden a atributos (.regla_id, etc.),
    no a claves dict. Si Jinja cayera a __getitem__ sobre un dict, este
    test seguiría pasando, pero la plantilla real usa atributos y por
    tanto fallaría el render si pasamos dicts. Forzamos modelos reales."""
    expediente = _build_expediente(
        Fase.COMPROBACION_PROPUESTA,
        documentos=[_build_documento()],
    )
    argumento = _build_argumento(
        regla_id="R042",
        descripcion="Falta de motivación",
        cita_verificada="Cita test real",
        referencia="Art. X LGT",
    )

    assert isinstance(expediente, ExpedienteEstructurado)
    assert isinstance(argumento, ArgumentoVerificado)

    output = writer.render_escrito(
        expediente, [argumento], fecha_hoy=date(2026, 4, 14)
    )
    # La plantilla ha resuelto .descripcion, .cita_verificada y
    # .referencia_normativa_canonica del modelo real.
    assert "Falta de motivación" in output
    assert "Cita test real" in output
    assert "Art. X LGT" in output
