"""Integration test usando el caso primigenio de David Oliva.

Este test es el GROUND TRUTH del producto. Valida que el pipeline de extracción
+ detección de fase funciona correctamente sobre el expediente real del beta
tester David (anonimizado).

Si este test falla, la build falla (spec §20 criterio de aceptación).
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from app.models.defensia import (
    ExpedienteEstructurado, DocumentoEstructurado,
    Tributo, TipoDocumento, Fase,
)
from app.services.defensia_phase_detector import detect_fase


FIXTURE = (
    Path(__file__).parent / "fixtures" / "caso_david" / "expediente_anonimizado.json"
)


def _cargar_expediente() -> ExpedienteEstructurado:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    docs = [
        DocumentoEstructurado(
            id=d["id"],
            nombre_original=d["nombre_original"],
            tipo_documento=TipoDocumento(d["tipo_documento"]),
            fecha_acto=datetime.fromisoformat(d["fecha_acto"]).replace(
                tzinfo=timezone.utc
            ),
            datos=d["datos"],
        )
        for d in raw["documentos"]
    ]
    return ExpedienteEstructurado(
        id="david",
        tributo=Tributo(raw["tributo"]),
        ccaa=raw["ccaa"],
        documentos=docs,
    )


def test_caso_david_fase_detectada_tear_interpuesta_reciente():
    """David presentó la reclamación TEAR sanción el 2026-04-09.

    Con `hoy` dentro de la ventana de 30 días posteriores a esa fecha,
    la fase activa es TEAR_INTERPUESTA (ampliación urgente).
    """
    exp = _cargar_expediente()
    hoy = datetime(2026, 4, 13, tzinfo=timezone.utc)  # 4 días después
    fase, confianza = detect_fase(exp, hoy=hoy)
    assert fase == Fase.TEAR_INTERPUESTA
    assert confianza >= 0.85


def test_caso_david_fase_detectada_tear_ampliacion_posible_pasados_30d():
    """Con `hoy` pasados más de 30 días del último escrito TEAR, la fase
    transiciona a TEAR_AMPLIACION_POSIBLE.
    """
    exp = _cargar_expediente()
    hoy = datetime(2026, 6, 1, tzinfo=timezone.utc)  # 53 días después
    fase, confianza = detect_fase(exp, hoy=hoy)
    assert fase == Fase.TEAR_AMPLIACION_POSIBLE
    assert confianza >= 0.85


def test_caso_david_timeline_ordenado_8_docs():
    exp = _cargar_expediente()
    tl = exp.timeline_ordenado()
    assert len(tl) == 8
    assert tl[0].tipo_documento == TipoDocumento.REQUERIMIENTO
    assert tl[-1].tipo_documento == TipoDocumento.ESCRITO_RECLAMACION_TEAR_USUARIO


def test_caso_david_contiene_doble_tipicidad_sancion():
    exp = _cargar_expediente()
    sanciones = [
        d for d in exp.documentos
        if d.tipo_documento == TipoDocumento.ACUERDO_IMPOSICION_SANCION
    ]
    assert len(sanciones) == 1
    assert sanciones[0].datos["tiene_doble_tipicidad_191_194"] is True


def test_caso_david_tiene_diff_gastos_adquisicion():
    exp = _cargar_expediente()
    liq = next(
        d for d in exp.documentos
        if d.tipo_documento == TipoDocumento.LIQUIDACION_PROVISIONAL
    )
    assert liq.datos["diff_gastos_adquisicion_no_admitidos"] == 759.25
