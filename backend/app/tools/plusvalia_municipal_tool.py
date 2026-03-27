"""
Plusvalia Municipal Tool for TaxIA

Provides function calling capability for the LLM to calculate the
Impuesto sobre el Incremento de Valor de los Terrenos de Naturaleza Urbana
(IIVTNU / plusvalia municipal).

Normativa:
- RDL 26/2021 (post STC 182/2021)
- Coeficientes maximos actualizados 2024 (Orden HFP/1177/2023)
- Tipo impositivo maximo: 30%, cada municipio fija el suyo
- El contribuyente elige el metodo (objetivo o real) que resulte menor

Exenciones:
- Transmisiones entre conyuges por divorcio
- Dacion en pago de vivienda habitual
- Aportaciones a sociedad conyugal
"""
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# OpenAI tool definition
# ---------------------------------------------------------------------------

PLUSVALIA_MUNICIPAL_TOOL = {
    "type": "function",
    "function": {
        "name": "calculate_plusvalia_municipal",
        "description": """SIEMPRE DEBES USAR ESTA FUNCION cuando el usuario pregunte sobre:
- Plusvalia municipal, IIVTNU, impuesto sobre incremento de valor de terrenos
- Cuanto se paga de plusvalia al vender un piso/casa/inmueble
- Impuesto municipal por venta de vivienda/local/terreno
- "He vendido mi casa, tengo que pagar plusvalia?"
- "Cuanto es la plusvalia municipal de mi piso?"
- Calculo de plusvalia tras herencia, donacion o venta

OBLIGATORIO usar esta funcion si el usuario menciona:
- Precio de venta y adquisicion de un inmueble
- Valor catastral del suelo
- Anos de tenencia del inmueble
- Tipo impositivo municipal

La funcion calcula la plusvalia municipal por ambos metodos (objetivo y real)
y devuelve el mas favorable para el contribuyente, segun RDL 26/2021.""",
        "parameters": {
            "type": "object",
            "properties": {
                "precio_venta": {
                    "type": "number",
                    "description": "Precio de transmision (venta) del inmueble en euros."
                },
                "precio_adquisicion": {
                    "type": "number",
                    "description": "Precio de adquisicion del inmueble en euros."
                },
                "valor_catastral_total": {
                    "type": "number",
                    "description": (
                        "Valor catastral total del inmueble (suelo + construccion) "
                        "en euros. Aparece en el recibo del IBI."
                    )
                },
                "valor_catastral_suelo": {
                    "type": "number",
                    "description": (
                        "Valor catastral del suelo en euros. "
                        "Aparece desglosado en el recibo del IBI."
                    )
                },
                "anos_tenencia": {
                    "type": "integer",
                    "description": (
                        "Anos completos de tenencia del inmueble "
                        "(desde la adquisicion hasta la transmision). Maximo relevante: 20."
                    )
                },
                "tipo_impositivo_municipal": {
                    "type": "number",
                    "description": (
                        "Tipo impositivo del municipio en porcentaje (maximo legal: 30%). "
                        "Ejemplos: Madrid 29%, Barcelona 30%, Valencia 30%, Sevilla 30%. "
                        "Si no se conoce, usar 30% (maximo legal)."
                    )
                },
                "es_vivienda_habitual_dacion": {
                    "type": "boolean",
                    "description": (
                        "True si la transmision es una dacion en pago de la vivienda habitual "
                        "(exenta de plusvalia municipal segun Art. 105.1.c TRLRHL)."
                    )
                },
                "es_divorcio": {
                    "type": "boolean",
                    "description": (
                        "True si la transmision es entre conyuges por disolucion matrimonial "
                        "(exenta de plusvalia municipal segun Art. 104.3 TRLRHL)."
                    )
                }
            },
            "required": [
                "precio_venta",
                "precio_adquisicion",
                "valor_catastral_total",
                "valor_catastral_suelo",
                "anos_tenencia"
            ]
        }
    }
}


# ---------------------------------------------------------------------------
# Tool executor
# ---------------------------------------------------------------------------

async def calculate_plusvalia_municipal_tool(
    precio_venta: float,
    precio_adquisicion: float,
    valor_catastral_total: float,
    valor_catastral_suelo: float,
    anos_tenencia: int,
    tipo_impositivo_municipal: float = 30.0,
    es_vivienda_habitual_dacion: bool = False,
    es_divorcio: bool = False,
) -> Dict[str, Any]:
    """
    Calcula la plusvalia municipal (IIVTNU) por ambos metodos y devuelve
    el mas favorable para el contribuyente.

    Normativa: RDL 26/2021 post STC 182/2021. Coeficientes 2024.

    Args:
        precio_venta: Precio de transmision en euros.
        precio_adquisicion: Precio de adquisicion en euros.
        valor_catastral_total: Valor catastral total (suelo + construccion).
        valor_catastral_suelo: Valor catastral del suelo.
        anos_tenencia: Anos completos de tenencia (0-20+).
        tipo_impositivo_municipal: Tipo del municipio (max 30%).
        es_vivienda_habitual_dacion: Dacion en pago vivienda habitual.
        es_divorcio: Transmision entre conyuges por divorcio.

    Returns:
        Dict con desglose ambos metodos, metodo elegido, cuota final,
        exenciones y formatted_response para el LLM.
    """
    try:
        from app.utils.calculators.plusvalia_municipal import (
            PlusvaliaMunicipalCalculator,
        )

        calculator = PlusvaliaMunicipalCalculator()
        result = await calculator.calculate(
            precio_venta=precio_venta,
            precio_adquisicion=precio_adquisicion,
            valor_catastral_total=valor_catastral_total,
            valor_catastral_suelo=valor_catastral_suelo,
            anos_tenencia=anos_tenencia,
            tipo_impositivo_municipal=tipo_impositivo_municipal,
            es_vivienda_habitual_dacion=es_vivienda_habitual_dacion,
            es_divorcio=es_divorcio,
        )
        return result

    except Exception as e:
        logger.error("Error calculating plusvalia municipal: %s", str(e))
        return {
            "success": False,
            "error": f"Error en el calculo de plusvalia municipal: {str(e)}",
            "formatted_response": (
                "Ha ocurrido un error al calcular la plusvalia municipal. "
                "Por favor, verifica los datos introducidos."
            ),
        }
