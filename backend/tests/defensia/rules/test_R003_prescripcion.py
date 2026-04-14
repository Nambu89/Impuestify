"""Tests de la regla R003 — prescripcion_4_anos (T1B-003).

Base normativa: arts. 66.a y 67.1 LGT + computo "de fecha a fecha" (doctrina TS).

La regla dispara cuando la AEAT notifica el inicio de actuaciones cuando ya han
transcurrido mas de 4 anos desde el fin del plazo voluntario de declaracion
(IRPF: 30 de junio del ano siguiente al ejercicio) y NO hubo interrupcion.

Absorbe el sub-caso "calculo de plazos" (R008 del plan v1 descartada).
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.models.defensia import (
    ArgumentoCandidato,
    Fase,
    TipoDocumento,
    Tributo,
)
from app.services.defensia_rules.reglas_procedimentales import R003_prescripcion


# ---------------------------------------------------------------------------
# Positivos
# ---------------------------------------------------------------------------

def test_r003_positivo_mas_de_4_anos_desde_plazo_voluntario(
    build_exp, build_doc, build_brief
):
    """Ejercicio 2020, notificacion 2025-08-01.

    Fin plazo voluntario IRPF 2020 = 2021-06-30.
    2025-08-01 - 2021-06-30 = ~4 anos 1 mes > 4 anos -> dispara.
    """
    doc_aeat = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={"ejercicio": 2020},
        fecha_acto=datetime(2025, 8, 1, tzinfo=timezone.utc),
        doc_id="liq-2020",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc_aeat],
    )
    brief = build_brief("AEAT me reclama 2020 pero ya prescribio")

    resultado = R003_prescripcion.evaluar(exp, brief)

    assert resultado is not None
    assert isinstance(resultado, ArgumentoCandidato)
    assert resultado.regla_id == "R003"
    # Cita semantica, NO hardcodeada con todas las letras del texto canonico
    assert "prescripcion" in resultado.cita_normativa_propuesta.lower()
    assert "dias_transcurridos" in resultado.datos_disparo
    assert resultado.datos_disparo["dias_transcurridos"] > 4 * 365


def test_r003_positivo_limite_exacto_mas_un_dia(
    build_exp, build_doc, build_brief
):
    """Limite exacto: fin plazo 2021-06-30, notificacion 2025-07-01.

    4 anos y 1 dia -> dispara (doctrina TS fecha a fecha).
    """
    doc_aeat = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={"ejercicio": 2020},
        fecha_acto=datetime(2025, 7, 1, tzinfo=timezone.utc),
        doc_id="liq-2020-lim",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc_aeat],
    )
    brief = build_brief("")

    resultado = R003_prescripcion.evaluar(exp, brief)

    assert resultado is not None
    assert resultado.regla_id == "R003"


# ---------------------------------------------------------------------------
# Negativos
# ---------------------------------------------------------------------------

def test_r003_negativo_limite_exacto_no_dispara(
    build_exp, build_doc, build_brief
):
    """Fin plazo 2021-06-30, notificacion 2025-06-30.

    Exactamente 4 anos -> NO dispara (dentro del plazo, doctrina fecha a fecha).
    """
    doc_aeat = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={"ejercicio": 2020},
        fecha_acto=datetime(2025, 6, 30, tzinfo=timezone.utc),
        doc_id="liq-2020-justo",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc_aeat],
    )
    brief = build_brief("")

    resultado = R003_prescripcion.evaluar(exp, brief)

    assert resultado is None


def test_r003_negativo_dentro_de_plazo(
    build_exp, build_doc, build_brief
):
    """Ejercicio 2023, notificacion 2026-02-01 -> claramente dentro de plazo."""
    doc_aeat = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={"ejercicio": 2023},
        fecha_acto=datetime(2026, 2, 1, tzinfo=timezone.utc),
        doc_id="liq-2023",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc_aeat],
    )
    brief = build_brief("")

    resultado = R003_prescripcion.evaluar(exp, brief)

    assert resultado is None


def test_r003_negativo_interrupcion_previa(
    build_exp, build_doc, build_brief
):
    """Hubo un requerimiento interruptivo dentro de los 4 anos.

    Ejercicio 2020 (fin plazo 2021-06-30), requerimiento 2024-05-01 (interrumpe,
    dentro del plazo de 4 anos) y liquidacion 2026-01-15 (pasada la ventana
    original pero la interrupcion resetea el computo) -> NO dispara.
    """
    doc_requerimiento = build_doc(
        TipoDocumento.REQUERIMIENTO,
        datos={"ejercicio": 2020},
        fecha_acto=datetime(2024, 5, 1, tzinfo=timezone.utc),
        doc_id="req-2024",
    )
    doc_liquidacion = build_doc(
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        datos={"ejercicio": 2020},
        fecha_acto=datetime(2026, 1, 15, tzinfo=timezone.utc),
        doc_id="liq-2026",
    )
    exp = build_exp(
        tributo=Tributo.IRPF,
        fase=Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        docs=[doc_requerimiento, doc_liquidacion],
    )
    brief = build_brief("")

    resultado = R003_prescripcion.evaluar(exp, brief)

    assert resultado is None
