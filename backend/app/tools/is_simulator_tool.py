"""
IS Simulator Tool for TaxIA.

Provides function calling capability for the LLM to run a complete
Impuesto sobre Sociedades simulation (Modelo 200).
"""
from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)

# Tool definition for OpenAI function calling
IS_SIMULATOR_TOOL = {
    "type": "function",
    "function": {
        "name": "simulate_is",
        "description": """Simulación del Impuesto sobre Sociedades (Modelo 200). Usa SIEMPRE esta función
cuando el usuario hable de su empresa (SL, SLP, SA), sociedad, impuesto de sociedades o Modelo 200.

Calcula la liquidación IS completa: resultado contable → ajustes → base imponible → cuota → deducciones → resultado.
Soporta 7 regímenes: común + 4 forales (Araba, Bizkaia, Gipuzkoa, Navarra) + ZEC Canarias + Ceuta/Melilla.

IMPORTANTE: NO usar esta herramienta para autónomos personas físicas (esos tributan por IRPF con simulate_irpf).
Solo para sociedades mercantiles (SL, SLP, SA, cooperativas).""",
        "parameters": {
            "type": "object",
            "properties": {
                "resultado_contable": {
                    "type": "number",
                    "description": "Resultado contable del ejercicio (ingresos - gastos según contabilidad). Puede ser negativo."
                },
                "territorio": {
                    "type": "string",
                    "description": "Territorio fiscal: Madrid, Barcelona, Bizkaia, Gipuzkoa, Araba, Navarra, Canarias, Ceuta, Melilla, etc."
                },
                "tipo_entidad": {
                    "type": "string",
                    "enum": ["sl", "slp", "sa", "nueva_creacion"],
                    "description": "Tipo de entidad: sl (Sociedad Limitada), slp (Sociedad Limitada Profesional), sa (Sociedad Anónima), nueva_creacion (primeros ejercicios con BI positiva)."
                },
                "facturacion_anual": {
                    "type": "number",
                    "description": "Facturación anual de la empresa. Si <1M → tramos pyme (23%+25% común). Si >10M → pago fraccionado al 24%."
                },
                "ejercicios_con_bi_positiva": {
                    "type": "integer",
                    "description": "Número de ejercicios con base imponible positiva. Si <=2 y tipo_entidad='nueva_creacion' → tipo reducido 15%/20%."
                },
                "gastos_no_deducibles": {
                    "type": "number",
                    "description": "Gastos contabilizados que no son deducibles fiscalmente (multas, sanciones, liberalidades, etc.)."
                },
                "ajustes_negativos": {
                    "type": "number",
                    "description": "Ajustes extracontables negativos (ingresos contabilizados no imputables fiscalmente)."
                },
                "amortizacion_contable": {
                    "type": "number",
                    "description": "Amortización registrada en contabilidad."
                },
                "amortizacion_fiscal": {
                    "type": "number",
                    "description": "Amortización según tablas fiscales. Si > contable → ajuste positivo."
                },
                "bins_pendientes": {
                    "type": "number",
                    "description": "Bases imponibles negativas de ejercicios anteriores pendientes de compensar."
                },
                "gasto_id": {
                    "type": "number",
                    "description": "Gasto en I+D del ejercicio (Art. 35.1 LIS). Deducción del 25%."
                },
                "gasto_it": {
                    "type": "number",
                    "description": "Gasto en innovación tecnológica (Art. 35.2 LIS). Deducción del 12%."
                },
                "incremento_ffpp": {
                    "type": "number",
                    "description": "Incremento de fondos propios para reserva de capitalización (Art. 25 LIS)."
                },
                "donativos": {
                    "type": "number",
                    "description": "Donativos a entidades acogidas a la Ley 49/2002 (mecenazgo). Deducción del 35%."
                },
                "empleados_discapacidad_33": {
                    "type": "integer",
                    "description": "Número de empleados con discapacidad >=33%. Deducción de 9.000 EUR/empleado."
                },
                "empleados_discapacidad_65": {
                    "type": "integer",
                    "description": "Número de empleados con discapacidad >=65%. Deducción de 12.000 EUR/empleado."
                },
                "dotacion_ric": {
                    "type": "number",
                    "description": "Dotación a la Reserva para Inversiones en Canarias (RIC). Reduce la BI."
                },
                "es_zec": {
                    "type": "boolean",
                    "description": "true si la empresa está inscrita en la Zona Especial Canaria (ZEC). Tipo del 4%."
                },
                "rentas_ceuta_melilla": {
                    "type": "number",
                    "description": "Rentas obtenidas en Ceuta o Melilla para bonificación del 50% (Art. 33.6 LIS)."
                },
                "retenciones_ingresos_cuenta": {
                    "type": "number",
                    "description": "Retenciones e ingresos a cuenta soportados durante el ejercicio."
                },
                "pagos_fraccionados_realizados": {
                    "type": "number",
                    "description": "Pagos fraccionados del Modelo 202 realizados durante el ejercicio."
                },
                "ingresos_explotacion": {
                    "type": "number",
                    "description": "Ingresos totales de explotación (alternativa a resultado_contable)."
                },
                "gastos_explotacion": {
                    "type": "number",
                    "description": "Gastos totales de explotación (alternativa a resultado_contable)."
                },
            },
            "required": ["territorio"]
        }
    }
}


async def simulate_is_tool(
    territorio: str = "Madrid",
    resultado_contable: float = 0.0,
    tipo_entidad: str = "sl",
    facturacion_anual: float = 0.0,
    ejercicios_con_bi_positiva: int = 10,
    gastos_no_deducibles: float = 0.0,
    ajustes_negativos: float = 0.0,
    amortizacion_contable: float = 0.0,
    amortizacion_fiscal: float | None = None,
    bins_pendientes: float = 0.0,
    gasto_id: float = 0.0,
    gasto_it: float = 0.0,
    incremento_ffpp: float = 0.0,
    donativos: float = 0.0,
    empleados_discapacidad_33: int = 0,
    empleados_discapacidad_65: int = 0,
    dotacion_ric: float = 0.0,
    es_zec: bool = False,
    rentas_ceuta_melilla: float = 0.0,
    retenciones_ingresos_cuenta: float = 0.0,
    pagos_fraccionados_realizados: float = 0.0,
    ingresos_explotacion: float | None = None,
    gastos_explotacion: float | None = None,
) -> Dict[str, Any]:
    """Execute IS simulation and return formatted result for LLM."""
    try:
        from app.utils.is_simulator import ISSimulator, ISInput
        from app.utils.ccaa_constants import normalize_ccaa

        ccaa = normalize_ccaa(territorio)

        logger.info(
            "Simulating IS: resultado_contable=%s, territorio=%s, tipo=%s",
            resultado_contable, ccaa, tipo_entidad,
        )

        inp = ISInput(
            resultado_contable=resultado_contable,
            territorio=ccaa,
            tipo_entidad=tipo_entidad,
            facturacion_anual=facturacion_anual,
            ejercicios_con_bi_positiva=ejercicios_con_bi_positiva,
            gastos_no_deducibles=gastos_no_deducibles,
            ajustes_negativos=ajustes_negativos,
            amortizacion_contable=amortizacion_contable,
            amortizacion_fiscal=amortizacion_fiscal,
            bins_pendientes=bins_pendientes,
            gasto_id=gasto_id,
            gasto_it=gasto_it,
            incremento_ffpp=incremento_ffpp,
            donativos=donativos,
            empleados_discapacidad_33=empleados_discapacidad_33,
            empleados_discapacidad_65=empleados_discapacidad_65,
            dotacion_ric=dotacion_ric,
            es_zec=es_zec,
            rentas_ceuta_melilla=rentas_ceuta_melilla,
            retenciones_ingresos_cuenta=retenciones_ingresos_cuenta,
            pagos_fraccionados_realizados=pagos_fraccionados_realizados,
            ingresos_explotacion=ingresos_explotacion,
            gastos_explotacion=gastos_explotacion,
        )

        result = ISSimulator.calculate(inp)

        # Also calculate 202 in both modalities
        r202_art40_2 = ISSimulator.calcular_202(
            modalidad="art40_2",
            cuota_integra_ultimo=result.cuota_integra,
            deducciones_bonificaciones_ultimo=result.deducciones_total + result.bonificaciones_total,
            retenciones_ultimo=result.retenciones,
        )
        r202_art40_3 = ISSimulator.calcular_202(
            modalidad="art40_3",
            base_imponible_periodo=result.base_imponible,
            facturacion_anual=facturacion_anual,
            territorio=ccaa,
        )

        return {
            "resultado_contable": result.resultado_contable,
            "ajustes_positivos": result.ajustes_positivos,
            "ajustes_negativos": result.ajustes_negativos,
            "reserva_capitalizacion": result.reserva_capitalizacion,
            "base_imponible_previa": result.base_imponible_previa,
            "compensacion_bins": result.compensacion_bins,
            "base_imponible": result.base_imponible,
            "bin_generada": result.bin_generada,
            "tipo_gravamen_aplicado": result.tipo_gravamen_aplicado,
            "cuota_integra": result.cuota_integra,
            "deducciones_detalle": result.deducciones_detalle,
            "deducciones_total": result.deducciones_total,
            "bonificaciones_total": result.bonificaciones_total,
            "cuota_liquida": result.cuota_liquida,
            "retenciones": result.retenciones,
            "pagos_fraccionados": result.pagos_fraccionados,
            "resultado_liquidacion": result.resultado_liquidacion,
            "tipo": result.tipo,
            "tipo_efectivo": result.tipo_efectivo,
            "regimen": result.regimen,
            "territorio": result.territorio,
            "pago_202_art40_2": r202_art40_2.pago_trimestral,
            "pago_202_art40_3": r202_art40_3.pago_trimestral,
            "disclaimer": "Este cálculo es orientativo y no sustituye asesoramiento profesional.",
        }

    except Exception as e:
        logger.error("Error simulating IS: %s", e, exc_info=True)
        return {
            "error": f"Error al simular el Impuesto sobre Sociedades: {str(e)}",
            "disclaimer": "Este cálculo es orientativo y no sustituye asesoramiento profesional.",
        }
