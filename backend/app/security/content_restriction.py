"""
Content Restriction for TaxIA/Impuestify

Detects autonomo (self-employed) queries and blocks them for
users on the Particular (salaried workers) plan.
"""
import re
from typing import List

# Keywords that indicate a query is about autonomo/self-employed topics.
# Ordered roughly by specificity (more specific first).
AUTONOMO_KEYWORDS: List[str] = [
    # Direct references
    "autónomo",
    "autonomo",
    "soy autónomo",
    "soy autonomo",
    "como autónomo",
    "como autonomo",
    "cuota de autónomo",
    "cuota de autonomo",
    "cuota autónomos",
    "cuota autonomos",
    "cotización autónomo",
    "cotizacion autonomo",
    # RETA (Regimen Especial de Trabajadores Autonomos)
    "reta",
    "régimen de autónomos",
    "regimen de autonomos",
    "tarifa plana autónomos",
    "tarifa plana autonomos",
    "alta autónomo",
    "alta autonomo",
    "baja autónomo",
    "baja autonomo",
    # Modelos fiscales de autonomos
    "modelo 130",
    "modelo 131",
    "modelo 303",
    "modelo 036",
    "modelo 037",
    "modelo 390",
    "pago fraccionado",
    # IVA como autonomo
    "iva trimestral",
    "declaración de iva",
    "declaracion de iva",
    "liquidación de iva",
    "liquidacion de iva",
    # Facturacion
    "factura emitida",
    "emitir factura",
    "facturar como",
    "facturación",
    "facturacion",
    # Rendimientos de actividades economicas
    "rendimientos de actividades económicas",
    "rendimientos de actividades economicas",
    "actividad económica",
    "actividad economica",
    "actividades económicas",
    "actividades economicas",
    # IAE
    "epígrafe iae",
    "epigrafe iae",
    "alta en hacienda",
    # Estimacion directa/objetiva
    "estimación directa",
    "estimacion directa",
    "estimación objetiva",
    "estimacion objetiva",
    # Gastos deducibles de autonomos
    "gastos deducibles autónomo",
    "gastos deducibles autonomo",
]

# Response shown to salaried-plan users who ask about autonomo topics.
AUTONOMO_RESPONSE = (
    "Estás solicitando información sobre **autónomos**, pero tu cuenta está "
    "registrada como **trabajador por cuenta ajena**.\n\n"
    "Tu plan actual (**Particular — 15 €/mes**) incluye:\n"
    "- Análisis de nóminas\n"
    "- Cálculo de IRPF (Modelo 100)\n"
    "- Consultas sobre notificaciones de la AEAT\n\n"
    "Si necesitas asistencia fiscal como autónomo o profesional por cuenta propia, "
    "contacta con nosotros para conocer nuestros planes especializados.\n\n"
    "👉 [Solicitar información sobre plan de autónomos](/contact?type=autonomo)"
)


def detect_autonomo_query(text: str) -> bool:
    """
    Detect if a query is about autonomo/self-employed topics.

    Uses case-insensitive keyword matching against a curated list
    of autonomo-related terms in Spanish.
    """
    text_lower = text.lower()

    for keyword in AUTONOMO_KEYWORDS:
        if keyword.lower() in text_lower:
            return True

    return False


def get_autonomo_block_response() -> str:
    """Return the friendly block message for autonomo queries."""
    return AUTONOMO_RESPONSE
