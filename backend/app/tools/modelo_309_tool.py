"""
Modelo 309 (Declaracion-Liquidacion No Periodica del IVA) Tool for TaxIA

The Modelo 309 is the *non-periodic* IVA self-assessment used by taxable persons
who, for a given operation, are not entitled to file the regular Modelo 303 — or
who must self-assess IVA outside the regular periodic flow.

Per AEAT instructions and Art. 154-163 LIVA + Art. 30 bis RIVA, key cases are:

1. Comerciantes minoristas en Recargo de Equivalencia (RE) que realicen:
   - Adquisiciones intracomunitarias de bienes (autoliquidacion IVA + RE).
   - Operaciones con inversion del sujeto pasivo (Art. 84.uno.2.o LIVA).
   - Importaciones de bienes (cuando el IVA importacion no se gestiona en aduana).

2. Sujetos en regimenes especiales (RE, agricultura, simplificado) que
   ocasionalmente realicen entregas o adquisiciones que excedan el regimen.

3. Sujetos pasivos no establecidos que excepcionalmente liquiden IVA.

4. Adjudicatarios en procedimientos administrativos de subasta que actuen
   como sujetos pasivos por inversion.

PLAZO: 20 primeros dias del mes siguiente al trimestre (T1=20-abr, T2=20-jul,
T3=20-oct), o 30 de enero para el 4T (Art. 71 RIVA).

Tipos de Recargo de Equivalencia vigentes (Art. 156 LIVA):
- 5,2% sobre tipo general 21%
- 1,4% sobre tipo reducido 10%
- 0,5% sobre tipo superreducido 4%
- 1,75% sobre labores del tabaco

NO confundir con Modelo 308 (solicitud de devolucion para sujetos ocasionales
de medios de transporte nuevos, transportistas en simplificado, o RE con
devoluciones a viajeros tax-free).
"""

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# IVA + RE rates (2025) — Art. 156 LIVA
# Each tuple: (iva_rate, re_rate)
TIPOS_RE_309 = {
    "general": (0.21, 0.052),
    "reducido": (0.10, 0.014),
    "superreducido": (0.04, 0.005),
    "tabaco": (0.21, 0.0175),  # Labores del tabaco — RE 1,75%
}

# Plazos por trimestre (dia limite)
PLAZOS_309 = {
    "1T": "20 de abril",
    "2T": "20 de julio",
    "3T": "20 de octubre",
    "4T": "30 de enero (del ano siguiente)",
}

MODELO_309_TOOL = {
    "type": "function",
    "function": {
        "name": "calculate_modelo_309",
        "description": """USAR ESTA FUNCION cuando el usuario pregunte sobre:
- Modelo 309
- Declaracion-liquidacion no periodica del IVA
- Comerciante minorista en Recargo de Equivalencia que compra a proveedor de la UE
- Adquisiciones intracomunitarias en regimen de Recargo de Equivalencia
- Inversion del sujeto pasivo (ISP) en regimen de Recargo de Equivalencia
- Estanco que adquiere labores del tabaco intracomunitarias (RE 1,75%)
- Farmacia, kiosco, comercio minorista que importa o compra a la UE

OBLIGATORIO usar esta funcion (NO el Modelo 308) cuando el usuario sea
comerciante en RE y deba autoliquidar IVA + RE por:
- Adquisiciones intracomunitarias de bienes (Art. 30 bis RIVA)
- Operaciones con inversion del sujeto pasivo (Art. 84.uno.2.o LIVA)
- Importaciones (en supuestos no liquidados en aduana)

El Modelo 309 es la autoliquidacion no periodica para casos en los que el
sujeto en RE no presenta Modelo 303 pero debe ingresar IVA + RE por estas
operaciones especificas.

NO confundir con Modelo 308 (devolucion para sujetos ocasionales por entrega
de medios de transporte nuevos, transportistas en simplificado adquiriendo
vehiculos, o comerciantes RE que devuelven IVA a viajeros tax-free).
""",
        "parameters": {
            "type": "object",
            "properties": {
                "periodo": {
                    "type": "string",
                    "description": "Trimestre de la operacion: '1T', '2T', '3T' o '4T'.",
                },
                "year": {"type": "integer", "description": "Ano fiscal. Por defecto: ano actual"},
                "base_intracomunitarias_21": {
                    "type": "number",
                    "description": "Base imponible de adquisiciones intracomunitarias al tipo general (21% IVA + 5,2% RE). Por defecto: 0",
                },
                "base_intracomunitarias_10": {
                    "type": "number",
                    "description": "Base imponible de adquisiciones intracomunitarias al tipo reducido (10% IVA + 1,4% RE). Por defecto: 0",
                },
                "base_intracomunitarias_4": {
                    "type": "number",
                    "description": "Base imponible de adquisiciones intracomunitarias al tipo superreducido (4% IVA + 0,5% RE). Por defecto: 0",
                },
                "base_intracomunitarias_tabaco": {
                    "type": "number",
                    "description": "Base imponible de adquisiciones intracomunitarias de labores del tabaco (21% IVA + 1,75% RE). Por defecto: 0",
                },
                "base_isp_21": {
                    "type": "number",
                    "description": "Base imponible de operaciones con inversion del sujeto pasivo al tipo general 21%. Por defecto: 0",
                },
                "base_isp_10": {
                    "type": "number",
                    "description": "Base imponible de operaciones con inversion del sujeto pasivo al tipo reducido 10%. Por defecto: 0",
                },
                "base_isp_4": {
                    "type": "number",
                    "description": "Base imponible de operaciones con inversion del sujeto pasivo al tipo superreducido 4%. Por defecto: 0",
                },
                "aplica_re": {
                    "type": "boolean",
                    "description": "Si el sujeto esta en regimen de Recargo de Equivalencia (true) o no (false). Si false, solo se calcula IVA, sin RE. Por defecto: true",
                },
            },
            "required": ["periodo"],
        },
    },
}


async def calculate_modelo_309_tool(
    periodo: str,
    year: int = None,
    base_intracomunitarias_21: float = 0,
    base_intracomunitarias_10: float = 0,
    base_intracomunitarias_4: float = 0,
    base_intracomunitarias_tabaco: float = 0,
    base_isp_21: float = 0,
    base_isp_10: float = 0,
    base_isp_4: float = 0,
    aplica_re: bool = True,
    restricted_mode: bool = False,
) -> dict[str, Any]:
    """
    Calculate the Modelo 309 (non-periodic IVA self-assessment) for retailers
    in the Recargo de Equivalencia (RE) regime, or for any taxable person
    needing to self-assess IVA outside the regular periodic Modelo 303.

    Covers:
    1. Adquisiciones intracomunitarias (general 21%, reducido 10%, superreducido
       4%, labores del tabaco 1,75% RE).
    2. Inversion del sujeto pasivo (Art. 84.uno.2.o LIVA).

    Args:
        periodo: '1T', '2T', '3T' or '4T'
        year: Fiscal year (default: current)
        base_intracomunitarias_21: Intra-community acquisitions at 21%
        base_intracomunitarias_10: Intra-community acquisitions at 10%
        base_intracomunitarias_4: Intra-community acquisitions at 4%
        base_intracomunitarias_tabaco: Tobacco intra-community (21% IVA + 1,75% RE)
        base_isp_21: Reverse charge operations at 21%
        base_isp_10: Reverse charge operations at 10%
        base_isp_4: Reverse charge operations at 4%
        aplica_re: Whether subject is in RE regime (true) or not (false)
        restricted_mode: If True, block (salaried-only plan)

    Returns:
        Dict with computed amounts and a Spanish-formatted response.
    """
    if restricted_mode:
        from app.security.content_restriction import get_autonomo_block_response

        logger.warning("calculate_modelo_309 called in restricted_mode — blocking")
        return {
            "success": False,
            "error": "restricted",
            "formatted_response": get_autonomo_block_response(),
        }

    try:
        if year is None:
            year = datetime.now().year

        # Validate periodo (309 is always quarterly — no annual 0A)
        periodos_validos = {"1T", "2T", "3T", "4T"}
        periodo_upper = periodo.upper().strip()
        if periodo_upper not in periodos_validos:
            return {
                "success": False,
                "error": "Periodo debe ser '1T', '2T', '3T' o '4T'",
                "formatted_response": (
                    "El periodo del Modelo 309 debe ser un trimestre "
                    "(1T, 2T, 3T o 4T). No admite presentacion anual."
                ),
            }

        # Validate no negative bases
        bases = {
            "base_intracomunitarias_21": base_intracomunitarias_21,
            "base_intracomunitarias_10": base_intracomunitarias_10,
            "base_intracomunitarias_4": base_intracomunitarias_4,
            "base_intracomunitarias_tabaco": base_intracomunitarias_tabaco,
            "base_isp_21": base_isp_21,
            "base_isp_10": base_isp_10,
            "base_isp_4": base_isp_4,
        }
        for name, val in bases.items():
            if val < 0:
                return {
                    "success": False,
                    "error": f"{name} no puede ser negativo",
                    "formatted_response": (
                        f"La base imponible '{name}' no puede ser negativa. "
                        f"Valor recibido: {val:,.2f} EUR."
                    ),
                }

        # ===== 1. ADQUISICIONES INTRACOMUNITARIAS =====
        cuota_intra_21_iva = round(base_intracomunitarias_21 * 0.21, 2)
        cuota_intra_10_iva = round(base_intracomunitarias_10 * 0.10, 2)
        cuota_intra_4_iva = round(base_intracomunitarias_4 * 0.04, 2)
        cuota_intra_tabaco_iva = round(base_intracomunitarias_tabaco * 0.21, 2)

        if aplica_re:
            cuota_intra_21_re = round(base_intracomunitarias_21 * 0.052, 2)
            cuota_intra_10_re = round(base_intracomunitarias_10 * 0.014, 2)
            cuota_intra_4_re = round(base_intracomunitarias_4 * 0.005, 2)
            cuota_intra_tabaco_re = round(base_intracomunitarias_tabaco * 0.0175, 2)
        else:
            cuota_intra_21_re = 0.0
            cuota_intra_10_re = 0.0
            cuota_intra_4_re = 0.0
            cuota_intra_tabaco_re = 0.0

        total_cuota_intra_iva = round(
            cuota_intra_21_iva + cuota_intra_10_iva + cuota_intra_4_iva + cuota_intra_tabaco_iva,
            2,
        )
        total_cuota_intra_re = round(
            cuota_intra_21_re + cuota_intra_10_re + cuota_intra_4_re + cuota_intra_tabaco_re,
            2,
        )
        total_base_intra = round(
            base_intracomunitarias_21
            + base_intracomunitarias_10
            + base_intracomunitarias_4
            + base_intracomunitarias_tabaco,
            2,
        )

        # ===== 2. INVERSION DEL SUJETO PASIVO =====
        cuota_isp_21_iva = round(base_isp_21 * 0.21, 2)
        cuota_isp_10_iva = round(base_isp_10 * 0.10, 2)
        cuota_isp_4_iva = round(base_isp_4 * 0.04, 2)

        if aplica_re:
            cuota_isp_21_re = round(base_isp_21 * 0.052, 2)
            cuota_isp_10_re = round(base_isp_10 * 0.014, 2)
            cuota_isp_4_re = round(base_isp_4 * 0.005, 2)
        else:
            cuota_isp_21_re = 0.0
            cuota_isp_10_re = 0.0
            cuota_isp_4_re = 0.0

        total_cuota_isp_iva = round(cuota_isp_21_iva + cuota_isp_10_iva + cuota_isp_4_iva, 2)
        total_cuota_isp_re = round(cuota_isp_21_re + cuota_isp_10_re + cuota_isp_4_re, 2)
        total_base_isp = round(base_isp_21 + base_isp_10 + base_isp_4, 2)

        # ===== TOTAL A INGRESAR =====
        # Modelo 309 es siempre "a ingresar" (no permite devolucion).
        total_iva_devengado = round(total_cuota_intra_iva + total_cuota_isp_iva, 2)
        total_re_devengado = round(total_cuota_intra_re + total_cuota_isp_re, 2)
        total_a_ingresar = round(total_iva_devengado + total_re_devengado, 2)

        # Period label
        trimestre_meses = {
            "1T": "enero-marzo",
            "2T": "abril-junio",
            "3T": "julio-septiembre",
            "4T": "octubre-diciembre",
        }[periodo_upper]
        periodo_label = f"{periodo_upper} {year} ({trimestre_meses})"
        plazo_label = PLAZOS_309[periodo_upper]

        # ===== BUILD FORMATTED RESPONSE =====
        lines = []
        lines.append(f"**Modelo 309 — Autoliquidacion No Periodica IVA — {periodo_label}**")
        regimen_label = "Recargo de Equivalencia" if aplica_re else "regimen general"
        lines.append(f"Regimen: {regimen_label}")
        lines.append("Presentacion: AEAT (sede.agenciatributaria.gob.es)")
        lines.append(f"Plazo: hasta el {plazo_label}.")
        lines.append("")

        has_intra = total_base_intra > 0
        has_isp = total_base_isp > 0

        # Section: Adquisiciones intracomunitarias
        if has_intra:
            lines.append("**Adquisiciones intracomunitarias (Art. 30 bis RIVA)**")
            if base_intracomunitarias_21 > 0:
                if aplica_re:
                    lines.append(
                        f"- Base 21%: {base_intracomunitarias_21:,.2f} EUR | "
                        f"IVA: {cuota_intra_21_iva:,.2f} EUR | "
                        f"RE 5,2%: {cuota_intra_21_re:,.2f} EUR"
                    )
                else:
                    lines.append(
                        f"- Base 21%: {base_intracomunitarias_21:,.2f} EUR | "
                        f"IVA: {cuota_intra_21_iva:,.2f} EUR"
                    )
            if base_intracomunitarias_10 > 0:
                if aplica_re:
                    lines.append(
                        f"- Base 10%: {base_intracomunitarias_10:,.2f} EUR | "
                        f"IVA: {cuota_intra_10_iva:,.2f} EUR | "
                        f"RE 1,4%: {cuota_intra_10_re:,.2f} EUR"
                    )
                else:
                    lines.append(
                        f"- Base 10%: {base_intracomunitarias_10:,.2f} EUR | "
                        f"IVA: {cuota_intra_10_iva:,.2f} EUR"
                    )
            if base_intracomunitarias_4 > 0:
                if aplica_re:
                    lines.append(
                        f"- Base 4%: {base_intracomunitarias_4:,.2f} EUR | "
                        f"IVA: {cuota_intra_4_iva:,.2f} EUR | "
                        f"RE 0,5%: {cuota_intra_4_re:,.2f} EUR"
                    )
                else:
                    lines.append(
                        f"- Base 4%: {base_intracomunitarias_4:,.2f} EUR | "
                        f"IVA: {cuota_intra_4_iva:,.2f} EUR"
                    )
            if base_intracomunitarias_tabaco > 0:
                lines.append(
                    f"- Base tabaco 21%: {base_intracomunitarias_tabaco:,.2f} EUR | "
                    f"IVA: {cuota_intra_tabaco_iva:,.2f} EUR | "
                    f"RE 1,75%: {cuota_intra_tabaco_re:,.2f} EUR"
                )
            if aplica_re:
                lines.append(
                    f"- **Total intracomunitarias: IVA {total_cuota_intra_iva:,.2f} EUR | "
                    f"RE {total_cuota_intra_re:,.2f} EUR**"
                )
            else:
                lines.append(f"- **Total intracomunitarias: IVA {total_cuota_intra_iva:,.2f} EUR**")
            lines.append("")

        # Section: Inversion del sujeto pasivo
        if has_isp:
            lines.append("**Inversion del sujeto pasivo (Art. 84.uno.2.o LIVA)**")
            if base_isp_21 > 0:
                if aplica_re:
                    lines.append(
                        f"- Base 21%: {base_isp_21:,.2f} EUR | "
                        f"IVA: {cuota_isp_21_iva:,.2f} EUR | "
                        f"RE 5,2%: {cuota_isp_21_re:,.2f} EUR"
                    )
                else:
                    lines.append(
                        f"- Base 21%: {base_isp_21:,.2f} EUR | " f"IVA: {cuota_isp_21_iva:,.2f} EUR"
                    )
            if base_isp_10 > 0:
                if aplica_re:
                    lines.append(
                        f"- Base 10%: {base_isp_10:,.2f} EUR | "
                        f"IVA: {cuota_isp_10_iva:,.2f} EUR | "
                        f"RE 1,4%: {cuota_isp_10_re:,.2f} EUR"
                    )
                else:
                    lines.append(
                        f"- Base 10%: {base_isp_10:,.2f} EUR | " f"IVA: {cuota_isp_10_iva:,.2f} EUR"
                    )
            if base_isp_4 > 0:
                if aplica_re:
                    lines.append(
                        f"- Base 4%: {base_isp_4:,.2f} EUR | "
                        f"IVA: {cuota_isp_4_iva:,.2f} EUR | "
                        f"RE 0,5%: {cuota_isp_4_re:,.2f} EUR"
                    )
                else:
                    lines.append(
                        f"- Base 4%: {base_isp_4:,.2f} EUR | " f"IVA: {cuota_isp_4_iva:,.2f} EUR"
                    )
            if aplica_re:
                lines.append(
                    f"- **Total ISP: IVA {total_cuota_isp_iva:,.2f} EUR | "
                    f"RE {total_cuota_isp_re:,.2f} EUR**"
                )
            else:
                lines.append(f"- **Total ISP: IVA {total_cuota_isp_iva:,.2f} EUR**")
            lines.append("")

        # Resultado
        lines.append("**Resultado**")
        lines.append(f"- IVA devengado: {total_iva_devengado:,.2f} EUR")
        if aplica_re:
            lines.append(f"- RE devengado: {total_re_devengado:,.2f} EUR")
        lines.append(f"- **Total a ingresar: {total_a_ingresar:,.2f} EUR**")
        lines.append("")

        # Notes
        if aplica_re:
            lines.append(
                "El sujeto en regimen de Recargo de Equivalencia debe autoliquidar "
                "IVA + RE en estas operaciones (Art. 154.dos LIVA). Estas cuotas NO "
                "son deducibles en el regimen RE (no se presentan via Modelo 303), "
                "por lo que el Modelo 309 es siempre 'a ingresar'."
            )
        lines.append(
            "Modelo 309 — declaracion-liquidacion no periodica. NO confundir con el "
            "Modelo 308 (devolucion para sujetos ocasionales de medios de transporte "
            "nuevos, transportistas en simplificado, o tax-free a viajeros)."
        )

        formatted_response = "\n".join(lines)

        logger.info(
            f"Modelo 309 calculated: {periodo_upper} {year}, "
            f"iva={total_iva_devengado}, re={total_re_devengado}, "
            f"total={total_a_ingresar}"
        )

        return {
            "success": True,
            "periodo": periodo_upper,
            "year": year,
            "modelo": "309",
            "regimen": "Recargo de Equivalencia" if aplica_re else "regimen general",
            "aplica_re": aplica_re,
            "plazo": plazo_label,
            "adquisiciones_intracomunitarias": {
                "base_total": total_base_intra,
                "cuota_iva": total_cuota_intra_iva,
                "cuota_re": total_cuota_intra_re,
                "desglose": {
                    "base_21": base_intracomunitarias_21,
                    "iva_21": cuota_intra_21_iva,
                    "re_21": cuota_intra_21_re,
                    "base_10": base_intracomunitarias_10,
                    "iva_10": cuota_intra_10_iva,
                    "re_10": cuota_intra_10_re,
                    "base_4": base_intracomunitarias_4,
                    "iva_4": cuota_intra_4_iva,
                    "re_4": cuota_intra_4_re,
                    "base_tabaco": base_intracomunitarias_tabaco,
                    "iva_tabaco": cuota_intra_tabaco_iva,
                    "re_tabaco": cuota_intra_tabaco_re,
                },
            },
            "inversion_sujeto_pasivo": {
                "base_total": total_base_isp,
                "cuota_iva": total_cuota_isp_iva,
                "cuota_re": total_cuota_isp_re,
                "desglose": {
                    "base_21": base_isp_21,
                    "iva_21": cuota_isp_21_iva,
                    "re_21": cuota_isp_21_re,
                    "base_10": base_isp_10,
                    "iva_10": cuota_isp_10_iva,
                    "re_10": cuota_isp_10_re,
                    "base_4": base_isp_4,
                    "iva_4": cuota_isp_4_iva,
                    "re_4": cuota_isp_4_re,
                },
            },
            "resultado": {
                "iva_devengado": total_iva_devengado,
                "re_devengado": total_re_devengado,
                "total_a_ingresar": total_a_ingresar,
                "tipo": "A ingresar",
            },
            "formatted_response": formatted_response,
        }

    except Exception as e:
        logger.error(f"Error calculating Modelo 309: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "formatted_response": f"Error al calcular el Modelo 309: {str(e)}",
        }
