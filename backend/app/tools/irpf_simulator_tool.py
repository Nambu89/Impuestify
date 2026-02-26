"""
IRPF Simulator Tool for TaxIA.

Provides function calling capability for the LLM to run a complete
IRPF simulation with multiple income types and MPYF calculation.

This is the enhanced version of calculate_irpf that handles:
- Work income deductions (SS, otros gastos, reducción trabajo)
- Savings income with separate ahorro tax scale
- Rental income with amortization and housing reduction
- Personal and family minimum (MPYF) by CCAA
"""
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# Tool definition for OpenAI function calling
IRPF_SIMULATOR_TOOL = {
    "type": "function",
    "function": {
        "name": "simulate_irpf",
        "description": """Simulación completa de IRPF. Usa SIEMPRE esta función cuando el usuario
quiera saber cuánto paga de IRPF, cuánto le sale la renta, o una estimación de su declaración.

Acepta múltiples tipos de renta (trabajo, alquiler, ahorro) y situación familiar
para calcular automáticamente el Mínimo Personal y Familiar (MPYF) por CCAA.

OBLIGATORIO usar esta función si el usuario menciona:
- Ingresos anuales o mensuales (ej: "gano 30.000€", "cobro 2.500€/mes")
- Cualquier pregunta sobre cuánto paga de IRPF o retención
- Declaración de la renta

El tool calcula automáticamente:
- Gastos deducibles del trabajo (SS, otros gastos 2.000€)
- Reducción por rendimientos del trabajo (art. 20)
- Base imponible general y del ahorro
- Tarifa progresiva general + tarifa del ahorro
- MPYF según CCAA y situación familiar
- Cuota líquida final

IMPORTANTE sobre ingresos:
- Si el usuario dice "gano X€ al mes" → multiplica por 14 (12 meses + 2 pagas extra) o por 12 si dice "al mes neto"
- Si dice "mi salario bruto es X€" → usar directamente como ingresos_trabajo
- SIEMPRE pregunta la CCAA si no la conoces""",
        "parameters": {
            "type": "object",
            "properties": {
                "comunidad_autonoma": {
                    "type": "string",
                    "description": "Comunidad autónoma del contribuyente. Afecta escala autonómica y MPYF."
                },
                "year": {
                    "type": "integer",
                    "description": "Año fiscal (default 2024)"
                },
                "ingresos_trabajo": {
                    "type": "number",
                    "description": "Ingresos brutos anuales del trabajo (salario bruto anual)"
                },
                "ss_empleado": {
                    "type": "number",
                    "description": "SS pagada por el empleado en el año. Si 0 o no se indica, se estima automáticamente (~6.35% del bruto)"
                },
                "intereses": {
                    "type": "number",
                    "description": "Intereses de cuentas/depósitos cobrados en el año"
                },
                "dividendos": {
                    "type": "number",
                    "description": "Dividendos cobrados en el año"
                },
                "ganancias_fondos": {
                    "type": "number",
                    "description": "Ganancias por venta/reembolso de fondos de inversión"
                },
                "ingresos_alquiler": {
                    "type": "number",
                    "description": "Ingresos anuales por alquiler de inmuebles"
                },
                "gastos_alquiler_total": {
                    "type": "number",
                    "description": "Gastos deducibles totales del alquiler (comunidad, seguros, IBI, reparaciones...)"
                },
                "valor_adquisicion_inmueble": {
                    "type": "number",
                    "description": "Valor de adquisición del inmueble alquilado (para calcular amortización al 3%)"
                },
                "edad_contribuyente": {
                    "type": "integer",
                    "description": "Edad del contribuyente. >65 y >75 aumentan el mínimo personal. Default: 35"
                },
                "num_descendientes": {
                    "type": "integer",
                    "description": "Número de hijos/descendientes a cargo. 0 si no tiene."
                },
                "anios_nacimiento_desc": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Años de nacimiento de cada hijo [2022, 2019]. Hijos <3 años suman 2.800€ extra."
                },
                "custodia_compartida": {
                    "type": "boolean",
                    "description": "true si custodia compartida → mínimos descendientes /2"
                },
                "num_ascendientes_65": {
                    "type": "integer",
                    "description": "Ascendientes a cargo mayores de 65 años"
                },
                "num_ascendientes_75": {
                    "type": "integer",
                    "description": "Ascendientes a cargo mayores de 75 años"
                },
                "discapacidad_contribuyente": {
                    "type": "integer",
                    "description": "Porcentaje de discapacidad del contribuyente (0, 33, 65...)"
                }
            },
            "required": ["comunidad_autonoma", "ingresos_trabajo"]
        }
    }
}


async def simulate_irpf_tool(
    comunidad_autonoma: str,
    ingresos_trabajo: float,
    year: int = 2024,
    ss_empleado: float = 0,
    intereses: float = 0,
    dividendos: float = 0,
    ganancias_fondos: float = 0,
    ingresos_alquiler: float = 0,
    gastos_alquiler_total: float = 0,
    valor_adquisicion_inmueble: float = 0,
    edad_contribuyente: int = 35,
    num_descendientes: int = 0,
    anios_nacimiento_desc: Optional[List[int]] = None,
    custodia_compartida: bool = False,
    num_ascendientes_65: int = 0,
    num_ascendientes_75: int = 0,
    discapacidad_contribuyente: int = 0,
) -> Dict[str, Any]:
    """Execute IRPF simulation and return formatted result."""
    try:
        from app.utils.irpf_simulator import IRPFSimulator
        from app.tools.web_scraper_tool import normalize_ccaa_name
        from app.database.turso_client import get_db_client

        db = await get_db_client()
        ccaa = normalize_ccaa_name(comunidad_autonoma)

        logger.info(
            "Simulating IRPF: %s€ trabajo, %s, %s",
            ingresos_trabajo, ccaa, year,
        )

        simulator = IRPFSimulator(db)
        result = await simulator.simulate(
            jurisdiction=ccaa,
            year=year,
            ingresos_trabajo=ingresos_trabajo,
            ss_empleado=ss_empleado,
            intereses=intereses,
            dividendos=dividendos,
            ganancias_fondos=ganancias_fondos,
            ingresos_alquiler=ingresos_alquiler,
            gastos_alquiler_total=gastos_alquiler_total,
            valor_adquisicion_inmueble=valor_adquisicion_inmueble,
            edad_contribuyente=edad_contribuyente,
            num_descendientes=num_descendientes,
            anios_nacimiento_desc=anios_nacimiento_desc,
            custodia_compartida=custodia_compartida,
            num_ascendientes_65=num_ascendientes_65,
            num_ascendientes_75=num_ascendientes_75,
            discapacidad_contribuyente=discapacidad_contribuyente,
        )

        # Build formatted response
        result["formatted_response"] = _format_simulation_result(result, ccaa)
        return result

    except ValueError as e:
        logger.warning("IRPF simulation failed: %s", e)
        return {
            "success": False,
            "error": str(e),
            "formatted_response": (
                f"No se pudo simular el IRPF para {comunidad_autonoma} en {year}. "
                f"Error: {e}. Puede que no haya datos de tramos para esa CCAA/año."
            ),
        }
    except Exception as e:
        logger.error("IRPF simulation error: %s", e, exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "formatted_response": f"Error al simular IRPF: {e}",
        }


def _format_simulation_result(result: Dict, ccaa: str) -> str:
    """Format simulation result as user-friendly text for the LLM."""
    year = result["year"]
    trabajo = result.get("trabajo", {})
    mpyf = result.get("mpyf", {})

    lines = [
        f"Simulación IRPF {year} — {ccaa}",
    ]

    # Work income
    if trabajo.get("ingresos_brutos", 0) > 0:
        lines.append(
            f"Rendimiento del trabajo: {trabajo['ingresos_brutos']:,.2f}€ brutos "
            f"→ {trabajo['rendimiento_neto_reducido']:,.2f}€ neto reducido "
            f"(gastos deducibles: {trabajo['gastos_deducibles']:,.2f}€, "
            f"reducción trabajo: {trabajo['reduccion_trabajo']:,.2f}€)"
        )

    # Rental income
    inmuebles = result.get("inmuebles")
    if inmuebles:
        lines.append(
            f"Rendimiento inmobiliario: {inmuebles['ingresos_alquiler']:,.2f}€ ingresos "
            f"→ {inmuebles['rendimiento_neto_reducido']:,.2f}€ neto reducido "
            f"(reducción vivienda: {inmuebles['reduccion_vivienda']:,.2f}€)"
        )

    # Tax bases
    lines.append(
        f"Base imponible general: {result['base_imponible_general']:,.2f}€"
    )
    if result.get("base_imponible_ahorro", 0) > 0:
        lines.append(
            f"Base imponible del ahorro: {result['base_imponible_ahorro']:,.2f}€"
        )

    # Cuota íntegra
    lines.append(
        f"Cuota íntegra general: {result['cuota_integra_general']:,.2f}€ "
        f"(estatal: {result['cuota_integra_estatal']:,.2f}€ + "
        f"autonómica: {result['cuota_integra_autonomica']:,.2f}€)"
    )

    # MPYF
    lines.append(
        f"Mínimo personal y familiar: estatal {mpyf.get('mpyf_estatal', 0):,.2f}€ / "
        f"autonómico {mpyf.get('mpyf_autonomico', 0):,.2f}€ "
        f"→ reducción cuota: {result['cuota_mpyf_estatal']:,.2f}€ + {result['cuota_mpyf_autonomica']:,.2f}€"
    )

    # Cuota líquida
    lines.append(
        f"Cuota líquida general: {result['cuota_liquida_general']:,.2f}€"
    )
    if result.get("cuota_ahorro", 0) > 0:
        lines.append(f"Cuota del ahorro: {result['cuota_ahorro']:,.2f}€")

    lines.append(
        f"CUOTA TOTAL: {result['cuota_total']:,.2f}€ "
        f"(tipo medio efectivo: {result['tipo_medio']:.2f}%)"
    )

    return "\n".join(lines)
