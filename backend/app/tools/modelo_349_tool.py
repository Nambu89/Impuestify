"""
Modelo 349 (Declaracion recapitulativa de operaciones intracomunitarias)
Tool for TaxIA function calling.

Wraps `Modelo349Calculator`:
- Acepta lista de operaciones con clave + NIF-IVA + importe.
- Detecta periodicidad (mensual / trimestral / anual) por umbrales legales.
- Valida sintacticamente los NIF-IVA.
- Opcionalmente valida en VIES (con fail-open + cache LRU).
- Devuelve cuadre 303<->349 si el caller pasa casillas_303.
- Routing CCAA: bloquea Canarias/Ceuta/Melilla (no son territorio IVA UE).

NO genera fichero AEAT, NO presenta. Solo computa y avisa.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.utils.calculators.modelo_349 import (
    CLAVES_VALIDAS,
    Modelo349Calculator,
    Operacion349,
)
from app.utils.ccaa_constants import CANARIAS_SET, CEUTA_MELILLA, normalize_ccaa

logger = logging.getLogger(__name__)


MODELO_349_TOOL = {
    "type": "function",
    "function": {
        "name": "calculate_modelo_349",
        "description": (
            "USAR ESTA FUNCION cuando el usuario pregunte sobre:\n"
            "- Modelo 349 / Declaracion recapitulativa de operaciones intracomunitarias\n"
            "- Operaciones intracomunitarias UE (entregas o adquisiciones)\n"
            "- Servicios B2B a clientes UE (Google Ireland, Meta Ireland, etc.)\n"
            "- Compras intracomunitarias de software o hardware UE\n"
            "- Periodicidad mensual vs trimestral del 349 (umbral 50.000 EUR)\n"
            "- Validacion NIF-IVA UE (VIES / ROI)\n"
            "- Cuadre entre Modelo 303 y Modelo 349\n"
            "- Operaciones triangulares (intermediario UE)\n"
            "- Consignaciones / call-off stock (Art. 9 bis LIVA)\n"
            "- Rectificaciones de declaraciones 349 anteriores\n\n"
            "RESTRICCIONES TERRITORIALES:\n"
            "- Si la CCAA es Canarias, Ceuta o Melilla: NO procede 349 (no son territorio IVA armonizado UE).\n"
            "  En esos territorios las operaciones con UE son exportaciones (no intracomunitarias).\n"
            "- Operaciones con Reino Unido (post-Brexit) NO van en 349 — son importaciones/exportaciones, salvo Irlanda del Norte (XI) en bienes.\n\n"
            "CLAVES DE OPERACION (Art. 4 Orden EHA/769/2010):\n"
            "  E=entrega bienes, A=adquisicion bienes, T=triangular, S=prestacion servicios B2B,\n"
            "  I=adquisicion servicios, M=entregas tras importacion, H=representante en M,\n"
            "  R=transferencia consignacion, D=devolucion consignacion, C=sustitucion adquirente, N=rectificacion."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "operaciones": {
                    "type": "array",
                    "description": (
                        "Lista de operaciones intracomunitarias del periodo. "
                        "Cada operacion debe especificar nif_operador (NIF-IVA UE con prefijo, "
                        "ej. 'IE9825613N'), nombre, clave (E/A/T/S/I/M/H/R/D/C/N) e importe (EUR)."
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "nif_operador": {
                                "type": "string",
                                "description": "NIF-IVA UE con prefijo ISO de 2 letras. Ej: 'IE9825613N' (Irlanda), 'DE123456789' (Alemania).",
                            },
                            "nombre": {
                                "type": "string",
                                "description": "Razon social del operador UE.",
                            },
                            "clave": {
                                "type": "string",
                                "enum": list(CLAVES_VALIDAS),
                                "description": "Clave de operacion: E, A, T, S, I, M, H, R, D, C, N.",
                            },
                            "importe": {
                                "type": "number",
                                "description": "Importe en EUR. Positivo salvo clave N (rectificacion a la baja, puede ser negativo).",
                            },
                            "periodo_rectificado": {
                                "type": "string",
                                "description": "Solo clave N o C: periodo original que se rectifica (ej. '2T 2025').",
                            },
                            "base_anterior_declarada": {
                                "type": "number",
                                "description": "Solo clave N: base previamente declarada que ahora se rectifica.",
                            },
                        },
                        "required": ["nif_operador", "nombre", "clave", "importe"],
                    },
                },
                "periodo": {
                    "type": "string",
                    "description": (
                        "Periodo declarado: '01'..'12' para mensual, '1T'..'4T' para trimestral, 'anual' para anual. "
                        "Por defecto '1T'."
                    ),
                },
                "year": {
                    "type": "integer",
                    "description": "Ano fiscal. Por defecto: ano actual.",
                },
                "ccaa": {
                    "type": "string",
                    "description": "CCAA del declarante (para excluir Canarias/Ceuta/Melilla). Opcional.",
                },
                "importes_4_trimestres_anteriores": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": (
                        "Volumen EIB+EIS+AIB+AIS de cada uno de los hasta 4 trimestres anteriores. "
                        "Si alguno > 50.000 EUR -> periodicidad mensual obligatoria."
                    ),
                },
                "casillas_303": {
                    "type": "object",
                    "description": (
                        "Casillas relevantes del 303 del mismo periodo para cuadre. "
                        "Keys: casilla_60 (EIB exentas), casilla_36 (AIB corrientes), casilla_38 (AIB inversion)."
                    ),
                    "properties": {
                        "casilla_60": {"type": "number"},
                        "casilla_36": {"type": "number"},
                        "casilla_38": {"type": "number"},
                    },
                },
                "validar_vies": {
                    "type": "boolean",
                    "description": (
                        "Si True, consulta el servicio VIES de la UE (timeout 5s, fail-open). "
                        "Por defecto False — la herramienta solo valida formato sintactico."
                    ),
                },
                "forzar_anual": {
                    "type": "boolean",
                    "description": "Si el declarante ya optó expresamente por modalidad anual.",
                },
            },
            "required": ["operaciones"],
        },
    },
}


# --------------------------------------------------------------------------- #
# Executor
# --------------------------------------------------------------------------- #


def _build_operaciones(raw: List[Dict[str, Any]]) -> tuple[List[Operacion349], List[str]]:
    """Convierte input dict -> Operacion349. Retorna (ops_validas, errores)."""
    operaciones: List[Operacion349] = []
    errores: List[str] = []
    for idx, op in enumerate(raw or []):
        try:
            nif = str(op.get("nif_operador", "")).strip()
            clave = str(op.get("clave", "")).strip().upper()
            nombre = str(op.get("nombre", "") or "").strip()
            importe_raw = op.get("importe", 0)
            try:
                importe = float(importe_raw)
            except (TypeError, ValueError):
                errores.append(f"Operacion #{idx + 1}: importe no numerico ({importe_raw!r}).")
                continue

            if not nif:
                errores.append(f"Operacion #{idx + 1}: NIF-IVA vacio.")
                continue
            if clave not in CLAVES_VALIDAS:
                errores.append(
                    f"Operacion #{idx + 1}: clave '{clave}' no valida "
                    f"(esperado {sorted(CLAVES_VALIDAS)})."
                )
                continue
            # Solo N admite negativos
            if importe < 0 and clave != "N":
                errores.append(
                    f"Operacion #{idx + 1} ({nif}): importe negativo solo permitido "
                    f"con clave N (rectificacion); recibida clave {clave}."
                )
                continue

            operaciones.append(
                Operacion349(
                    nif_operador=nif,
                    nombre=nombre or nif,
                    clave=clave,
                    importe=importe,
                    periodo_rectificado=op.get("periodo_rectificado") or None,
                    base_anterior_declarada=(
                        float(op["base_anterior_declarada"])
                        if op.get("base_anterior_declarada") is not None
                        else None
                    ),
                )
            )
        except Exception as exc:  # noqa: BLE001
            errores.append(f"Operacion #{idx + 1}: error parseando ({exc}).")
    return operaciones, errores


def _periodo_label(periodicidad: str, periodo: str, year: int) -> str:
    if periodicidad == "mensual":
        try:
            mes = int(periodo)
            meses = [
                "enero", "febrero", "marzo", "abril", "mayo", "junio",
                "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
            ]
            return f"{meses[mes - 1].capitalize()} {year}"
        except (ValueError, IndexError):
            return f"{periodo} {year}"
    if periodicidad == "trimestral":
        return f"{periodo.upper()} {year}"
    return f"Anual {year}"


async def calculate_modelo_349_tool(
    operaciones: List[Dict[str, Any]],
    periodo: str = "1T",
    year: Optional[int] = None,
    ccaa: Optional[str] = None,
    importes_4_trimestres_anteriores: Optional[List[float]] = None,
    casillas_303: Optional[Dict[str, float]] = None,
    validar_vies: bool = False,
    forzar_anual: bool = False,
    restricted_mode: bool = False,
) -> Dict[str, Any]:
    """Calcula el Modelo 349 a partir de una lista de operaciones intracomunitarias."""
    if restricted_mode:
        from app.security.content_restriction import get_autonomo_block_response

        logger.warning("calculate_modelo_349 called in restricted_mode — blocking")
        return {
            "success": False,
            "error": "restricted",
            "formatted_response": get_autonomo_block_response(),
        }

    try:
        if year is None:
            year = datetime.now().year

        # ----- Routing territorial -----
        ccaa_canonical = normalize_ccaa(ccaa) if ccaa else None
        if ccaa_canonical in CANARIAS_SET:
            return {
                "success": False,
                "error": "ccaa_no_aplicable",
                "ccaa": ccaa_canonical,
                "formatted_response": (
                    "Canarias NO pertenece al territorio IVA armonizado UE (Art. 6 Directiva IVA). "
                    "El Modelo 349 no aplica desde Canarias. Las facturas a Google Ireland, Meta Ireland, "
                    "etc. son EXPORTACION de servicios, no operacion intracomunitaria. Verifica IGIC y Modelo 420."
                ),
            }
        if ccaa_canonical in CEUTA_MELILLA:
            return {
                "success": False,
                "error": "ccaa_no_aplicable",
                "ccaa": ccaa_canonical,
                "formatted_response": (
                    f"En {ccaa_canonical} no aplica el Modelo 349 — el regimen es IPSI (Impuesto sobre la "
                    "Produccion, los Servicios y la Importacion), no IVA. Las operaciones con UE se tratan "
                    "como exportaciones."
                ),
            }

        # ----- Parse operaciones -----
        ops, parse_errors = _build_operaciones(operaciones or [])
        if not ops:
            return {
                "success": False,
                "error": "sin_operaciones_validas",
                "errores_parse": parse_errors,
                "formatted_response": (
                    "No se han recibido operaciones intracomunitarias validas. "
                    + (" ".join(parse_errors) if parse_errors else "")
                ),
            }

        calc = Modelo349Calculator()

        # ----- Validacion sintactica de NIF-IVA -----
        nif_validations: List[Dict[str, Any]] = []
        for op in ops:
            ok_format, country, motivo = calc.validate_nif_iva_format(op.nif_operador)
            nif_validations.append({
                "nif_iva": calc.normalize_nif_iva(op.nif_operador),
                "country": country,
                "format_ok": ok_format,
                "motivo": motivo,
                "vies": None,
            })

        # ----- Validacion VIES opcional -----
        vies_warnings: List[str] = []
        if validar_vies:
            for entry in nif_validations:
                if not entry["format_ok"]:
                    continue
                vies_result = await calc.validate_nif_iva_vies(entry["nif_iva"])
                entry["vies"] = vies_result
                if vies_result.get("vies_unavailable"):
                    vies_warnings.append(
                        f"VIES no disponible para {entry['nif_iva']}: {vies_result.get('warning')}"
                    )
                elif not vies_result.get("valid"):
                    vies_warnings.append(
                        f"VIES marca como NO valido el NIF-IVA {entry['nif_iva']} "
                        f"({vies_result.get('error') or 'no encontrado'})."
                    )

        formato_invalidos = [v for v in nif_validations if not v["format_ok"]]

        # ----- Periodicidad -----
        periodicidad_info = calc.detect_periodicidad(
            operaciones_actual=ops,
            importes_4_trimestres_anteriores=importes_4_trimestres_anteriores,
            forzar_anual=forzar_anual,
        )
        periodicidad = periodicidad_info["periodicidad"]
        plazo = calc.plazo_presentacion(periodicidad, periodo, year)

        # ----- Resumen por clave -----
        resumen = calc.build_resumen(ops)

        # ----- Cuadre 303 -----
        cuadre_dict: Optional[Dict[str, Any]] = None
        if casillas_303:
            cuadre = calc.cuadrar_con_303(operaciones_349=ops, casillas_303=casillas_303)
            cuadre_dict = {
                "diff_entregas_bienes": cuadre.diff_entregas_bienes,
                "diff_adquisiciones_bienes": cuadre.diff_adquisiciones_bienes,
                "servicios_prestados_349": cuadre.diff_servicios_prestados,
                "servicios_adquiridos_349": cuadre.diff_servicios_adquiridos,
                "warnings": cuadre.warnings,
                "cuadre_ok": cuadre.cuadre_ok,
            }

        # ----- Formatted response -----
        periodo_label = _periodo_label(periodicidad, periodo, year)
        totales = resumen["totales"]
        por_clave = resumen["por_clave"]

        lines: List[str] = []
        lines.append(f"**Modelo 349 — Declaracion recapitulativa intracomunitaria — {periodo_label}**")
        lines.append(f"Periodicidad detectada: **{periodicidad}** ({periodicidad_info['motivo']})")
        lines.append(f"Plazo de presentacion: {plazo}")
        if ccaa_canonical:
            lines.append(f"CCAA declarante: {ccaa_canonical}")
        lines.append("")

        lines.append("**Resumen por clave**")
        labels_clave = {
            "E": "Entregas intracomunitarias de bienes",
            "A": "Adquisiciones intracomunitarias de bienes",
            "T": "Operaciones triangulares",
            "S": "Prestaciones intracomunitarias de servicios",
            "I": "Adquisiciones intracomunitarias de servicios",
            "M": "Entregas posteriores a importacion",
            "H": "Representante en entregas tras importacion",
            "R": "Transferencias consignacion (call-off stock)",
            "D": "Devoluciones consignacion",
            "C": "Sustitucion adquirente consignacion",
            "N": "Rectificaciones",
        }
        for clave in CLAVES_VALIDAS:
            data = por_clave[clave]
            if data["n_operaciones"] > 0:
                lines.append(
                    f"- [{clave}] {labels_clave[clave]}: {data['importe']:,.2f} EUR "
                    f"({data['n_operaciones']} ops, {data['n_operadores']} operadores)"
                )

        lines.append("")
        lines.append("**Totales agregados**")
        lines.append(f"- Entregas bienes (E+T+M+H): {totales['entregas_bienes']:,.2f} EUR")
        lines.append(f"- Adquisiciones bienes (A): {totales['adquisiciones_bienes']:,.2f} EUR")
        lines.append(f"- Servicios prestados (S): {totales['servicios_prestados']:,.2f} EUR")
        lines.append(f"- Servicios adquiridos (I): {totales['servicios_adquiridos']:,.2f} EUR")
        lines.append(f"- Volumen relevante (umbral 50.000 EUR): {totales['volumen_relevante']:,.2f} EUR")
        lines.append(f"- Total general (todas las claves): {totales['total_general']:,.2f} EUR")
        lines.append(f"- Operadores unicos: {resumen['operadores_unicos']}")
        lines.append(f"- Operaciones declaradas: {resumen['operaciones_count']}")

        if formato_invalidos:
            lines.append("")
            lines.append("**Avisos NIF-IVA (formato invalido)**")
            for v in formato_invalidos:
                lines.append(f"- {v['nif_iva']} ({v['country'] or 'sin pais'}): {v['motivo']}")

        if vies_warnings:
            lines.append("")
            lines.append("**Avisos VIES**")
            for w in vies_warnings:
                lines.append(f"- {w}")

        if cuadre_dict:
            lines.append("")
            lines.append("**Cuadre 303 <-> 349**")
            if cuadre_dict["cuadre_ok"]:
                lines.append("- Cuadre OK (diferencias dentro de tolerancia 0,5 EUR).")
            else:
                for w in cuadre_dict["warnings"]:
                    lines.append(f"- {w}")

        if parse_errors:
            lines.append("")
            lines.append("**Operaciones descartadas**")
            for err in parse_errors:
                lines.append(f"- {err}")

        lines.append("")
        lines.append(
            "Calculo informativo basado en Orden EHA/769/2010 y Reglamento IVA RD 1624/1992. "
            "La presentacion oficial requiere el formulario telematico de Sede AEAT."
        )

        formatted_response = "\n".join(lines)

        logger.info(
            "Modelo 349 calculated: periodicidad=%s, periodo=%s %s, ops=%d, "
            "operadores=%d, volumen_relevante=%.2f, cuadre_ok=%s",
            periodicidad, periodo, year, resumen["operaciones_count"],
            resumen["operadores_unicos"], totales["volumen_relevante"],
            cuadre_dict["cuadre_ok"] if cuadre_dict else "n/a",
        )

        return {
            "success": True,
            "modelo": "349",
            "periodicidad": periodicidad,
            "periodicidad_motivo": periodicidad_info["motivo"],
            "periodo": periodo,
            "year": year,
            "ccaa": ccaa_canonical,
            "plazo": plazo,
            "resumen": resumen,
            "totales": totales,
            "nif_validations": nif_validations,
            "formato_invalidos": formato_invalidos,
            "vies_warnings": vies_warnings,
            "cuadre_303": cuadre_dict,
            "errores_parse": parse_errors,
            "formatted_response": formatted_response,
        }

    except Exception as exc:  # noqa: BLE001
        logger.error("Error calculating Modelo 349: %s", exc, exc_info=True)
        return {
            "success": False,
            "error": str(exc),
            "formatted_response": f"Error al calcular el Modelo 349: {exc}",
        }
