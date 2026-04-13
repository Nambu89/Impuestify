"""Tests para el detector de fase procesal (12-state automaton)."""
from datetime import datetime, timezone
from app.models.defensia import (
    Tributo, Fase, TipoDocumento, DocumentoEstructurado, ExpedienteEstructurado,
)
from app.services.defensia_phase_detector import detect_fase


def _doc(tipo, fecha, id_="d"):
    return DocumentoEstructurado(
        id=id_,
        nombre_original=f"{id_}.pdf",
        tipo_documento=tipo,
        fecha_acto=datetime.fromisoformat(fecha).replace(tzinfo=timezone.utc),
        datos={},
    )


def _exp(docs):
    return ExpedienteEstructurado(
        id="e1", tributo=Tributo.IRPF, ccaa="Madrid", documentos=docs,
    )


def test_solo_requerimiento_fase_comprobacion_requerimiento():
    exp = _exp([_doc(TipoDocumento.REQUERIMIENTO, "2025-11-03")])
    fase, conf = detect_fase(exp)
    assert fase == Fase.COMPROBACION_REQUERIMIENTO
    assert conf >= 0.85


def test_propuesta_sin_alegaciones_fase_comprobacion_propuesta():
    exp = _exp([
        _doc(TipoDocumento.REQUERIMIENTO, "2025-11-03", "d1"),
        _doc(TipoDocumento.PROPUESTA_LIQUIDACION, "2025-12-10", "d2"),
    ])
    fase, _ = detect_fase(exp)
    assert fase == Fase.COMPROBACION_PROPUESTA


def test_liquidacion_dictada_fase_liquidacion_firme():
    exp = _exp([
        _doc(TipoDocumento.PROPUESTA_LIQUIDACION, "2025-12-10", "d1"),
        _doc(TipoDocumento.ESCRITO_ALEGACIONES_USUARIO, "2025-12-22", "d2"),
        _doc(TipoDocumento.LIQUIDACION_PROVISIONAL, "2026-01-30", "d3"),
    ])
    fase, _ = detect_fase(exp)
    assert fase == Fase.LIQUIDACION_FIRME_PLAZO_RECURSO


def test_reclamacion_tear_presentada_fase_tear_ampliacion_posible():
    exp = _exp([
        _doc(TipoDocumento.LIQUIDACION_PROVISIONAL, "2026-01-30", "d1"),
        _doc(TipoDocumento.ESCRITO_RECLAMACION_TEAR_USUARIO, "2026-02-01", "d2"),
    ])
    fase, _ = detect_fase(exp)
    assert fase == Fase.TEAR_AMPLIACION_POSIBLE


def test_acuerdo_sancion_fase_sancionador_impuesta():
    exp = _exp([
        _doc(TipoDocumento.ACUERDO_INICIO_SANCIONADOR, "2026-02-02", "d1"),
        _doc(TipoDocumento.ACUERDO_IMPOSICION_SANCION, "2026-04-07", "d2"),
    ])
    fase, _ = detect_fase(exp)
    assert fase == Fase.SANCIONADOR_IMPUESTA


def test_acta_inspeccion_fuera_de_alcance():
    exp = _exp([_doc(TipoDocumento.ACTA_INSPECCION, "2026-03-01")])
    fase, _ = detect_fase(exp)
    assert fase == Fase.FUERA_DE_ALCANCE


def test_providencia_apremio_fuera_de_alcance():
    exp = _exp([_doc(TipoDocumento.PROVIDENCIA_APREMIO, "2026-03-01")])
    fase, _ = detect_fase(exp)
    assert fase == Fase.FUERA_DE_ALCANCE


def test_expediente_vacio_indeterminada():
    exp = _exp([])
    fase, conf = detect_fase(exp)
    assert fase == Fase.INDETERMINADA
    assert conf == 0.0
