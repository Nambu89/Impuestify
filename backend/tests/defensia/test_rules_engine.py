"""Tests para el motor de reglas deterministas."""
from app.models.defensia import (
    ExpedienteEstructurado, Tributo, Fase,
    Brief, ArgumentoCandidato,
)
from app.services.defensia_rules_engine import regla, evaluar, REGISTRY, reset_registry


def _exp_basico():
    return ExpedienteEstructurado(
        id="e1", tributo=Tributo.IRPF, ccaa="Madrid",
        documentos=[],
        fase_detectada=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        fase_confianza=0.9,
    )


def test_registry_vacio_devuelve_lista_vacia():
    reset_registry()
    candidatos = evaluar(_exp_basico(), Brief(texto="test"))
    assert candidatos == []


def test_decorador_registra_regla():
    reset_registry()

    @regla(
        id="R_TEST_001",
        tributos=["IRPF"],
        fases=["LIQUIDACION_FIRME_PLAZO_RECURSO"],
        descripcion="Test rule",
    )
    def _r(expediente, brief):
        return ArgumentoCandidato(
            regla_id="R_TEST_001",
            descripcion="Disparada",
            cita_normativa_propuesta="Art. 1 LGT",
            datos_disparo={},
        )

    assert "R_TEST_001" in REGISTRY
    candidatos = evaluar(_exp_basico(), Brief(texto="test"))
    assert len(candidatos) == 1
    assert candidatos[0].regla_id == "R_TEST_001"


def test_evaluar_filtra_por_tributo():
    reset_registry()

    @regla(
        id="R_IVA",
        tributos=["IVA"],
        fases=["LIQUIDACION_FIRME_PLAZO_RECURSO"],
        descripcion="solo IVA",
    )
    def _r(expediente, brief):
        return ArgumentoCandidato(
            regla_id="R_IVA",
            descripcion="x",
            cita_normativa_propuesta="x",
            datos_disparo={},
        )

    candidatos = evaluar(_exp_basico(), Brief(texto="test"))
    assert candidatos == []


def test_evaluar_filtra_por_fase():
    reset_registry()

    @regla(
        id="R_TEAR",
        tributos=["IRPF"],
        fases=["TEAR_INTERPUESTA"],
        descripcion="solo TEAR",
    )
    def _r(expediente, brief):
        return ArgumentoCandidato(
            regla_id="R_TEAR",
            descripcion="x",
            cita_normativa_propuesta="x",
            datos_disparo={},
        )

    candidatos = evaluar(_exp_basico(), Brief(texto="test"))
    assert candidatos == []


def test_regla_que_retorna_none_no_se_incluye():
    reset_registry()

    @regla(
        id="R_NONE",
        tributos=["IRPF"],
        fases=["LIQUIDACION_FIRME_PLAZO_RECURSO"],
        descripcion="no dispara",
    )
    def _r(expediente, brief):
        return None

    candidatos = evaluar(_exp_basico(), Brief(texto="test"))
    assert candidatos == []


def test_regla_que_falla_con_excepcion_no_tumba_pipeline():
    """Una regla defectuosa no debe romper la evaluación de las demás."""
    reset_registry()

    @regla(
        id="R_FALLA",
        tributos=["IRPF"],
        fases=["LIQUIDACION_FIRME_PLAZO_RECURSO"],
        descripcion="falla",
    )
    def _bad(expediente, brief):
        raise RuntimeError("boom")

    @regla(
        id="R_OK",
        tributos=["IRPF"],
        fases=["LIQUIDACION_FIRME_PLAZO_RECURSO"],
        descripcion="ok",
    )
    def _good(expediente, brief):
        return ArgumentoCandidato(
            regla_id="R_OK",
            descripcion="x",
            cita_normativa_propuesta="x",
            datos_disparo={},
        )

    candidatos = evaluar(_exp_basico(), Brief(texto="test"))
    assert len(candidatos) == 1
    assert candidatos[0].regla_id == "R_OK"
