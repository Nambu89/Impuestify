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
from datetime import datetime
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
                },
                "ceuta_melilla": {
                    "type": "boolean",
                    "description": "true si el contribuyente reside y trabaja en Ceuta o Melilla. Aplica deduccion del 60% sobre la cuota integra (Art. 68.4 LIRPF). Usar true cuando la CCAA sea Ceuta o Melilla."
                },
                "ingresos_actividad": {
                    "type": "number",
                    "description": "Ingresos brutos anuales de actividad economica (autonomo/empresario). Es la facturacion total (base imponible, SIN IVA/IGIC). Si el usuario es autonomo, usar este campo EN VEZ DE ingresos_trabajo. Si es asalariado y autonomo a la vez, usar ambos campos."
                },
                "gastos_actividad": {
                    "type": "number",
                    "description": "Gastos deducibles anuales de la actividad economica (suministros, alquiler local, seguros, material, servicios profesionales, viajes, formacion, marketing, etc.). NO incluir cuota de autonomo (campo separado) ni amortizaciones (campo separado)."
                },
                "cuota_autonomo_anual": {
                    "type": "number",
                    "description": "Cuota de Seguridad Social como autonomo pagada en el ano (ej: 300 EUR/mes x 12 = 3.600 EUR). Es gasto deducible al 100%. Si no se indica, preguntar al usuario."
                },
                "amortizaciones_actividad": {
                    "type": "number",
                    "description": "Amortizaciones de bienes de inversion afectos a la actividad (vehiculo, ordenador, mobiliario, maquinaria). Segun tablas oficiales de amortizacion."
                },
                "estimacion_actividad": {
                    "type": "string",
                    "enum": ["directa_normal", "directa_simplificada", "objetiva"],
                    "description": "'directa_simplificada' (default, mayoria de autonomos): anade 5% gastos dificil justificacion (max 2.000 EUR). 'directa_normal': mas detallada, permite provisiones. 'objetiva': modulos (no soportado aun)."
                },
                "inicio_actividad": {
                    "type": "boolean",
                    "description": "true si el autonomo ha iniciado su actividad en el ano actual o anterior Y no ha tenido rendimiento neto positivo antes. Aplica reduccion del 20% (Art. 32.3 LIRPF)."
                },
                "un_solo_cliente": {
                    "type": "boolean",
                    "description": "true si mas del 75% de los ingresos del autonomo provienen de un solo cliente (autonomo economicamente dependiente/TRADE). Aplica reduccion similar a rendimientos del trabajo (Art. 32.2 LIRPF)."
                },
                "retenciones_actividad": {
                    "type": "number",
                    "description": "Retenciones IRPF practicadas por clientes en facturas del autonomo (15% general, 7% nuevos autonomos primeros 3 anos). Total anual acumulado."
                },
                "pagos_fraccionados_130": {
                    "type": "number",
                    "description": "Total de pagos fraccionados del Modelo 130 realizados durante el ano (suma de los 4 trimestres). Se descuentan de la cuota total para calcular el resultado final (a pagar o a devolver)."
                },
                "aportaciones_plan_pensiones": {
                    "type": "number",
                    "description": "Aportaciones propias del contribuyente a planes de pensiones en el año (máx 1.500€ deducibles). Reduce la base imponible general."
                },
                "aportaciones_plan_pensiones_empresa": {
                    "type": "number",
                    "description": "Aportaciones de la empresa al plan de pensiones del empleado. Conjuntamente con las propias, máx 8.500€ (y máx 30% renta neta)."
                },
                "hipoteca_pre2013": {
                    "type": "boolean",
                    "description": "true si el contribuyente tiene hipoteca sobre su vivienda habitual contratada ANTES del 1 de enero de 2013 (deducción suprimida para hipotecas posteriores). Si true, pasará `capital_amortizado_hipoteca` e `intereses_hipoteca`."
                },
                "capital_amortizado_hipoteca": {
                    "type": "number",
                    "description": "Capital amortizado de la hipoteca pre-2013 en el año (cuotas de principal pagadas). Solo relevante si hipoteca_pre2013=true."
                },
                "intereses_hipoteca": {
                    "type": "number",
                    "description": "Intereses pagados de la hipoteca pre-2013 en el año. Solo relevante si hipoteca_pre2013=true. Base deducción = capital_amortizado + intereses, máx 9.040€. Deducción = 15%."
                },
                "madre_trabajadora_ss": {
                    "type": "boolean",
                    "description": "true si la madre (o contribuyente principal) trabaja y cotiza a la Seguridad Social, y tiene hijos menores de 3 años. Habilita la deducción por maternidad (1.200€/hijo <3 años)."
                },
                "gastos_guarderia_anual": {
                    "type": "number",
                    "description": "Gastos anuales en guardería o centros de educación infantil autorizados para hijos menores de 3 años. Permite deducción adicional a la de maternidad (hasta 1.000€ extra por hijo)."
                },
                "familia_numerosa": {
                    "type": "boolean",
                    "description": "true si el contribuyente tiene título de familia numerosa reconocido. Deducción: 1.200€/año (general) o 2.400€ (especial)."
                },
                "tipo_familia_numerosa": {
                    "type": "string",
                    "enum": ["general", "especial"],
                    "description": "'general' = 3 hijos (1.200€). 'especial' = 5+ hijos o 4 con discapacidad (2.400€). Solo relevante si familia_numerosa=true."
                },
                "donativos_ley_49_2002": {
                    "type": "number",
                    "description": "Total de donativos realizados en el año a entidades acogidas a la Ley 49/2002 (ONGs, fundaciones, iglesias con convenio). Deducción: 80% primeros 250€ + 40% exceso (o 45% si donativo_recurrente=true)."
                },
                "donativo_recurrente": {
                    "type": "boolean",
                    "description": "true si el contribuyente lleva 2 o más años consecutivos donando a la misma entidad con importe igual o superior. Aumenta el tipo del exceso al 45%."
                },
                "retenciones_trabajo": {
                    "type": "number",
                    "description": "Total de retenciones IRPF soportadas en nómina durante el año. Necesario para calcular si la declaración sale a pagar o a devolver."
                },
                "retenciones_alquiler": {
                    "type": "number",
                    "description": "Retenciones por rendimientos de alquiler (19%). Necesario para el resultado final de la declaración."
                },
                "retenciones_ahorro": {
                    "type": "number",
                    "description": "Retenciones por rendimientos del capital mobiliario (intereses, dividendos). Necesario para el resultado final."
                },
                "tributacion_conjunta": {
                    "type": "boolean",
                    "description": "true si la declaración se presenta de forma conjunta (matrimonio o monoparental). Aplica reducción sobre la base imponible general: 3.400€ para matrimonios y 2.150€ para unidades monoparentales (Art. 84 LIRPF)."
                },
                "tipo_unidad_familiar": {
                    "type": "string",
                    "enum": ["matrimonio", "monoparental"],
                    "description": "'matrimonio' = cónyuge e hijos (reducción 3.400€). 'monoparental' = padre/madre con hijos sin cónyuge (reducción 2.150€). Solo relevante si tributacion_conjunta=true."
                },
                "alquiler_habitual_pre2015": {
                    "type": "boolean",
                    "description": "true si el contribuyente pagaba alquiler por su vivienda habitual con contrato anterior a 1 de enero de 2015 y sigue aplicando la deducción transitoria (DT 15ª LIRPF). La deducción es el 10,05% del alquiler pagado (máx. base 9.040€), con reducción lineal si BI entre 17.707,20€ y 24.107,20€. Desaparece con BI >= 24.107,20€."
                },
                "alquiler_pagado_anual": {
                    "type": "number",
                    "description": "Total de alquiler pagado por el contribuyente como inquilino en el año (no confundir con ingresos_alquiler que son rentas percibidas como propietario). Solo relevante si alquiler_habitual_pre2015=true."
                },
                "valor_catastral_segundas_viviendas": {
                    "type": "number",
                    "description": "Valor catastral de inmuebles urbanos en propiedad distintos de la vivienda habitual que no generan rendimientos de alquiler (ej: segunda residencia vacía, plaza de garaje no alquilada). El fisco imputa un 1,1% (o 2% si el catastro no ha sido revisado desde 1994) como renta en la base general (Art. 85 LIRPF)."
                },
                "valor_catastral_revisado_post1994": {
                    "type": "boolean",
                    "description": "true (default) si el valor catastral del inmueble fue revisado a partir de 1994 → imputación del 1,1%. false si el catastro es anterior a 1994 → imputación del 2%. Solo relevante si valor_catastral_segundas_viviendas > 0."
                },
                "ganancias_acciones": {
                    "type": "number",
                    "description": "Ganancias brutas por venta de acciones o participaciones en el año (casilla 0338). Base del ahorro."
                },
                "perdidas_acciones": {
                    "type": "number",
                    "description": "Pérdidas por venta de acciones (casilla 0339). Compensan las ganancias de acciones."
                },
                "ganancias_reembolso_fondos": {
                    "type": "number",
                    "description": "Ganancias por reembolso de participaciones en fondos de inversión (casilla 0320). Base del ahorro."
                },
                "perdidas_reembolso_fondos": {
                    "type": "number",
                    "description": "Pérdidas por reembolso de fondos de inversión. Compensan las ganancias de fondos."
                },
                "ganancias_derivados": {
                    "type": "number",
                    "description": "Ganancias por operaciones con derivados, CFDs o Forex (casilla 0353). Base del ahorro."
                },
                "perdidas_derivados": {
                    "type": "number",
                    "description": "Pérdidas por derivados/CFDs/Forex (casilla 0354). Compensan las ganancias de derivados."
                },
                "cripto_ganancia_neta": {
                    "type": "number",
                    "description": "Ganancia patrimonial neta por transmisión de criptomonedas (casilla 1814). Base del ahorro. Usar cuando el usuario dice que ha vendido Bitcoin, Ethereum u otras criptomonedas con beneficio."
                },
                "cripto_perdida_neta": {
                    "type": "number",
                    "description": "Pérdida patrimonial neta por transmisión de criptomonedas (casilla 1813). Compensa las ganancias cripto del mismo ejercicio."
                },
                "premios_metalico_privados": {
                    "type": "number",
                    "description": "Premios en metálico de juegos, apuestas o concursos privados (casilla 0282). Van a la base imponible GENERAL (no al ahorro). Ejemplos: apuestas deportivas online, premios de concursos televisivos, póker online."
                },
                "premios_especie_privados": {
                    "type": "number",
                    "description": "Premios en especie de juegos/apuestas privados, valorados a precio de mercado (casilla 0283). Base general."
                },
                "perdidas_juegos_privados": {
                    "type": "number",
                    "description": "Pérdidas en juegos/apuestas privados (casilla 0287). Solo compensan ganancias del mismo tipo, no otras rentas."
                },
                "premios_metalico_publicos": {
                    "type": "number",
                    "description": "Premios en metálico de loterías del Estado, ONCE o Cruz Roja (casilla 0292). Exentos los primeros 40.000 EUR; el exceso tributa al 20% como gravamen especial separado (Art. 75bis LIRPF). NO van a la base general."
                },
                "premios_especie_publicos": {
                    "type": "number",
                    "description": "Premios en especie de loterías públicas, valorados a precio de mercado (casilla 0293). Mismo tratamiento que premios_metalico_publicos."
                },
                # --- Fase XSD: Gastos granulares actividad (casillas 0181-0217) ---
                "gastos_compras": {
                    "type": "number",
                    "description": "Compras de mercaderías y materias primas (casilla 0181). Gasto deducible de actividad económica en estimación directa."
                },
                "gastos_sueldos": {
                    "type": "number",
                    "description": "Sueldos y salarios del personal empleado (casilla 0190). Solo para autónomos con trabajadores a cargo."
                },
                "gastos_ss_empresa": {
                    "type": "number",
                    "description": "Seguridad Social a cargo de la empresa (casilla 0191). Cuotas SS del empresario por sus empleados."
                },
                "gastos_arrendamientos": {
                    "type": "number",
                    "description": "Alquileres de locales, oficinas y bienes afectos a la actividad (casilla 0196)."
                },
                "gastos_reparaciones_actividad": {
                    "type": "number",
                    "description": "Gastos de reparación y conservación de bienes afectos a la actividad (casilla 0197)."
                },
                "gastos_servicios_profesionales": {
                    "type": "number",
                    "description": "Servicios de profesionales independientes: gestoría, abogados, consultores (casilla 0198)."
                },
                "gastos_tributos": {
                    "type": "number",
                    "description": "Tributos y tasas deducibles: IAE, IBI de local, tasas municipales (casilla 0201)."
                },
                "gastos_financieros_actividad": {
                    "type": "number",
                    "description": "Gastos financieros de la actividad: intereses de préstamos afectos (casilla 0203)."
                },
                "gastos_suministros_actividad": {
                    "type": "number",
                    "description": "Suministros afectos a la actividad: luz, agua, internet, teléfono (casilla 0205). Para trabajadores en domicilio, hasta el 30% de la parte proporcional del inmueble."
                },
                "gastos_otros": {
                    "type": "number",
                    "description": "Otros gastos deducibles no clasificados en categorías anteriores (casilla 0217)."
                },
                "gastos_publicidad": {
                    "type": "number",
                    "description": "Gastos de publicidad, marketing y promoción de la actividad (va en casilla 0217)."
                },
                "gastos_formacion": {
                    "type": "number",
                    "description": "Gastos de formación y actualización profesional relacionados con la actividad (va en 0217)."
                },
                "gastos_software": {
                    "type": "number",
                    "description": "Licencias de software, suscripciones SaaS y herramientas digitales afectas (va en 0217)."
                },
                # --- Fase XSD: Ingresos granulares actividad (casillas 0171-0179) ---
                "ingresos_ventas": {
                    "type": "number",
                    "description": "Ingresos por ventas de bienes y prestación de servicios (casilla 0171). Si se proporciona este campo junto con otros ingresos granulares, sustituyen a ingresos_actividad."
                },
                "ingresos_subvenciones": {
                    "type": "number",
                    "description": "Subvenciones de explotación y de capital afectas a la actividad (casilla 0173)."
                },
                "ingresos_financieros_actividad": {
                    "type": "number",
                    "description": "Ingresos financieros de la actividad económica (casilla 0175)."
                },
                "ingresos_otros_actividad": {
                    "type": "number",
                    "description": "Otros ingresos de la actividad no clasificados en categorías anteriores (casilla 0179)."
                },
                # --- Fase XSD: Royalties / Derechos de autor ---
                "ingresos_derechos_autor": {
                    "type": "number",
                    "description": "Ingresos por royalties o derechos de autor (casilla 0128). Aplicable a creadores de contenido, escritores, músicos, artistas. Se suman al rendimiento de actividad. Si reduccion_derechos_autor=true, se aplica reducción del 30% (Art. 32.1 LIRPF)."
                },
                "reduccion_derechos_autor": {
                    "type": "boolean",
                    "description": "true si los derechos de autor se han generado en más de 2 años (Art. 32.1 LIRPF). Aplica reducción del 30% sobre ingresos_derechos_autor."
                },
                "retencion_derechos_autor": {
                    "type": "number",
                    "description": "Retenciones IRPF practicadas sobre los ingresos por derechos de autor (19% general). Se suman a retenciones_actividad para el cálculo del resultado final."
                },
                # --- Fase XSD: Estimacion objetiva (modulos) ---
                "modulos_rendimiento_neto": {
                    "type": "number",
                    "description": "Rendimiento neto previo calculado por módulos (estimacion_actividad='objetiva'). Es el resultado de aplicar los módulos de la AEAT a la actividad del autónomo. Solo relevante si estimacion_actividad='objetiva'."
                },
                "modulos_indice_corrector": {
                    "type": "number",
                    "description": "Índice corrector aplicable en estimación objetiva (default 1.0). Valores habituales: 0.75 (inicio actividad), 0.90 (determinadas actividades). Solo si estimacion_actividad='objetiva'."
                },
                # --- Fase XSD: WorkIncome nuevos params ---
                "defensa_juridica": {
                    "type": "number",
                    "description": "Gastos de defensa jurídica del trabajador frente al empleador (casilla 0016). Deducible con límite de 300 EUR/año."
                },
                "incremento_desempleado_nuevo_empleo": {
                    "type": "number",
                    "description": "Incremento de gastos deducibles del trabajo por aceptar empleo en municipio distinto siendo desempleado (casilla 0020). Hasta 2.000 EUR adicionales sobre los 2.000 EUR base."
                },
                "incremento_discapacidad_activo": {
                    "type": "number",
                    "description": "Incremento de gastos deducibles por discapacidad del trabajador activo (casilla 0021). 3.500 EUR si discapacidad >=33%; 7.750 EUR si >=65% o movilidad reducida."
                },
                # --- Fase XSD: Gastos granulares alquiler (casillas 0105-0126) ---
                "gastos_financiacion_alquiler": {
                    "type": "number",
                    "description": "Intereses y gastos de financiación del inmueble alquilado (casilla 0105). Incluye intereses hipotecarios. Limitados al importe de los ingresos íntegros (Art. 23.1.a LIRPF)."
                },
                "gastos_reparacion_alquiler": {
                    "type": "number",
                    "description": "Gastos de reparación y conservación del inmueble alquilado (casilla 0106). Limitados conjuntamente con financiación al importe de ingresos íntegros."
                },
                "gastos_comunidad_alquiler": {
                    "type": "number",
                    "description": "Cuotas de comunidad de propietarios del inmueble alquilado (casilla 0109). Sin límite de importe."
                },
                "ibi_alquiler": {
                    "type": "number",
                    "description": "IBI (Impuesto sobre Bienes Inmuebles) del inmueble alquilado. Deducible sin límite."
                },
                "gastos_seguros_alquiler": {
                    "type": "number",
                    "description": "Primas de seguro del inmueble alquilado: hogar, responsabilidad civil, impago (casilla 0114). Sin límite."
                },
                "gastos_suministros_alquiler": {
                    "type": "number",
                    "description": "Suministros del inmueble alquilado a cargo del propietario: agua, luz, gas (casilla 0113). Sin límite."
                },
                "pagadores": {
                    "type": "array",
                    "description": "Lista de pagadores/empleadores con desglose de retribuciones. Si el usuario menciona varios pagadores, usar este campo.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "nombre": {"type": "string", "description": "Nombre del pagador"},
                            "retribuciones_dinerarias": {"type": "number", "description": "Retribuciones dinerarias brutas de este pagador"},
                            "retenciones": {"type": "number", "description": "Retenciones IRPF de este pagador"},
                            "gastos_deducibles": {"type": "number", "description": "Gastos deducibles (SS) de este pagador"},
                        }
                    }
                },
                "num_pagadores": {
                    "type": "integer",
                    "description": "Numero de pagadores/empleadores del contribuyente. Si es > 1, puede afectar al limite de obligacion de declarar (15.876 EUR vs 22.000 EUR).",
                    "default": 1
                },
                "retribuciones_especie": {
                    "type": "number",
                    "description": "Retribuciones en especie recibidas (coche empresa, seguro medico, etc.). Se suman a la base imponible del trabajo.",
                    "default": 0
                },
                "ingresos_cuenta": {
                    "type": "number",
                    "description": "Ingresos a cuenta repercutidos al trabajador. Se suman a la base imponible del trabajo.",
                    "default": 0
                }
            },
            "required": ["comunidad_autonoma"]
        }
    }
}


async def simulate_irpf_tool(
    comunidad_autonoma: str,
    ingresos_trabajo: float = 0,
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
    ceuta_melilla: bool = False,
    # Activity income (autonomos)
    ingresos_actividad: float = 0,
    gastos_actividad: float = 0,
    cuota_autonomo_anual: float = 0,
    amortizaciones_actividad: float = 0,
    estimacion_actividad: str = "directa_simplificada",
    inicio_actividad: bool = False,
    un_solo_cliente: bool = False,
    retenciones_actividad: float = 0,
    pagos_fraccionados_130: float = 0,
    # Phase 1: Reductions & deductions
    aportaciones_plan_pensiones: float = 0,
    aportaciones_plan_pensiones_empresa: float = 0,
    hipoteca_pre2013: bool = False,
    capital_amortizado_hipoteca: float = 0,
    intereses_hipoteca: float = 0,
    madre_trabajadora_ss: bool = False,
    gastos_guarderia_anual: float = 0,
    familia_numerosa: bool = False,
    tipo_familia_numerosa: str = "general",
    donativos_ley_49_2002: float = 0,
    donativo_recurrente: bool = False,
    retenciones_trabajo: float = 0,
    retenciones_alquiler: float = 0,
    retenciones_ahorro: float = 0,
    # Phase 2: Tributación conjunta (Art. 84 LIRPF)
    tributacion_conjunta: bool = False,
    tipo_unidad_familiar: str = "matrimonio",
    # Phase 2: Alquiler vivienda habitual pre-2015 (DT 15ª LIRPF)
    alquiler_habitual_pre2015: bool = False,
    alquiler_pagado_anual: float = 0,
    # Phase 2: Rentas imputadas inmuebles (Art. 85 LIRPF)
    valor_catastral_segundas_viviendas: float = 0,
    valor_catastral_revisado_post1994: bool = True,
    # Fase 4: Ganancias patrimoniales del ahorro
    ganancias_acciones: float = 0,
    perdidas_acciones: float = 0,
    ganancias_reembolso_fondos: float = 0,
    perdidas_reembolso_fondos: float = 0,
    ganancias_derivados: float = 0,
    perdidas_derivados: float = 0,
    cripto_ganancia_neta: float = 0,
    cripto_perdida_neta: float = 0,
    # Fase 4: Juegos privados y loterías públicas
    premios_metalico_privados: float = 0,
    premios_especie_privados: float = 0,
    perdidas_juegos_privados: float = 0,
    premios_metalico_publicos: float = 0,
    premios_especie_publicos: float = 0,
    # Fase XSD: Gastos granulares actividad (casillas 0181-0217)
    gastos_compras: float = 0,
    gastos_sueldos: float = 0,
    gastos_ss_empresa: float = 0,
    gastos_arrendamientos: float = 0,
    gastos_reparaciones_actividad: float = 0,
    gastos_servicios_profesionales: float = 0,
    gastos_tributos: float = 0,
    gastos_financieros_actividad: float = 0,
    gastos_suministros_actividad: float = 0,
    gastos_otros: float = 0,
    gastos_publicidad: float = 0,
    gastos_formacion: float = 0,
    gastos_software: float = 0,
    # Fase XSD: Ingresos granulares actividad (casillas 0171-0179)
    ingresos_ventas: float = 0,
    ingresos_subvenciones: float = 0,
    ingresos_financieros_actividad: float = 0,
    ingresos_otros_actividad: float = 0,
    # Fase XSD: Royalties / Derechos de autor
    ingresos_derechos_autor: float = 0,
    reduccion_derechos_autor: bool = False,
    retencion_derechos_autor: float = 0,
    # Fase XSD: Estimacion objetiva (modulos)
    modulos_rendimiento_neto: float = 0,
    modulos_indice_corrector: float = 1.0,
    # Fase XSD: WorkIncome nuevos params
    defensa_juridica: float = 0,
    incremento_desempleado_nuevo_empleo: float = 0,
    incremento_discapacidad_activo: float = 0,
    # Fase XSD: Gastos granulares alquiler (casillas 0105-0126)
    gastos_financiacion_alquiler: float = 0,
    gastos_reparacion_alquiler: float = 0,
    gastos_comunidad_alquiler: float = 0,
    ibi_alquiler: float = 0,
    gastos_seguros_alquiler: float = 0,
    gastos_suministros_alquiler: float = 0,
    # Multi-pagador support
    pagadores: Optional[List[dict]] = None,
    num_pagadores: int = 1,
    retribuciones_especie: float = 0,
    ingresos_cuenta: float = 0,
) -> Dict[str, Any]:
    """Execute IRPF simulation and return formatted result."""
    try:
        from app.utils.irpf_simulator import IRPFSimulator
        from app.utils.ccaa_constants import normalize_ccaa
        from app.database.turso_client import get_db_client

        db = await get_db_client()
        ccaa = normalize_ccaa(comunidad_autonoma)

        # Auto-detect Ceuta/Melilla from CCAA if not explicitly set
        if not ceuta_melilla and ccaa.lower() in ("ceuta", "melilla"):
            ceuta_melilla = True

        # Multi-pagador aggregation: if pagadores list provided, aggregate totals
        if pagadores:
            ingresos_trabajo = sum(
                p.get("retribuciones_dinerarias", 0) + p.get("retribuciones_especie", 0) + p.get("ingresos_cuenta", 0)
                for p in pagadores
            )
            retenciones_trabajo = sum(p.get("retenciones", 0) for p in pagadores)
            ss_empleado = sum(p.get("gastos_deducibles", 0) for p in pagadores)
            num_pagadores = len(pagadores)

        logger.info(
            "Simulating IRPF: %s€ trabajo, %s, %s, ceuta_melilla=%s",
            ingresos_trabajo, ccaa, year, ceuta_melilla,
        )

        simulator = IRPFSimulator(db)

        # retencion_derechos_autor se suma a retenciones_actividad en el tool (no en el simulator)
        retenciones_actividad_total = retenciones_actividad + retencion_derechos_autor

        # Determine if granular rental expenses are provided
        # If any granular rental field > 0, use them; otherwise fall back to gastos_alquiler_total
        _rental_granulares_sum = (
            gastos_financiacion_alquiler + gastos_reparacion_alquiler
            + gastos_comunidad_alquiler + ibi_alquiler
            + gastos_seguros_alquiler + gastos_suministros_alquiler
        )
        _use_rental_granulares = _rental_granulares_sum > 0

        # Build shared kwargs for both simulate() calls (normal and fallback)
        _simulate_kwargs = dict(
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
            ceuta_melilla=ceuta_melilla,
            ingresos_actividad=ingresos_actividad,
            gastos_actividad=gastos_actividad,
            cuota_autonomo_anual=cuota_autonomo_anual,
            amortizaciones_actividad=amortizaciones_actividad,
            estimacion_actividad=estimacion_actividad,
            inicio_actividad=inicio_actividad,
            un_solo_cliente=un_solo_cliente,
            retenciones_actividad=retenciones_actividad_total,
            pagos_fraccionados_130=pagos_fraccionados_130,
            aportaciones_plan_pensiones=aportaciones_plan_pensiones,
            aportaciones_plan_pensiones_empresa=aportaciones_plan_pensiones_empresa,
            hipoteca_pre2013=hipoteca_pre2013,
            capital_amortizado_hipoteca=capital_amortizado_hipoteca,
            intereses_hipoteca=intereses_hipoteca,
            madre_trabajadora_ss=madre_trabajadora_ss,
            gastos_guarderia_anual=gastos_guarderia_anual,
            familia_numerosa=familia_numerosa,
            tipo_familia_numerosa=tipo_familia_numerosa,
            donativos_ley_49_2002=donativos_ley_49_2002,
            donativo_recurrente=donativo_recurrente,
            retenciones_alquiler=retenciones_alquiler,
            retenciones_ahorro=retenciones_ahorro,
            tributacion_conjunta=tributacion_conjunta,
            tipo_unidad_familiar=tipo_unidad_familiar,
            alquiler_habitual_pre2015=alquiler_habitual_pre2015,
            alquiler_pagado_anual=alquiler_pagado_anual,
            valor_catastral_segundas_viviendas=valor_catastral_segundas_viviendas,
            valor_catastral_revisado_post1994=valor_catastral_revisado_post1994,
            ganancias_acciones=ganancias_acciones,
            perdidas_acciones=perdidas_acciones,
            ganancias_reembolso_fondos=ganancias_reembolso_fondos,
            perdidas_reembolso_fondos=perdidas_reembolso_fondos,
            ganancias_derivados=ganancias_derivados,
            perdidas_derivados=perdidas_derivados,
            cripto_ganancia_neta=cripto_ganancia_neta,
            cripto_perdida_neta=cripto_perdida_neta,
            premios_metalico_privados=premios_metalico_privados,
            premios_especie_privados=premios_especie_privados,
            perdidas_juegos_privados=perdidas_juegos_privados,
            premios_metalico_publicos=premios_metalico_publicos,
            premios_especie_publicos=premios_especie_publicos,
            # Fase XSD: Gastos granulares actividad
            gastos_compras=gastos_compras,
            gastos_sueldos=gastos_sueldos,
            gastos_ss_empresa=gastos_ss_empresa,
            gastos_arrendamientos=gastos_arrendamientos,
            gastos_reparaciones_actividad=gastos_reparaciones_actividad,
            gastos_servicios_profesionales=gastos_servicios_profesionales,
            gastos_tributos=gastos_tributos,
            gastos_financieros_actividad=gastos_financieros_actividad,
            gastos_suministros_actividad=gastos_suministros_actividad,
            gastos_otros=gastos_otros,
            gastos_publicidad=gastos_publicidad,
            gastos_formacion=gastos_formacion,
            gastos_software=gastos_software,
            # Fase XSD: Ingresos granulares actividad
            ingresos_ventas=ingresos_ventas,
            ingresos_subvenciones=ingresos_subvenciones,
            ingresos_financieros_actividad=ingresos_financieros_actividad,
            ingresos_otros_actividad=ingresos_otros_actividad,
            # Fase XSD: Royalties
            ingresos_derechos_autor=ingresos_derechos_autor,
            reduccion_derechos_autor=reduccion_derechos_autor,
            # Fase XSD: Modulos
            modulos_rendimiento_neto=modulos_rendimiento_neto,
            modulos_indice_corrector=modulos_indice_corrector,
            # Fase XSD: WorkIncome
            defensa_juridica=defensa_juridica,
            incremento_desempleado_nuevo_empleo=incremento_desempleado_nuevo_empleo,
            incremento_discapacidad_activo=incremento_discapacidad_activo,
            # Fase XSD: Gastos granulares alquiler (solo si se proporcionan)
            gastos_financiacion_alquiler=gastos_financiacion_alquiler if _use_rental_granulares else 0,
            gastos_reparacion_alquiler=gastos_reparacion_alquiler if _use_rental_granulares else 0,
            gastos_comunidad_alquiler=gastos_comunidad_alquiler if _use_rental_granulares else 0,
            ibi_alquiler=ibi_alquiler if _use_rental_granulares else 0,
            gastos_seguros_alquiler=gastos_seguros_alquiler if _use_rental_granulares else 0,
            gastos_suministros_alquiler=gastos_suministros_alquiler if _use_rental_granulares else 0,
            # Multi-pagador / retribuciones especie
            retribuciones_especie=retribuciones_especie,
            ingresos_cuenta=ingresos_cuenta,
        )

        # Try requested year first, fallback to year-1 if no data
        effective_year = year
        year_warning = ""
        try:
            result = await simulator.simulate(
                jurisdiction=ccaa,
                year=year,
                **_simulate_kwargs,
            )
        except ValueError:
            # Year not available — fallback to previous year
            effective_year = year - 1
            logger.info("Year %s not available, falling back to %s", year, effective_year)
            year_warning = (
                f"No hay datos de tramos para {year}. "
                f"Calculo basado en tramos de {effective_year} (los tramos apenas cambian ano a ano)."
            )
            result = await simulator.simulate(
                jurisdiction=ccaa,
                year=effective_year,
                **_simulate_kwargs,
            )

        # Build formatted response
        formatted = _format_simulation_result(result, ccaa)
        if year_warning:
            formatted = f"⚠️ {year_warning}\n\n{formatted}"

        # --- Fase 4: Auto-discover deductions end-to-end ---
        try:
            from app.tools.deduction_discovery_tool import discover_deductions_tool

            # Pre-fill answers from simulation parameters
            ded_answers = {}
            if num_descendientes > 0:
                ded_answers["tiene_hijos"] = True
            if anios_nacimiento_desc:
                current_yr = datetime.now().year
                if any((current_yr - y) < 3 for y in anios_nacimiento_desc):
                    ded_answers["hijo_menor_3"] = True
            if num_ascendientes_65 > 0 or num_ascendientes_75 > 0:
                ded_answers["ascendiente_a_cargo"] = True
            if discapacidad_contribuyente >= 33:
                ded_answers["discapacidad_reconocida"] = True
            if ceuta_melilla:
                ded_answers["residente_ceuta_melilla"] = True

            ded_result = await discover_deductions_tool(
                ccaa=ccaa,
                tax_year=effective_year,
                answers=ded_answers,
            )
            if ded_result.get("success") and (ded_result.get("deductions_found", 0) > 0 or ded_result.get("maybe_eligible", 0) > 0):
                formatted += "\n\n---\n" + ded_result["formatted_response"]
                result["deductions"] = ded_result
        except Exception as e:
            logger.warning("Deduction discovery in simulation failed (non-fatal): %s", e)

        result["formatted_response"] = formatted
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
            f"Rendimiento del trabajo: {trabajo['ingresos_brutos']:,.2f} EUR brutos "
            f"-> {trabajo['rendimiento_neto_reducido']:,.2f} EUR neto reducido "
            f"(gastos deducibles: {trabajo['gastos_deducibles']:,.2f} EUR, "
            f"reduccion trabajo: {trabajo['reduccion_trabajo']:,.2f} EUR)"
        )

    # Activity income (autonomos)
    actividad = result.get("actividad")
    if actividad:
        est_label = {
            "directa_simplificada": "ED Simplificada",
            "directa_normal": "ED Normal",
            "objetiva": "Modulos",
        }.get(actividad.get("estimacion", ""), "")
        lines.append(
            f"Rendimiento actividad economica ({est_label}): "
            f"{actividad['ingresos_actividad']:,.2f} EUR ingresos "
            f"- {actividad['total_gastos_deducibles']:,.2f} EUR gastos"
        )
        if actividad.get("gastos_dificil_justificacion", 0) > 0:
            lines.append(
                f"  Gastos dificil justificacion (5%): "
                f"-{actividad['gastos_dificil_justificacion']:,.2f} EUR"
            )
        lines.append(
            f"  Rendimiento neto: {actividad['rendimiento_neto']:,.2f} EUR"
        )
        if actividad.get("reduccion_aplicada", 0) > 0:
            tipo_red = actividad.get("tipo_reduccion", "")
            red_label = ""
            if tipo_red == "inicio_actividad_art32_3":
                red_label = "inicio actividad Art. 32.3, 20%"
            elif tipo_red == "dependiente_art32_2":
                red_label = "autonomo dependiente Art. 32.2"
            lines.append(
                f"  Reduccion ({red_label}): "
                f"-{actividad['reduccion_aplicada']:,.2f} EUR"
            )
        lines.append(
            f"  Rendimiento neto reducido: "
            f"{actividad['rendimiento_neto_reducido']:,.2f} EUR"
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

    # Ceuta/Melilla deduction
    if result.get("deduccion_ceuta_melilla", 0) > 0:
        lines.append(
            f"Deducción Ceuta/Melilla (60% cuota íntegra, Art. 68.4 LIRPF): "
            f"-{result['deduccion_ceuta_melilla']:,.2f}€"
        )

    # Cuota líquida
    lines.append(
        f"Cuota líquida general: {result['cuota_liquida_general']:,.2f}€"
    )
    if result.get("cuota_ahorro", 0) > 0:
        lines.append(f"Cuota del ahorro: {result['cuota_ahorro']:,.2f}€")

    lines.append(
        f"CUOTA TOTAL: {result['cuota_total']:,.2f} EUR "
        f"(tipo medio efectivo: {result['tipo_medio']:.2f}%)"
    )

    # Retenciones y resultado final (si hay datos)
    total_ret = result.get("total_retenciones", 0)
    if total_ret > 0:
        lines.append("")
        lines.append("**Retenciones y pagos a cuenta**")
        if result.get("retenciones_actividad", 0) > 0:
            lines.append(f"- Retenciones actividad: {result['retenciones_actividad']:,.2f} EUR")
        if result.get("pagos_fraccionados_130", 0) > 0:
            lines.append(f"- Pagos fraccionados (Mod. 130): {result['pagos_fraccionados_130']:,.2f} EUR")
        if result.get("retenciones_alquiler", 0) > 0:
            lines.append(f"- Retenciones alquiler: {result.get('retenciones_alquiler', 0):,.2f} EUR")
        if result.get("retenciones_ahorro", 0) > 0:
            lines.append(f"- Retenciones ahorro: {result.get('retenciones_ahorro', 0):,.2f} EUR")
        lines.append(f"- Total retenciones: {total_ret:,.2f} EUR")

        cuota_dif = result.get("cuota_diferencial", 0)
        tipo_res = result.get("tipo_resultado", "")
        if cuota_dif > 0:
            lines.append(f"- **RESULTADO: A PAGAR {cuota_dif:,.2f} EUR**")
        elif cuota_dif < 0:
            lines.append(f"- **RESULTADO: A DEVOLVER {abs(cuota_dif):,.2f} EUR**")
        else:
            lines.append("- **RESULTADO: 0 EUR (sin ingreso ni devolucion)**")

    return "\n".join(lines)
