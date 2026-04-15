"""Integration test del RAG verifier con el caso David Oliva (T2B-003).

El caso David es el ground truth del producto DefensIA (ver
`memory/project_session32_defensia_part1.md`). Este test construye un
expediente sintetico que fuerza el disparo de las 5 reglas obligatorias
del caso (R001, R004, R007, R011, R012), pasa los candidatos por el RAG
verifier con un retriever mockeado "inteligente" y comprueba que las 5
sobreviven al umbral de 0.7.

El retriever mock devuelve similarities altas (>= 0.85) cuando la query
contiene palabras clave asociadas a cada una de las 5 reglas, y baja
(<= 0.3) en otro caso. Esto imita el comportamiento esperado del corpus
RAG real cuando encuentra una cita canonica para la cita semantica libre
que produce cada regla.

Spec: plans/2026-04-13-defensia-implementation-plan-part2.md §T2B-003
"""
from __future__ import annotations

import importlib
import sys
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

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
from app.services import defensia_rules
from app.services.defensia_rag_verifier import CONFIANZA_MIN, DefensiaRagVerifier
from app.services.defensia_rules_engine import REGISTRY, evaluar, reset_registry


def _forzar_recarga_reglas() -> None:
    """Recarga todas las reglas R0NN_*.py forzando re-ejecucion del decorador.

    ``defensia_rules.load_all()`` usa ``importlib.import_module``, que es un
    no-op si el modulo ya esta en ``sys.modules`` — no re-ejecuta el cuerpo
    del modulo y por tanto el decorador ``@regla`` no vuelve a poblar el
    REGISTRY tras un ``reset_registry()``. Este helper fuerza el reimport
    real purgando primero ``sys.modules`` y luego llamando a ``load_all()``,
    de modo que el test es estable tanto en modo solo como dentro de la
    suite completa (otros tests de reglas hacen reset y contaminan el orden).
    """
    reset_registry()
    prefijo = "app.services.defensia_rules."
    a_eliminar = [
        nombre for nombre in list(sys.modules)
        if nombre.startswith(prefijo)
        and any(
            f".{sub}." in nombre
            for sub in ("reglas_procedimentales", "reglas_irpf", "reglas_otros_tributos")
        )
    ]
    for nombre in a_eliminar:
        del sys.modules[nombre]
    # Tambien recargamos el paquete raiz para que load_all() vuelva a
    # iterar sobre los subpaquetes vacios en sys.modules.
    importlib.reload(defensia_rules)
    defensia_rules.load_all()


@pytest.fixture(autouse=True)
def _aislar_registry():
    """Fuerza una recarga completa de las reglas antes y limpia despues.

    Esto garantiza que el test es estable independientemente del orden de
    ejecucion con el resto de la suite, y que ``evaluar`` ve las 30 reglas
    reales aunque otro test previo las haya dejado parcialmente cargadas o
    totalmente vacias.
    """
    _forzar_recarga_reglas()
    yield
    reset_registry()


# ---------------------------------------------------------------------------
# Fixture: retriever "inteligente" — similarity por palabras clave
# ---------------------------------------------------------------------------


# Mapa palabra clave -> (similarity, texto, titulo) que el retriever devuelve
# cuando la query contiene esa palabra. Primera coincidencia gana.
_MAPA_CITAS: list[tuple[tuple[str, ...], float, str, str]] = [
    (
        ("motivacion", "fundamentos de derecho"),
        0.92,
        (
            "Los actos de aplicacion de los tributos y de imposicion de sanciones "
            "deberan motivarse con referencia expresa a los hechos y fundamentos "
            "de derecho (art. 102.2.c Ley 58/2003 LGT)."
        ),
        "LGT art. 102 — motivacion de los actos tributarios",
    ),
    (
        ("carga de la prueba", "facilidad probatoria", "carga probatoria"),
        0.90,
        (
            "En los procedimientos de aplicacion de los tributos, quien haga valer "
            "su derecho debera probar los hechos constitutivos del mismo (art. 105.1 LGT)."
        ),
        "LGT art. 105 — carga de la prueba",
    ),
    (
        ("culpabilidad", "interpretacion razonable"),
        0.88,
        (
            "Las acciones u omisiones tipificadas en las leyes no daran lugar a "
            "responsabilidad por infraccion tributaria cuando el obligado actue "
            "amparandose en una interpretacion razonable de la norma (art. 179.2.d LGT)."
        ),
        "LGT art. 179 — principio de culpabilidad tributaria",
    ),
    (
        ("vivienda habitual", "cambio de domicilio", "circunstancias"),
        0.93,
        (
            "Se entendera que la vivienda tiene el caracter de habitual cuando haya "
            "constituido la residencia del contribuyente durante un plazo continuado "
            "de al menos tres anos. No obstante, se considerara que la vivienda tuvo "
            "caracter habitual cuando circunstancias que necesariamente exijan el "
            "cambio de domicilio, tales como separacion matrimonial, impidan el "
            "cumplimiento del plazo (art. 41 bis RIRPF, RD 439/2007)."
        ),
        "RIRPF art. 41 bis — vivienda habitual",
    ),
    (
        ("anualidades por alimentos", "escalas separadas"),
        0.89,
        (
            "Los contribuyentes que satisfagan anualidades por alimentos a favor "
            "de sus hijos por decision judicial aplicaran las escalas de gravamen "
            "de forma separada sobre el importe de las anualidades y sobre el "
            "resto de la base liquidable general (arts. 64 y 75 LIRPF, Ley 35/2006)."
        ),
        "LIRPF arts. 64 y 75 — anualidades por alimentos",
    ),
]


def _retriever_inteligente() -> MagicMock:
    """Retriever mock que resuelve similarities por palabras clave en la query."""

    async def _search(query: str, query_embedding=None, k: int = 5, territory_filter=None):
        texto = (query or "").lower()
        for palabras, sim, contenido, titulo in _MAPA_CITAS:
            if any(p in texto for p in palabras):
                return [
                    {
                        "id": f"chunk-{titulo[:10]}",
                        "text": contenido,
                        "page": 1,
                        "source": "legislacion_tributaria",
                        "title": titulo,
                        "similarity": sim,
                        "territory": "AEAT",
                        "tax_type": "",
                    }
                ]
        # Nada reconocido — devolvemos un chunk con similarity por debajo del umbral.
        return [
            {
                "id": "chunk-nomatch",
                "text": "(sin match relevante en el corpus)",
                "page": 0,
                "source": "",
                "title": "",
                "similarity": 0.25,
                "territory": "",
                "tax_type": "",
            }
        ]

    retriever = MagicMock()
    retriever.search = AsyncMock(side_effect=_search)
    return retriever


# ---------------------------------------------------------------------------
# Fixture: expediente sintetico caso David que dispara R001/R004/R007/R011/R012
# ---------------------------------------------------------------------------


def _doc(
    doc_id: str,
    tipo: TipoDocumento,
    *,
    datos: dict[str, Any],
    fecha_acto: datetime | None = None,
    nombre: str = "doc.pdf",
) -> DocumentoEstructurado:
    return DocumentoEstructurado(
        id=doc_id,
        nombre_original=nombre,
        tipo_documento=tipo,
        fecha_acto=fecha_acto,
        datos=datos,
        clasificacion_confianza=0.95,
    )


def _expediente_caso_david() -> ExpedienteEstructurado:
    """Construye el expediente caso David anonimizado con todos los campos
    necesarios para que disparen R001, R004, R007, R011 y R012.

    El fixture JSON de Parte 1 (`caso_david/expediente_anonimizado.json`) no
    tiene las flags que R001/R004/R007/R011/R012 necesitan para disparar, asi
    que generamos uno sintetico aqui mismo — el prompt T2B-003 lo permite
    explicitamente.
    """
    # Requerimiento AEAT — antecede la liquidacion (necesario para que R004
    # entre por el patron "aportada_sin_motivar_insuficiencia").
    requerimiento = _doc(
        "d01-req",
        TipoDocumento.REQUERIMIENTO,
        fecha_acto=datetime(2025, 11, 3, tzinfo=timezone.utc),
        datos={
            "plazo_aportar_docs_dias": 10,
            "tipo_procedimiento": "comprobacion_limitada",
            "alcance": "ganancia patrimonial transmision inmueble",
            "tiene_fundamentos_derecho": True,
        },
    )

    # Escritura vivienda habitual — adq 2024-01-10 -> trans 2025-10-15
    # (~1 ano y 9 meses, inferior a 3 anos -> R011 dispara).
    escritura = _doc(
        "d02-esc",
        TipoDocumento.ESCRITURA,
        fecha_acto=datetime(2024, 1, 10, tzinfo=timezone.utc),
        datos={
            "es_vivienda_habitual": True,
            "fecha_adquisicion": "2024-01-10",
            "fecha_transmision": "2025-10-15",
        },
    )

    # Sentencia judicial de modificacion de medidas — causa separacion
    # matrimonial + incluye anualidades por alimentos. Dispara R011 y R012.
    sentencia = _doc(
        "d03-sent",
        TipoDocumento.SENTENCIA_JUDICIAL,
        fecha_acto=datetime(2025, 6, 28, tzinfo=timezone.utc),
        datos={
            "modifica_medidas_familiares": True,
            "causa": "separacion_matrimonial",
            "incluye_anualidades_alimentos": True,
            "fecha_sentencia": "2025-06-28",
        },
    )

    # Liquidacion provisional — deniega exencion por reinversion por plazo
    # de 3 anos incumplido (R011), NO aplica escalas separadas (R012),
    # deniega beneficio fiscal sin motivar (R004) y carece de fundamentos
    # de derecho (R001).
    liquidacion = _doc(
        "d04-liq",
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        fecha_acto=datetime(2026, 1, 30, tzinfo=timezone.utc),
        datos={
            "cuota": 6183.05,
            "ejercicio": 2024,
            "ccaa": "Madrid",
            "tipo_tributo": "IRPF",
            "plazo_recurso_dias": 30,
            # R001 — sin fundamentos de derecho.
            "tiene_fundamentos_derecho": False,
            # R004 — deniega beneficio fiscal con documentacion aportada pero
            # sin motivar la insuficiencia probatoria.
            "deniega_beneficio_fiscal": True,
            "concepto_denegado": "exencion por reinversion en vivienda habitual",
            "documentacion_aportada": True,
            "motivacion_insuficiencia_prueba": False,
            # R011 — deniega exencion por incumplimiento del plazo de 3 anos.
            "deniega_exencion_reinversion": True,
            "motivo_denegacion": "residencia_inferior_3_anos",
            # R012 — no aplica escalas separadas sobre las anualidades.
            "aplica_escalas_separadas": False,
            "progenitor_no_custodio": True,
        },
    )

    # Acuerdo de imposicion de sancion — motivacion generica de culpabilidad
    # y sin analisis de interpretacion razonable (R007 dispara).
    sancion = _doc(
        "d05-sanc",
        TipoDocumento.ACUERDO_IMPOSICION_SANCION,
        fecha_acto=datetime(2026, 4, 7, tzinfo=timezone.utc),
        datos={
            "importe_sancion": 3393.52,
            "articulos_tipicos": ["Art. 191 LGT"],
            "motivacion_culpabilidad_generica": True,
            "razonamiento_por_exclusion": False,
            "analisis_interpretacion_razonable": False,
            "tiene_fundamentos_derecho": True,
        },
    )

    return ExpedienteEstructurado(
        id="exp-caso-david",
        tributo=Tributo.IRPF,
        ccaa="Madrid",
        documentos=[requerimiento, escritura, sentencia, liquidacion, sancion],
        fase_detectada=Fase.SANCIONADOR_IMPUESTA,
        fase_confianza=0.95,
    )


# ---------------------------------------------------------------------------
# Test principal: rules engine -> RAG verifier -> 5 reglas sobreviven
# ---------------------------------------------------------------------------


async def test_caso_david_5_reglas_sobreviven_verificador():
    """Pipeline real (rules engine + RAG verifier mock) con el caso David.

    Las 5 reglas obligatorias del caso (R001, R004, R007, R011, R012) deben
    estar presentes en `verificados` tras pasar el umbral de 0.7.
    """
    # 1. Las reglas ya estan cargadas en el REGISTRY por el fixture autouse
    #    `_aislar_registry` (que fuerza recarga limpia para evitar contaminacion
    #    entre tests). Sanity check defensivo:
    assert len(REGISTRY) >= 5, (
        f"REGISTRY solo tiene {len(REGISTRY)} reglas — se esperaba >= 5 tras "
        f"la recarga forzada del fixture autouse."
    )

    # 2. Construir expediente sintetico + brief del usuario.
    expediente = _expediente_caso_david()
    brief = Brief(
        texto=(
            "Quiero defender la exencion por reinversion en vivienda habitual: "
            "me separe por sentencia antes de cumplir los 3 anos, tenia "
            "anualidades por alimentos a mis hijos y la AEAT no aplica las "
            "escalas separadas. Ademas la sancion me parece infundada, "
            "mi interpretacion era razonable."
        ),
    )

    # 3. Ejecutar el motor de reglas sobre el expediente.
    candidatos = evaluar(expediente, brief)
    ids_candidatos = {c.regla_id for c in candidatos}

    # Sanity: las 5 reglas obligatorias deben haber disparado antes de RAG.
    obligatorias = {"R001", "R004", "R007", "R011", "R012"}
    assert obligatorias.issubset(ids_candidatos), (
        f"El expediente sintetico no dispara las 5 obligatorias: "
        f"faltan {obligatorias - ids_candidatos}, disparadas {ids_candidatos}"
    )

    # 4. RAG verifier con retriever inteligente.
    retriever = _retriever_inteligente()
    verifier = DefensiaRagVerifier(retriever=retriever, db_client=None)

    verificados = await verifier.verify_all(candidatos)

    # 5. Asercion: las 5 obligatorias sobreviven al umbral.
    ids_verificados = {a.regla_id for a in verificados}
    obligatorias_vivas = [a for a in verificados if a.regla_id in obligatorias]
    assert len(obligatorias_vivas) == 5, (
        f"Solo sobreviven {len(obligatorias_vivas)} de 5 reglas obligatorias. "
        f"Sobrevivientes totales: {ids_verificados}"
    )

    # 6. Invariante dura del producto: todo sobreviviente esta sobre el umbral.
    assert all(isinstance(a, ArgumentoVerificado) for a in verificados)
    assert all(a.confianza >= CONFIANZA_MIN for a in verificados)

    # 7. La cita canonica resuelta debe venir del RAG (no hardcoded en la regla).
    for arg in obligatorias_vivas:
        assert arg.referencia_normativa_canonica, (
            f"R{arg.regla_id} no tiene referencia canonica tras verificacion"
        )
        assert arg.cita_verificada, (
            f"R{arg.regla_id} no tiene cita verificada tras RAG"
        )
