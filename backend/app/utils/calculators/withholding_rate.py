"""
Calculadora de Retenciones IRPF 2026.

Implementa el algoritmo oficial AEAT (26-12-2025 SGTT) para calcular
el tipo de retencion a cuenta del IRPF sobre rendimientos del trabajo.

Referencia: AEAT-Algoritmo_Retenciones_2026.pdf (47 paginas)
Normativa: Ley 35/2006 LIRPF + RD 439/2007 RIRPF (Arts. 80-89)
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import math


class SituacionFamiliar(str, Enum):
    """Art. 81 RIRPF — Situacion familiar del perceptor."""
    SITUACION1 = "1"  # Soltero/viudo/divorciado con hijos a cargo
    SITUACION2 = "2"  # Casado, conyuge con rentas < 1.500 EUR
    SITUACION3 = "3"  # Resto (soltero sin hijos, casado conyuge con rentas > 1.500)


class SituacionLaboral(str, Enum):
    ACTIVO = "activo"
    PENSIONISTA = "pensionista"
    DESEMPLEADO = "desempleado"


class TipoContrato(str, Enum):
    INDEFINIDO = "indefinido"
    TEMPORAL = "temporal"


class Discapacidad(str, Enum):
    SIN = "sin"
    DE33A65 = "33-65"
    DESDE65 = "65+"


@dataclass
class Descendiente:
    ano_nacimiento: int
    ano_adopcion: Optional[int] = None
    por_entero: bool = True  # computado por entero (no compartido)
    discapacidad: Discapacidad = Discapacidad.SIN
    movilidad_reducida: bool = False


@dataclass
class Ascendiente:
    ano_nacimiento: int
    convivencia: int = 1  # num personas con las que convive (1 = solo contigo)
    discapacidad: Discapacidad = Discapacidad.SIN
    movilidad_reducida: bool = False


@dataclass
class WithholdingInput:
    """Datos de entrada para el calculo de retenciones."""
    retribucion_bruta_anual: float
    situacion_familiar: SituacionFamiliar = SituacionFamiliar.SITUACION3
    situacion_laboral: SituacionLaboral = SituacionLaboral.ACTIVO
    tipo_contrato: TipoContrato = TipoContrato.INDEFINIDO
    ano_nacimiento: int = 1990
    discapacidad: Discapacidad = Discapacidad.SIN
    movilidad_reducida: bool = False

    # Familia
    descendientes: List[Descendiente] = field(default_factory=list)
    ascendientes: List[Ascendiente] = field(default_factory=list)

    # Datos economicos
    cotizaciones_ss: Optional[float] = None  # Si None, se estima al 6.35%
    reduccion_irregular_18_2: float = 0.0  # Rtos irregulares Art. 18.2
    reduccion_irregular_18_3: float = 0.0  # Rtos irregulares Art. 18.3

    # Deducciones adicionales
    pension_compensatoria: float = 0.0  # Al conyuge (fijada judicialmente)
    anualidades_alimentos: float = 0.0  # A hijos (fijadas judicialmente)
    hipoteca_pre2013: bool = False  # Deduccion vivienda pre-2013
    movilidad_geografica: bool = False
    prolongacion_actividad: bool = False  # >65 anos activo
    ceuta_melilla: bool = False

    num_pagas: int = 14  # 12 o 14 (para calcular mensual)


@dataclass
class WithholdingResult:
    """Resultado del calculo de retenciones."""
    tipo_retencion: float  # % de retencion (redondeado a 2 decimales)
    cuota_anual: float
    retencion_mensual: float
    salario_neto_mensual: float

    # Desglose
    retribucion_bruta: float
    cotizaciones_ss: float
    otros_gastos: float
    gastos_deducibles: float
    rendimiento_neto: float
    reduccion_trabajo: float
    rendimiento_neto_reducido: float
    minimo_personal_familiar: float
    base_retencion: float

    # Detalles MPYF
    minimo_contribuyente: float
    minimo_descendientes: float
    minimo_ascendientes: float
    minimo_discapacidad: float

    # Flags
    exento: bool
    motivo_exencion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tipo_retencion": self.tipo_retencion,
            "cuota_anual": round(self.cuota_anual, 2),
            "retencion_mensual": round(self.retencion_mensual, 2),
            "salario_neto_mensual": round(self.salario_neto_mensual, 2),
            "retribucion_bruta": round(self.retribucion_bruta, 2),
            "cotizaciones_ss": round(self.cotizaciones_ss, 2),
            "gastos_deducibles": round(self.gastos_deducibles, 2),
            "rendimiento_neto_reducido": round(self.rendimiento_neto_reducido, 2),
            "minimo_personal_familiar": round(self.minimo_personal_familiar, 2),
            "base_retencion": round(self.base_retencion, 2),
            "exento": self.exento,
            "motivo_exencion": self.motivo_exencion,
        }


# ===================================================================
# TABLA 2 — Escala de retencion (Art. 101.1 LIRPF, vigente 2026)
# ===================================================================
ESCALA_RETENCION = [
    (12450.00, 0.19),
    (20200.00, 0.24),
    (35200.00, 0.30),
    (60000.00, 0.37),
    (300000.00, 0.45),
    (float("inf"), 0.47),
]

# TABLA 1 — Limites excluyentes de retencion (Art. 81 RIRPF, RD 142/2024)
LIMITES_EXENCION = {
    # situacion_familiar: {num_descendientes: limite}
    SituacionFamiliar.SITUACION1: {0: 0, 1: 17644, 2: 18694},
    SituacionFamiliar.SITUACION2: {0: 17197, 1: 18130, 2: 19262},
    SituacionFamiliar.SITUACION3: {0: 15876, 1: 16342, 2: 16867},
}


def _redondear(valor: float) -> float:
    """Redondeo a 2 decimales (0.005 → 0.01)."""
    return round(valor, 2)


def _aplicar_escala(base: float) -> float:
    """Aplica la escala de retencion (TABLA 2) a una base."""
    if base <= 0:
        return 0.0

    cuota = 0.0
    base_restante = base
    anterior = 0.0

    for limite, porcentaje in ESCALA_RETENCION:
        tramo = min(base_restante, limite - anterior)
        if tramo <= 0:
            break
        cuota += tramo * porcentaje
        base_restante -= tramo
        anterior = limite

    return _redondear(cuota)


def calcular_retencion(inp: WithholdingInput) -> WithholdingResult:
    """
    Calcula el tipo de retencion IRPF segun algoritmo oficial AEAT 2026.

    Args:
        inp: Datos del perceptor

    Returns:
        WithholdingResult con tipo_retencion y desglose
    """
    RETRIB = inp.retribucion_bruta_anual
    ANO_ACTUAL = 2026

    # ================================================================
    # 1. COTIZACIONES A LA SEGURIDAD SOCIAL
    # ================================================================
    if inp.cotizaciones_ss is not None:
        COTIZACIONES = inp.cotizaciones_ss
    else:
        # Estimar SS al 6.35% (contingencias comunes 4.70% + desempleo 1.55% + FP 0.10%)
        COTIZACIONES = _redondear(RETRIB * 0.0635)

    # ================================================================
    # 2. OTROS GASTOS DEDUCIBLES (pag 22 algoritmo)
    # ================================================================
    GASTOSGEN = 2000.00

    # Movilidad geografica
    INCREGASMOVIL = 2000.00 if inp.movilidad_geografica else 0.0

    # Discapacidad trabajador activo
    INCREGASDISTRA = 0.0
    if inp.situacion_laboral == SituacionLaboral.ACTIVO:
        if inp.discapacidad == Discapacidad.DESDE65 or (
            inp.discapacidad == Discapacidad.DE33A65 and inp.movilidad_reducida
        ):
            INCREGASDISTRA = 7750.00
        elif inp.discapacidad == Discapacidad.DE33A65:
            INCREGASDISTRA = 3500.00

    OTROSGASTOS = GASTOSGEN + INCREGASMOVIL + INCREGASDISTRA

    # Limitar otros gastos
    if RETRIB - COTIZACIONES < 0:
        OTROSGASTOS = 0
    elif OTROSGASTOS > RETRIB - COTIZACIONES:
        OTROSGASTOS = RETRIB - COTIZACIONES

    GASTOS = COTIZACIONES + OTROSGASTOS

    # ================================================================
    # 3. RENDIMIENTO NETO DEL TRABAJO (pag 22)
    # ================================================================
    RNT = RETRIB - inp.reduccion_irregular_18_2 - inp.reduccion_irregular_18_3 - COTIZACIONES
    if RNT < 0:
        RNT = 0

    # ================================================================
    # 4. REDUCCION POR OBTENCION DE RENDIMIENTOS DEL TRABAJO (pag 23)
    #    Art. 20 LIRPF + RD-Ley 4/2024
    # ================================================================
    if RNT <= 14852.00:
        RED20 = 7302.00
    elif RNT <= 17673.52:
        RED20 = 7302.00 - 1.75 * (RNT - 14852.00)
    elif RNT < 19747.50:
        RED20 = 2364.34 - 1.14 * (RNT - 17673.52)
    else:
        RED20 = 0.0
    RED20 = _redondear(RED20)

    # ================================================================
    # 5. RENDIMIENTO NETO REDUCIDO (pag 23)
    # ================================================================
    RNTREDU = RNT - OTROSGASTOS - RED20
    if RNTREDU < 0:
        RNTREDU = 0

    # Reducciones adicionales
    PENSION_RED = 600.00 if inp.situacion_laboral == SituacionLaboral.PENSIONISTA else 0.0
    HIJOS_RED = 600.00 if len(inp.descendientes) > 2 else 0.0
    DESEM_RED = 1200.00 if inp.situacion_laboral == SituacionLaboral.DESEMPLEADO else 0.0

    # ================================================================
    # 6. MINIMO PERSONAL Y FAMILIAR (pag 24-28)
    # ================================================================

    # A. Minimo contribuyente
    edad = ANO_ACTUAL - inp.ano_nacimiento
    MINPER = 5550.00
    PER65 = 1150.00 if edad > 64 else 0.0
    PER75 = 1400.00 if edad > 74 else 0.0
    MINCON = MINPER + PER65 + PER75

    # B. Minimo por descendientes
    MINDES = 0.0
    MINDES3 = 0.0
    MINDISDESC = 0.0
    num_des = len(inp.descendientes)

    for i, desc in enumerate(inp.descendientes):
        entero = 1.0 if desc.por_entero else 0.5
        # Minimo general por orden
        if i == 0:
            MINDES += 2400.00 * entero
        elif i == 1:
            MINDES += 2700.00 * entero
        elif i == 2:
            MINDES += 4000.00 * entero
        else:
            MINDES += 4500.00 * entero

        # Menores de 3 anos
        if desc.ano_nacimiento > ANO_ACTUAL - 3:
            MINDES3 += 2800.00 * entero
        elif desc.ano_adopcion and desc.ano_adopcion > ANO_ACTUAL - 3:
            MINDES3 += 2800.00 * entero

        # Discapacidad descendientes
        if desc.discapacidad == Discapacidad.DE33A65:
            MINDISDESC += 3000.00 * entero
        elif desc.discapacidad == Discapacidad.DESDE65:
            MINDISDESC += 9000.00 * entero
        if desc.movilidad_reducida and desc.discapacidad != Discapacidad.SIN:
            MINDISDESC += 3000.00 * entero

    MINDES = _redondear(MINDES + MINDES3)

    # C. Minimo por ascendientes
    MINAS = 0.0
    MINDISASC = 0.0
    for asc in inp.ascendientes:
        edad_asc = ANO_ACTUAL - asc.ano_nacimiento
        factor = 1.0 / asc.convivencia

        if edad_asc > 64:
            MINAS += 1150.00 * factor
        if edad_asc > 74:
            MINAS += 1400.00 * factor

        # Discapacidad ascendientes
        if asc.discapacidad == Discapacidad.DE33A65:
            MINDISASC += 3000.00 * factor
        elif asc.discapacidad == Discapacidad.DESDE65:
            MINDISASC += 9000.00 * factor
        if asc.movilidad_reducida and asc.discapacidad != Discapacidad.SIN:
            MINDISASC += 3000.00 * factor

    MINAS = _redondear(MINAS)

    # D. Discapacidad del contribuyente
    MINDISCON = 0.0
    if inp.discapacidad == Discapacidad.DE33A65:
        MINDISCON = 3000.00
    elif inp.discapacidad == Discapacidad.DESDE65:
        MINDISCON = 9000.00
    if inp.movilidad_reducida and inp.discapacidad != Discapacidad.SIN:
        MINDISCON += 3000.00

    MINDIS = MINDISCON + MINDISDESC + MINDISASC
    MINPERFAM = MINCON + MINDES + MINAS + MINDIS

    # ================================================================
    # 7. BASE PARA CALCULAR EL TIPO DE RETENCION (pag 29)
    # ================================================================
    REDU = PENSION_RED + HIJOS_RED + DESEM_RED + inp.pension_compensatoria
    BASE = max(0.0, RNTREDU - REDU)

    # ================================================================
    # 8. COMPROBAR EXENCION (pag 29-30, TABLA 1)
    # ================================================================
    num_des_exencion = min(len(inp.descendientes), 2)
    limite_exencion = LIMITES_EXENCION[inp.situacion_familiar].get(
        num_des_exencion, LIMITES_EXENCION[inp.situacion_familiar][2]
    )
    # Situacion 1 sin hijos: no hay limite (siempre sujeto)
    if inp.situacion_familiar == SituacionFamiliar.SITUACION1 and len(inp.descendientes) == 0:
        limite_exencion = 0

    tope_exencion = limite_exencion + PENSION_RED + DESEM_RED
    exento = RETRIB <= tope_exencion and limite_exencion > 0

    if exento:
        return WithholdingResult(
            tipo_retencion=0.0,
            cuota_anual=0.0,
            retencion_mensual=0.0,
            salario_neto_mensual=_redondear((RETRIB - COTIZACIONES) / inp.num_pagas),
            retribucion_bruta=RETRIB,
            cotizaciones_ss=COTIZACIONES,
            otros_gastos=OTROSGASTOS,
            gastos_deducibles=GASTOS,
            rendimiento_neto=RNT,
            reduccion_trabajo=RED20,
            rendimiento_neto_reducido=RNTREDU,
            minimo_personal_familiar=MINPERFAM,
            base_retencion=BASE,
            minimo_contribuyente=MINCON,
            minimo_descendientes=MINDES,
            minimo_ascendientes=MINAS,
            minimo_discapacidad=MINDIS,
            exento=True,
            motivo_exencion=f"Retribucion ({RETRIB:.0f} EUR) inferior al limite de exencion ({tope_exencion:.0f} EUR) para su situacion familiar",
        )

    # ================================================================
    # 9. CUOTA DE RETENCION (pag 30-34)
    # ================================================================

    # Cuota 1: Escala sobre BASE
    if inp.anualidades_alimentos > 0 and BASE > inp.anualidades_alimentos:
        BASE1 = BASE - inp.anualidades_alimentos
        BASE2 = inp.anualidades_alimentos
        CUOTA1 = _aplicar_escala(BASE1) + _aplicar_escala(BASE2)
    else:
        CUOTA1 = _aplicar_escala(BASE)

    # Cuota 2: Escala sobre MINPERFAM
    CUOTA2 = _aplicar_escala(MINPERFAM)

    # Cuota de retencion
    CUOTA = max(0.0, CUOTA1 - CUOTA2)

    # Deduccion Ceuta/Melilla (60% de la cuota)
    if inp.ceuta_melilla:
        CUOTA = _redondear(CUOTA * 0.40)  # Paga solo 40% (60% deduccion)

    # ================================================================
    # 10. TIPO DE RETENCION (pag 34-35)
    # ================================================================
    if RETRIB > 0:
        TIPO_PREVIO = _redondear((CUOTA / RETRIB) * 100)
    else:
        TIPO_PREVIO = 0.0

    # Redondear al entero o medio punto mas proximo
    # Segun algoritmo: redondear a 2 decimales
    TIPO = TIPO_PREVIO

    # Minimo por tipo de contrato
    if inp.tipo_contrato == TipoContrato.TEMPORAL:
        TIPO = max(TIPO, 2.0)  # Minimo 2% para temporales
    # Para indefinidos no hay minimo adicional (el tipo calculado aplica)

    # Minoracion por hipoteca pre-2013
    if inp.hipoteca_pre2013 and RETRIB < 33007.20:
        MINOPAGO = min(CUOTA, 660.14)
        CUOTA = max(0.0, CUOTA - MINOPAGO)
        if RETRIB > 0:
            TIPO = _redondear((CUOTA / RETRIB) * 100)

    TIPO = max(0.0, TIPO)

    # ================================================================
    # 11. CALCULAR IMPORTES MENSUALES
    # ================================================================
    CUOTA_ANUAL = _redondear(RETRIB * TIPO / 100)
    RETENCION_MENSUAL = _redondear(CUOTA_ANUAL / inp.num_pagas)
    NETO_MENSUAL = _redondear((RETRIB - COTIZACIONES - CUOTA_ANUAL) / inp.num_pagas)

    return WithholdingResult(
        tipo_retencion=TIPO,
        cuota_anual=CUOTA_ANUAL,
        retencion_mensual=RETENCION_MENSUAL,
        salario_neto_mensual=NETO_MENSUAL,
        retribucion_bruta=RETRIB,
        cotizaciones_ss=COTIZACIONES,
        otros_gastos=OTROSGASTOS,
        gastos_deducibles=GASTOS,
        rendimiento_neto=RNT,
        reduccion_trabajo=RED20,
        rendimiento_neto_reducido=RNTREDU,
        minimo_personal_familiar=MINPERFAM,
        base_retencion=BASE,
        minimo_contribuyente=MINCON,
        minimo_descendientes=MINDES,
        minimo_ascendientes=MINAS,
        minimo_discapacidad=MINDIS,
        exento=False,
    )
