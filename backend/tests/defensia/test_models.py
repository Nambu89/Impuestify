from datetime import datetime, timezone
import pytest
from pydantic import ValidationError
from app.models.defensia import (
    Tributo, Fase, TipoDocumento, EstadoExpediente,
    ExpedienteEstructurado, DocumentoEstructurado, Brief,
    ArgumentoCandidato, ArgumentoVerificado,
)


def test_tributo_enum_values():
    assert Tributo.IRPF.value == "IRPF"
    assert Tributo.IVA.value == "IVA"
    assert Tributo.ISD.value == "ISD"
    assert Tributo.ITP.value == "ITP"
    assert Tributo.PLUSVALIA.value == "PLUSVALIA"
    assert len(Tributo) == 5


def test_fase_enum_all_cases():
    fases = {f.value for f in Fase}
    assert "COMPROBACION_REQUERIMIENTO" in fases
    assert "LIQUIDACION_FIRME_PLAZO_RECURSO" in fases
    assert "SANCIONADOR_IMPUESTA" in fases
    assert "TEAR_AMPLIACION_POSIBLE" in fases
    assert "FUERA_DE_ALCANCE" in fases
    assert "INDETERMINADA" in fases
    assert len(Fase) == 12


def test_documento_estructurado_requires_tipo_y_fecha():
    doc = DocumentoEstructurado(
        id="d1",
        nombre_original="notif.pdf",
        tipo_documento=TipoDocumento.LIQUIDACION_PROVISIONAL,
        fecha_acto=datetime(2026, 1, 30, tzinfo=timezone.utc),
        datos={"referencia": "202410049560746N", "cuota": 6183.05},
    )
    assert doc.tipo_documento == TipoDocumento.LIQUIDACION_PROVISIONAL
    assert doc.datos["cuota"] == 6183.05


def test_expediente_estructurado_timeline_orden_por_fecha():
    docs = [
        DocumentoEstructurado(
            id="d2",
            nombre_original="liq.pdf",
            tipo_documento=TipoDocumento.LIQUIDACION_PROVISIONAL,
            fecha_acto=datetime(2026, 1, 30, tzinfo=timezone.utc),
            datos={},
        ),
        DocumentoEstructurado(
            id="d1",
            nombre_original="req.pdf",
            tipo_documento=TipoDocumento.REQUERIMIENTO,
            fecha_acto=datetime(2025, 11, 3, tzinfo=timezone.utc),
            datos={},
        ),
    ]
    exp = ExpedienteEstructurado(
        id="e1",
        tributo=Tributo.IRPF,
        ccaa="Madrid",
        documentos=docs,
        fase_detectada=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        fase_confianza=0.9,
    )
    timeline = exp.timeline_ordenado()
    assert timeline[0].id == "d1"
    assert timeline[1].id == "d2"


def test_argumento_candidato_valida_impacto_estimado_opcional():
    arg = ArgumentoCandidato(
        regla_id="R001",
        descripcion="Falta motivación",
        cita_normativa_propuesta="Art. 102 LGT",
        datos_disparo={"campo": "motivacion", "valor": None},
    )
    assert arg.impacto_estimado is None


def test_argumento_verificado_requiere_cita_exacta():
    arg = ArgumentoVerificado(
        regla_id="R001",
        descripcion="Falta motivación",
        cita_verificada="Artículo 102. Notificación de las liquidaciones...",
        referencia_normativa_canonica="Art. 102 LGT",
        confianza=0.9,
        datos_disparo={"campo": "motivacion"},
    )
    assert arg.confianza >= 0.7

    # Validate upper bound enforcement
    with pytest.raises(ValidationError):
        ArgumentoVerificado(
            regla_id="R001",
            descripcion="x",
            cita_verificada="x",
            referencia_normativa_canonica="x",
            confianza=1.5,
            datos_disparo={},
        )
