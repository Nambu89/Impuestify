"""
Joint vs Individual IRPF Comparison Tool.

Calcula 2 escenarios (declaracion conjunta matrimonio vs declaraciones
individuales) y recomienda la opcion mas favorable.

El tool llama a IRPFSimulator.simulate() como usuario externo, sin
modificar ninguna logica interna del simulador.
"""
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool definition for OpenAI function calling
# ---------------------------------------------------------------------------

JOINT_COMPARISON_TOOL = {
    "type": "function",
    "function": {
        "name": "compare_joint_individual",
        "description": (
            "Compara declaracion conjunta vs individual para un matrimonio. "
            "Calcula ambos escenarios con los ingresos del declarante y del "
            "conyuge y recomienda la opcion mas favorable. "
            "Usar cuando el usuario pregunte '¿nos conviene hacer la renta juntos?', "
            "'conjunta o separada', '¿merece la pena declarar juntos?', etc."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ingresos_declarante": {
                    "type": "number",
                    "description": "Ingresos brutos anuales del declarante principal (trabajo, actividad...)"
                },
                "ingresos_conyuge": {
                    "type": "number",
                    "description": "Ingresos brutos anuales del conyuge/pareja"
                },
                "ccaa": {
                    "type": "string",
                    "description": "CCAA de residencia (ej: Madrid, Cataluna, Andalucia)"
                },
                "num_descendientes": {
                    "type": "integer",
                    "description": "Numero de hijos/descendientes a cargo. Default 0.",
                    "default": 0
                },
                "num_descendientes_menores_3": {
                    "type": "integer",
                    "description": "Hijos menores de 3 anos (para deduccion maternidad). Default 0.",
                    "default": 0
                },
                "edad_declarante": {
                    "type": "integer",
                    "description": "Edad del declarante principal. Default 35.",
                    "default": 35
                },
                "aportaciones_plan_pensiones": {
                    "type": "number",
                    "description": "Aportaciones anuales a planes de pensiones del declarante. Default 0.",
                    "default": 0
                },
                "aportaciones_plan_pensiones_conyuge": {
                    "type": "number",
                    "description": "Aportaciones anuales a planes de pensiones del conyuge. Default 0.",
                    "default": 0
                },
                "hipoteca_pre2013": {
                    "type": "boolean",
                    "description": "Tiene hipoteca anterior a 2013. Default false.",
                    "default": False
                },
                "capital_amortizado_hipoteca": {
                    "type": "number",
                    "description": "Capital amortizado de hipoteca en el ano (principal + intereses). Default 0.",
                    "default": 0
                },
                "donativos": {
                    "type": "number",
                    "description": "Donativos a ONGs (Ley 49/2002) del declarante. Default 0.",
                    "default": 0
                },
                "donativos_conyuge": {
                    "type": "number",
                    "description": "Donativos a ONGs del conyuge. Default 0.",
                    "default": 0
                },
                "retenciones_declarante": {
                    "type": "number",
                    "description": "Retenciones IRPF del declarante (aparece en nomina/certificado retenciones). Default 0.",
                    "default": 0
                },
                "retenciones_conyuge": {
                    "type": "number",
                    "description": "Retenciones IRPF del conyuge. Default 0.",
                    "default": 0
                },
                "madre_trabajadora_ss": {
                    "type": "boolean",
                    "description": "La madre es trabajadora con SS (para deduccion maternidad 1200 EUR/hijo). Default false.",
                    "default": False
                }
            },
            "required": ["ingresos_declarante", "ingresos_conyuge", "ccaa"]
        }
    }
}


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------

async def compare_joint_individual_executor(
    ingresos_declarante: float,
    ingresos_conyuge: float,
    ccaa: str,
    num_descendientes: int = 0,
    num_descendientes_menores_3: int = 0,
    edad_declarante: int = 35,
    aportaciones_plan_pensiones: float = 0,
    aportaciones_plan_pensiones_conyuge: float = 0,
    hipoteca_pre2013: bool = False,
    capital_amortizado_hipoteca: float = 0,
    donativos: float = 0,
    donativos_conyuge: float = 0,
    retenciones_declarante: float = 0,
    retenciones_conyuge: float = 0,
    madre_trabajadora_ss: bool = False,
) -> Dict[str, Any]:
    """
    Ejecuta la comparativa conjunta vs individual.

    Calcula hasta 4 escenarios:
      1. Declarante en declaracion individual.
      2. Conyuge en declaracion individual.
      3. Conjunta matrimonio (3.400 EUR reduccion, usando segundo_declarante).
      4. Conjunta monoparental (2.150 EUR reduccion, si aplica).

    Retorna tabla comparativa + recomendacion de la opcion mas favorable.
    """
    from app.utils.irpf_simulator import IRPFSimulator
    from app.utils.ccaa_constants import normalize_ccaa
    from app.database.turso_client import get_db_client

    db = await get_db_client()
    simulator = IRPFSimulator(db)

    jurisdiction = normalize_ccaa(ccaa)

    # Local aliases for clarity inside the function
    aportaciones_pp = float(aportaciones_plan_pensiones)
    aportaciones_pp_conyuge = float(aportaciones_plan_pensiones_conyuge)
    capital_amortizado = float(capital_amortizado_hipoteca)

    # Parametros comunes que no cambian entre escenarios
    base_familiar = dict(
        jurisdiction=jurisdiction,
        year=2024,
        num_descendientes=num_descendientes,
        edad_contribuyente=edad_declarante,
        hipoteca_pre2013=hipoteca_pre2013,
        capital_amortizado_hipoteca=capital_amortizado,
        madre_trabajadora_ss=madre_trabajadora_ss,
        gastos_guarderia_anual=0.0,
    )

    # Build segundo_declarante dict for conjunta scenarios
    segundo_declarante_data = {
        "ingresos_trabajo": ingresos_conyuge,
        "aportaciones_plan_pensiones": aportaciones_pp_conyuge,
        "edad": edad_declarante,  # Assume same age if not specified
    }

    # ------------------------------------------------------------------
    # Escenario 1: Declarante individual
    # ------------------------------------------------------------------
    r_declarante = await simulator.simulate(
        ingresos_trabajo=ingresos_declarante,
        tributacion_conjunta=False,
        aportaciones_plan_pensiones=aportaciones_pp,
        donativos_ley_49_2002=donativos,
        retenciones_trabajo=retenciones_declarante,
        **base_familiar,
    )

    # ------------------------------------------------------------------
    # Escenario 2: Conyuge individual
    # En la declaracion individual del conyuge no aplicamos hipoteca (ya
    # la declara el titular) ni descendientes (ya los declara el declarante).
    # Para la comparativa mas conservadora usamos descendientes=0 para conyuge.
    # Si ambos declaran hijos individualmente, el simulador los duplicaria.
    # ------------------------------------------------------------------
    r_conyuge = await simulator.simulate(
        jurisdiction=jurisdiction,
        year=2024,
        ingresos_trabajo=ingresos_conyuge,
        tributacion_conjunta=False,
        num_descendientes=0,  # hijos ya incluidos en declarante individual
        edad_contribuyente=edad_declarante,
        aportaciones_plan_pensiones=aportaciones_pp_conyuge,
        hipoteca_pre2013=False,  # solo el titular aplica en individual
        donativos_ley_49_2002=donativos_conyuge,
        retenciones_trabajo=retenciones_conyuge,
    )

    # ------------------------------------------------------------------
    # Escenario 3: Conjunta matrimonio (3.400 EUR reduccion)
    # Usa segundo_declarante para calculo real con MPYF de ambos.
    # ------------------------------------------------------------------
    r_conjunta_matrimonio = await simulator.simulate(
        ingresos_trabajo=ingresos_declarante,
        tributacion_conjunta=True,
        tipo_unidad_familiar="matrimonio",
        aportaciones_plan_pensiones=aportaciones_pp,
        donativos_ley_49_2002=donativos + donativos_conyuge,
        retenciones_trabajo=retenciones_declarante + retenciones_conyuge,
        segundo_declarante=segundo_declarante_data,
        **base_familiar,
    )

    # ------------------------------------------------------------------
    # Escenario 4: Conjunta monoparental (2.150 EUR reduccion)
    # Solo aplica a unidades familiares monoparentales (Art. 82.2 LIRPF).
    # Incluido para completitud de la comparativa.
    # ------------------------------------------------------------------
    r_conjunta_monoparental = await simulator.simulate(
        ingresos_trabajo=ingresos_declarante,
        tributacion_conjunta=True,
        tipo_unidad_familiar="monoparental",
        aportaciones_plan_pensiones=aportaciones_pp,
        donativos_ley_49_2002=donativos,
        retenciones_trabajo=retenciones_declarante,
        **base_familiar,
    )

    # ------------------------------------------------------------------
    # Comparativa
    # ------------------------------------------------------------------
    cuota_declarante = r_declarante.get("cuota_diferencial", 0.0)
    cuota_conyuge = r_conyuge.get("cuota_diferencial", 0.0)
    cuota_conjunta_mat = r_conjunta_matrimonio.get("cuota_diferencial", 0.0)
    cuota_conjunta_mono = r_conjunta_monoparental.get("cuota_diferencial", 0.0)

    total_individual = cuota_declarante + cuota_conyuge

    # Find the best option
    opciones = {
        "individual": total_individual,
        "conjunta_matrimonio": cuota_conjunta_mat,
        "conjunta_monoparental": cuota_conjunta_mono,
    }
    recomendacion = min(opciones, key=opciones.get)
    mejor_cuota = opciones[recomendacion]
    ahorro_vs_individual = total_individual - mejor_cuota

    if recomendacion == "individual":
        nota = (
            f"Mejor declarar por separado: las declaraciones individuales "
            f"ahorran {abs(mejor_cuota - min(cuota_conjunta_mat, cuota_conjunta_mono)):.2f} EUR "
            f"respecto a la mejor opcion conjunta."
        )
    elif recomendacion == "conjunta_matrimonio":
        nota = (
            f"La declaracion conjunta (matrimonio) ahorra {ahorro_vs_individual:.2f} EUR "
            f"respecto a dos declaraciones individuales."
        )
    else:
        nota = (
            f"La declaracion conjunta monoparental ahorra {ahorro_vs_individual:.2f} EUR "
            f"respecto a la declaracion individual."
        )

    return {
        "escenario_individual": {
            "declarante": {
                "ingresos": ingresos_declarante,
                "cuota_diferencial": round(cuota_declarante, 2),
                "tipo_efectivo": r_declarante.get("tipo_efectivo_total", 0.0),
            },
            "conyuge": {
                "ingresos": ingresos_conyuge,
                "cuota_diferencial": round(cuota_conyuge, 2),
                "tipo_efectivo": r_conyuge.get("tipo_efectivo_total", 0.0),
            },
            "total_pagar": round(total_individual, 2),
        },
        "escenario_conjunta_matrimonio": {
            "ingresos_conjuntos": ingresos_declarante + ingresos_conyuge,
            "cuota_diferencial": round(cuota_conjunta_mat, 2),
            "tipo_efectivo": r_conjunta_matrimonio.get("tipo_efectivo_total", 0.0),
            "reduccion_aplicada": r_conjunta_matrimonio.get("reduccion_tributacion_conjunta", 3400.0),
            "segundo_declarante": r_conjunta_matrimonio.get("segundo_declarante_desglose"),
        },
        "escenario_conjunta_monoparental": {
            "ingresos_declarante": ingresos_declarante,
            "cuota_diferencial": round(cuota_conjunta_mono, 2),
            "tipo_efectivo": r_conjunta_monoparental.get("tipo_efectivo_total", 0.0),
            "reduccion_aplicada": r_conjunta_monoparental.get("reduccion_tributacion_conjunta", 2150.0),
        },
        # Backwards compatibility: escenario_conjunta = matrimonio
        "escenario_conjunta": {
            "ingresos_conjuntos": ingresos_declarante + ingresos_conyuge,
            "cuota_diferencial": round(cuota_conjunta_mat, 2),
            "tipo_efectivo": r_conjunta_matrimonio.get("tipo_efectivo_total", 0.0),
            "reduccion_aplicada": r_conjunta_matrimonio.get("reduccion_tributacion_conjunta", 3400.0),
        },
        "diferencia": round(cuota_conjunta_mat - total_individual, 2),
        "recomendacion": recomendacion,
        "ahorro": round(abs(ahorro_vs_individual), 2),
        "nota": nota,
    }
