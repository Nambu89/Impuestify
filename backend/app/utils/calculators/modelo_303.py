"""
IVA / Modelo 303 Calculator — Declaracion trimestral del IVA (Regimen General).

Official form: Modelo 303 (AEAT, aprobado por Orden HAP/2215/2013 y sucesivas).
Casillas reference: version vigente ejercicio 2025.

Scope:
- Territorio comun (AEAT)
- Pais Vasco (Modelo 300, same arithmetic, different submission context)
- Navarra (uses this same structure)
- Canarias: NOT covered here (uses IGIC / Modelo 420)
- Ceuta / Melilla: NOT covered here (uses IPSI, deferred implementation)

Only Regimen General is implemented.  Regimen Simplificado (modulos) is
out of scope and would require a separate calculator.

IVA rates are statutory (LIVA art. 90-91) and do NOT come from the database,
so TaxParameterRepository is accepted in __init__ for interface consistency
but is not used in calculations.

P1/P2 extensions (audit 2026-05, sesion 40):
- RECC (Regimen Especial Criterio de Caja, Art. 163 decies-sexies LIVA):
  bandera + umbral elegibilidad <2.000.000 EUR + advertencia.
- SII (Suministro Inmediato Informacion, Art. 62.6 RIVA): bandera + umbral
  obligatorio >6.010.121,04 EUR + plazos especiales.
- ISP (Inversion Sujeto Pasivo, Art. 84.uno.2 LIVA): ya soportado en
  casillas 12-13 (mantiene compat); ampliado con desglose por supuesto.
- Modificaciones bases (Art. 80 + 89 LIVA): casillas 14-15 + 16-17.
- Tipos transitorios 0%/5% (RDL 4/2022, RDL 19/2022, RDL 9/2024):
  expirados desde 1-oct-2025 segun normativa vigente — bandera vigente
  con default False; warning si se intenta usar fuera de rango temporal.
- RE (Recargo Equivalencia, Art. 154-163 LIVA): detector ampliado +
  flag `bloqueo_re` que indica que el sujeto NO presenta 303.
"""
from typing import Any, Dict, List, Optional

from app.utils.tax_parameter_repository import TaxParameterRepository

# Statutory IVA rates (LIVA art. 90-91, unchanged since 2012 for general/reduced/superreduced)
_TIPO_GENERAL: float = 21.0
_TIPO_REDUCIDO: float = 10.0
_TIPO_SUPERREDUCIDO: float = 4.0

# Tipos transitorios alimentacion / aceites (RDL 20/2022 + RDL 4/2024 + RDL 9/2024)
_TIPO_TRANSITORIO_0: float = 0.0
_TIPO_TRANSITORIO_5: float = 5.0
_TIPO_TRANSITORIO_2: float = 2.0   # 2025 productos basicos hasta 30 sept 2025
_TIPO_TRANSITORIO_75: float = 7.5  # 2024 aceites/pasta tras subida 1 oct 2024

# Umbrales regimenes especiales
_UMBRAL_RECC: float = 2_000_000.0          # Art. 163 decies LIVA
_UMBRAL_SII_OBLIGATORIO: float = 6_010_121.04  # Art. 62.6 RIVA

# CNAE / IAE patterns para detector RE ampliado
# Art. 149 LIVA: comerciantes minoristas persona fisica que cumplen requisitos
# CNAE 47.x = comercio al por menor (excluyendo 47.3 vehiculos motor)
# IAE 64x-65x = comercio menor (epigrafes 1992)
_RE_CNAE_PREFIXES = ("47.1", "47.2", "47.4", "47.5", "47.6", "47.7", "47.8", "47.9")
_RE_IAE_PREFIXES = ("641", "642", "643", "644", "645", "646", "647", "651", "652", "653", "654", "656", "657", "659")

# Tipos RE actuales (Art. 161 LIVA)
RE_RATES_FULL: Dict[float, float] = {
    21.0: 5.2,    # general
    10.0: 1.4,    # reducido
    5.0: 0.62,    # transitorio aceites/pasta (proporcional)
    4.0: 0.5,     # superreducido
    2.0: 0.26,    # transitorio basicos 2025 (proporcional)
    1.75: 1.75,   # tabaco/labores (categoria propia)
    0.0: 0.0,     # transitorio basicos 0%
}

# Supuestos ISP comunes (Art. 84.uno.2 LIVA) — informativo
ISP_SUPUESTOS = {
    "construccion": "Art. 84.uno.2.f — ejecuciones obra construccion/rehabilitacion",
    "moviles": "Art. 84.uno.2.g — telefonos moviles, consolas, ordenadores portatiles, tablets",
    "inmuebles": "Art. 84.uno.2.e — entregas de inmuebles (renuncia a exencion)",
    "residuos": "Art. 84.uno.2.c — entregas de desechos/residuos",
    "oro_inversion": "Art. 84.uno.2.b — oro de inversion",
    "gas_electricidad": "Art. 84.uno.2.h — gas natural/electricidad B2B",
    "servicios_intracom": "Art. 84.uno.2.a — servicios prestados por no establecidos",
}


class Modelo303Calculator:
    """
    Calculates the quarterly IVA self-assessment (Modelo 303, Regimen General).

    Each instance is stateless beyond the (unused) repository reference;
    all state lives in the ``calculate`` call.
    """

    # Recargo de Equivalencia rates (Art. 154-163 LIVA)
    # Applies to retail traders who are personas fisicas (e.g. pharmacies, CNAE 47.73)
    RE_RATES = {
        21: 5.2,   # IVA general 21% -> RE 5.2%
        10: 1.4,   # IVA reducido 10% -> RE 1.4%
        4: 0.5,    # IVA superreducido 4% -> RE 0.5%
    }

    def __init__(self, repo: TaxParameterRepository) -> None:
        # Kept for interface consistency with the rest of the calculator package.
        self._repo = repo

    @staticmethod
    def is_recargo_equivalencia(
        situacion_laboral: str = "",
        cnae: str = "",
        iae: str = "",
        es_persona_fisica: bool = True,
        es_minorista: bool = False,
    ) -> bool:
        """Check if the taxpayer is subject to Recargo de Equivalencia.

        Detector AMPLIADO (audit 2026-05 BUG-303-05):
        Applies to retail traders (comerciantes minoristas) que cumplen TODOS:
        1. Persona fisica (no SL/SA/SC).
        2. Comerciante minorista (>80% ventas a consumidor final, Art. 149 LIVA).
        3. CNAE 47.x (comercio menor) excepto vehiculos motor (47.3).
        4. O IAE 641-659 (epigrafes minoristas 1992).

        Casos canonicos cubiertos:
        - Farmacia (CNAE 47.73, IAE 652.1).
        - Pequeno comercio textil, alimentacion, hogar, etc.

        When RE applies:
        - The taxpayer does NOT file Modelo 303 (IVA quarterly).
        - The taxpayer does NOT file Modelo 390 (IVA annual summary).
        - IVA + RE is charged and remitted by the supplier.
        - The taxpayer cannot deduct input IVA (IVA soportado).
        - Invoices to customers are issued without IVA (simplified tickets).
        - Si hay intracom/ISP -> presenta Modelo 308 (devolucion) o 309 (no
          periodicas).
        """
        # Caso explicito: farmaceutico
        if situacion_laboral == "farmaceutico":
            return True

        # Persona juridica nunca esta en RE
        if not es_persona_fisica:
            return False

        # CNAE minorista (47.x salvo vehiculos)
        if cnae:
            cnae_norm = cnae.strip()
            if cnae_norm.startswith(_RE_CNAE_PREFIXES):
                return True
            # 47.3 vehiculos motor: excluido del RE
            if cnae_norm.startswith("47.3"):
                return False

        # IAE epigrafes minoristas
        if iae:
            iae_norm = iae.strip().split(".")[0]  # "652.1" -> "652"
            if iae_norm.startswith(_RE_IAE_PREFIXES):
                return True

        # Bandera explicita del usuario
        return bool(es_minorista and es_persona_fisica)

    @staticmethod
    def es_elegible_recc(volumen_ano_anterior: float) -> bool:
        """Check if a taxpayer is eligible for Regimen Especial Criterio de Caja.

        Art. 163 decies LIVA: solo elegibles sujetos con volumen de operaciones
        del ano natural anterior <= 2.000.000 EUR. Si en el ano corriente las
        cobros en efectivo de un mismo destinatario superan 100.000 EUR, queda
        excluido al ano siguiente.

        Para no elegibles: el calculo 303 sigue siendo correcto en regimen
        general (devengo a la entrega, deduccion al recibir factura).
        """
        return 0 <= volumen_ano_anterior <= _UMBRAL_RECC

    @staticmethod
    def requiere_sii(volumen_ano_anterior: float, redeme: bool = False, grupo_iva: bool = False) -> bool:
        """Check SII obligation (Art. 62.6 RIVA + Art. 30 RD 1065/2007).

        Obligatorio si:
        - Volumen operaciones ano anterior > 6.010.121,04 EUR (gran empresa).
        - Inscrito en REDEME (Registro Devolucion Mensual).
        - Grupo IVA Art. 163 quinquies LIVA.

        Si SII -> presentacion 303 MENSUAL (no trimestral) en los 30 primeros
        dias naturales del mes siguiente (20 dias en agosto -> trasladable).
        """
        return volumen_ano_anterior > _UMBRAL_SII_OBLIGATORIO or redeme or grupo_iva

    @staticmethod
    def _validar_tipos_transitorios(year: int, mes: int = 1) -> Dict[str, bool]:
        """Validate whether transitional 0%/5%/2%/7.5% rates are still in force.

        Cronologia (RDL 20/2022 + RDL 5/2023 + RDL 4/2024 + RDL 9/2024):
        - 1 ene 2023 a 30 jun 2024: pan/leche/huevos/frutas/verduras 0%; aceites/pasta 5%.
        - 1 jul 2024 a 30 sept 2024: aceites 5% -> 7.5% (subida progresiva).
        - 1 oct 2024 a 31 dic 2024: aceite oliva 7.5%; resto basicos 0%.
        - 1 ene 2025 a 30 sept 2025: basicos 2%; aceites 7.5% (transitorios).
        - 1 oct 2025 en adelante: vuelta a tipos normales 4%/10%.

        Returns dict con flags per tipo transitorio.
        """
        # Cierre normativo: desde 1 oct 2025, vuelve a tipos normales
        if year > 2025:
            return {"tipo_0_vigente": False, "tipo_5_vigente": False,
                    "tipo_2_vigente": False, "tipo_75_vigente": False}
        if year == 2025 and mes >= 10:
            return {"tipo_0_vigente": False, "tipo_5_vigente": False,
                    "tipo_2_vigente": False, "tipo_75_vigente": False}
        if year == 2025:
            # Ene-sept 2025: basicos 2% + aceites 7.5%
            return {"tipo_0_vigente": False, "tipo_5_vigente": False,
                    "tipo_2_vigente": True, "tipo_75_vigente": True}
        if year == 2024:
            # 2024 mixto: 0% basicos casi todo el ano, 5%/7.5% aceites
            return {"tipo_0_vigente": True, "tipo_5_vigente": mes <= 6,
                    "tipo_2_vigente": False, "tipo_75_vigente": mes >= 7}
        if year == 2023:
            return {"tipo_0_vigente": True, "tipo_5_vigente": True,
                    "tipo_2_vigente": False, "tipo_75_vigente": False}
        # Antes de 2023: no aplican
        return {"tipo_0_vigente": False, "tipo_5_vigente": False,
                "tipo_2_vigente": False, "tipo_75_vigente": False}

    def _calc_transitorios(
        self,
        bases_transitorias: Optional[Dict[str, float]],
        year: int,
        mes: int = 1,
    ) -> Dict[str, float]:
        """Calculate cuotas at transitional rates 0%/2%/5%/7.5%.

        Input ``bases_transitorias`` keys (todas opcionales):
        - "base_0": productos basicos al 0% (RDL 20/2022).
        - "base_5": aceites/pasta al 5% (RDL 4/2022).
        - "base_2": basicos al 2% (RDL 9/2024).
        - "base_75": aceites al 7.5% (RDL 4/2024).

        Si los tipos no estan vigentes en (year, mes), devuelve cuotas pero
        anota warning en la salida (a recoger por el caller).
        """
        bases = bases_transitorias or {}
        vigencia = self._validar_tipos_transitorios(year, mes)
        warnings: List[str] = []

        base_0 = float(bases.get("base_0", 0.0) or 0.0)
        base_5 = float(bases.get("base_5", 0.0) or 0.0)
        base_2 = float(bases.get("base_2", 0.0) or 0.0)
        base_75 = float(bases.get("base_75", 0.0) or 0.0)

        if base_0 > 0 and not vigencia["tipo_0_vigente"]:
            warnings.append("tipo 0% no vigente en periodo declarado")
        if base_5 > 0 and not vigencia["tipo_5_vigente"]:
            warnings.append("tipo 5% no vigente en periodo declarado")
        if base_2 > 0 and not vigencia["tipo_2_vigente"]:
            warnings.append("tipo 2% no vigente en periodo declarado")
        if base_75 > 0 and not vigencia["tipo_75_vigente"]:
            warnings.append("tipo 7.5% no vigente en periodo declarado")

        cuota_0 = round(base_0 * _TIPO_TRANSITORIO_0 / 100, 2)
        cuota_5 = round(base_5 * _TIPO_TRANSITORIO_5 / 100, 2)
        cuota_2 = round(base_2 * _TIPO_TRANSITORIO_2 / 100, 2)
        cuota_75 = round(base_75 * _TIPO_TRANSITORIO_75 / 100, 2)
        total = round(cuota_0 + cuota_5 + cuota_2 + cuota_75, 2)

        return {
            "base_0": round(base_0, 2),
            "cuota_0": cuota_0,
            "base_5": round(base_5, 2),
            "cuota_5": cuota_5,
            "base_2": round(base_2, 2),
            "cuota_2": cuota_2,
            "base_75": round(base_75, 2),
            "cuota_75": cuota_75,
            "cuota_total_transitorios": total,
            "warnings": warnings,
            "vigencia": vigencia,
        }

    def _calc_isp(
        self,
        bases_isp: Optional[Dict[str, float]],
    ) -> Dict[str, Any]:
        """Calculate ISP (Inversion Sujeto Pasivo) por supuesto Art. 84.uno.2 LIVA.

        Input ``bases_isp`` keys (todas opcionales):
        - "construccion": {"base": float, "tipo": float}
        - "moviles": {"base": float, "tipo": float}
        - "inmuebles": {"base": float, "tipo": float}
        - "residuos": ...
        - "oro_inversion": ...
        - "gas_electricidad": ...
        - "servicios_intracom": ...

        ISP genera cuota DEVENGADA (autoliquidacion) Y simultaneamente
        DEDUCIBLE (si la actividad es deducible). El neto suele ser cero,
        pero la presentacion es obligatoria. La cuota deducible se anade
        a casilla 29 (corrientes) del lado deducible — el caller decide.
        """
        bases = bases_isp or {}
        desglose: Dict[str, Dict[str, float]] = {}
        total_base = 0.0
        total_cuota = 0.0

        for supuesto, descripcion in ISP_SUPUESTOS.items():
            entry = bases.get(supuesto)
            if not entry:
                continue
            base = float(entry.get("base", 0.0) or 0.0)
            tipo = float(entry.get("tipo", 21.0) or 21.0)
            cuota = round(base * tipo / 100, 2)
            total_base += base
            total_cuota += cuota
            desglose[supuesto] = {
                "base": round(base, 2),
                "tipo": tipo,
                "cuota": cuota,
                "descripcion": descripcion,
            }

        return {
            "desglose_supuestos": desglose,
            "total_base_isp": round(total_base, 2),
            "total_cuota_isp": round(total_cuota, 2),
        }

    def _calc_mod_bases(
        self,
        mods_bases: Optional[Dict[str, float]],
    ) -> Dict[str, Any]:
        """Calculate modificaciones de bases y cuotas anteriores (Art. 80 + 89 LIVA).

        Input ``mods_bases`` keys (signed: +/-):
        - "envases": devolucion de envases.
        - "oferta_anulada": operaciones acogidas a oferta vinculante anuladas.
        - "concurso": creditos incobrables por concurso de acreedores.
        - "incobrables": creditos incobrables Art. 80.cuatro LIVA.
        - "rappels_descuentos": descuentos posventa.

        Cada concepto puede llevar tipo IVA aplicable (default 21).
        Devuelve totales para casillas 14 (bases) + 16 (cuotas) o
        casillas 15+17 segun convenio del modelo vigente.
        """
        mods = mods_bases or {}
        total_base_mod = 0.0
        total_cuota_mod = 0.0
        desglose: Dict[str, Dict[str, float]] = {}

        for concepto in ("envases", "oferta_anulada", "concurso", "incobrables", "rappels_descuentos"):
            entry = mods.get(concepto)
            if not entry:
                continue
            base = float(entry.get("base", 0.0) or 0.0)
            tipo = float(entry.get("tipo", 21.0) or 21.0)
            cuota = round(base * tipo / 100, 2)
            total_base_mod += base
            total_cuota_mod += cuota
            desglose[concepto] = {
                "base": round(base, 2),
                "tipo": tipo,
                "cuota": cuota,
            }

        return {
            "desglose_modificaciones": desglose,
            "total_base_modificaciones": round(total_base_mod, 2),
            "total_cuota_modificaciones": round(total_cuota_mod, 2),
        }

    def _calc_recc(
        self,
        regimen_recc: bool,
        volumen_ano_anterior: float,
        cobros_pendientes_anteriores: float = 0.0,
        pagos_pendientes_anteriores: float = 0.0,
        year: int = 2025,
    ) -> Dict[str, Any]:
        """Calculate RECC adjustments (Art. 163 decies-sexies LIVA).

        Sin re-calcular el modelo entero: ajusta el devengado (operaciones cuyo
        cobro se materializa en el periodo) y el deducible (compras cuyo pago
        se materializa en el periodo).

        Limite temporal Art. 163 terdecies: si al 31 dic del ano siguiente al
        devengo no se ha cobrado/pagado, devengo/deduccion forzados.

        Returns dict con flags + ajustes informativos. NO modifica casillas
        directamente — caller usa estos valores como inputs adicionales.
        """
        if not regimen_recc:
            return {
                "regimen_aplicado": False,
                "elegible": True,
                "warning": None,
                "limite_temporal_year": None,
            }

        elegible = self.es_elegible_recc(volumen_ano_anterior)
        warning = None
        if not elegible:
            warning = (
                f"Volumen operaciones {volumen_ano_anterior:,.2f} EUR > "
                f"umbral RECC {_UMBRAL_RECC:,.2f} EUR (Art. 163 decies LIVA). "
                f"Sujeto NO elegible — calculo en regimen general."
            )

        return {
            "regimen_aplicado": elegible,
            "elegible": elegible,
            "warning": warning,
            "limite_temporal_year": year + 1,  # devengo forzado al 31-dic ano siguiente
            "cobros_pendientes_anteriores": round(cobros_pendientes_anteriores, 2),
            "pagos_pendientes_anteriores": round(pagos_pendientes_anteriores, 2),
            "umbral_volumen": _UMBRAL_RECC,
            "volumen_declarado": volumen_ano_anterior,
        }

    async def calculate(
        self,
        *,
        # --- IVA DEVENGADO (output tax) ---
        base_4: float = 0.0,
        base_10: float = 0.0,
        base_21: float = 0.0,
        # Adquisiciones intracomunitarias de bienes / servicios (casillas 10-12)
        base_intracomunitarias: float = 0.0,
        tipo_intracomunitarias: float = 0.0,   # variable %, e.g. 21.0
        # Inversion del sujeto pasivo — ISP (casillas 13-14)
        base_inversion_sp: float = 0.0,
        tipo_inversion_sp: float = 21.0,       # normally 21% unless service is reduced
        # Modificacion de bases y cuotas de periodos anteriores (casillas 15-16)
        mod_bases: float = 0.0,
        mod_cuotas: float = 0.0,               # signed: negative = rectification in favour
        # --- IVA DEDUCIBLE (input tax) ---
        # Corrientes interiores (casillas 28-29): base informativa + deductible quota
        base_corrientes_interiores: float = 0.0,
        cuota_corrientes_interiores: float = 0.0,
        # Bienes de inversion interiores (casillas 30-31)
        base_inversion_interiores: float = 0.0,
        cuota_inversion_interiores: float = 0.0,
        # Importaciones corrientes (casillas 32-33)
        base_importaciones_corrientes: float = 0.0,
        cuota_importaciones_corrientes: float = 0.0,
        # Importaciones de bienes de inversion (casillas 34-35)
        base_importaciones_inversion: float = 0.0,
        cuota_importaciones_inversion: float = 0.0,
        # Adquisiciones intracomunitarias corrientes (casillas 36-37)
        base_intracom_corrientes: float = 0.0,
        cuota_intracom_corrientes: float = 0.0,
        # Adquisiciones intracomunitarias de inversion (casillas 38-39)
        base_intracom_inversion: float = 0.0,
        cuota_intracom_inversion: float = 0.0,
        # Rectificacion de deducciones (casillas 40-41), signed
        base_rectificacion_deducciones: float = 0.0,
        rectificacion_deducciones: float = 0.0,
        # Compensaciones regimen especial agricultura, ganaderia y pesca (casilla 42)
        compensacion_agricultura: float = 0.0,
        # Regularizacion bienes de inversion por regla de prorrata (casilla 43), signed
        regularizacion_inversion: float = 0.0,
        # Regularizacion por aplicacion del porcentaje definitivo de prorrata (casilla 44), signed
        regularizacion_prorrata: float = 0.0,
        # --- RESULTADO ---
        # Porcentaje de atribucion al Estado (casilla 65)
        # 100% for territorio comun; <100% for companies operating in multiple territories
        pct_atribucion_estado: float = 100.0,
        # IVA a la importacion liquidado por la Aduana pendiente de ingreso (casilla 77)
        iva_aduana_pendiente: float = 0.0,
        # Cuotas a compensar de periodos anteriores (casilla 78), >= 0
        cuotas_compensar_anteriores: float = 0.0,
        # Regularizacion anual (casilla 68): ONLY filled in 4T; signed
        regularizacion_anual: float = 0.0,
        # Para declaracion complementaria: resultado de la declaracion anterior (casilla 70)
        resultado_anterior_complementaria: float = 0.0,
        # --- P1/P2 EXTENSIONS (audit 2026-05) ---
        # RECC — Regimen Especial Criterio de Caja (Art. 163 decies LIVA)
        regimen_recc: bool = False,
        volumen_ano_anterior: float = 0.0,
        cobros_pendientes_recc: float = 0.0,    # cobros materializados de devengo anterior
        pagos_pendientes_recc: float = 0.0,     # pagos materializados de deducciones anteriores
        # SII — Suministro Inmediato Informacion (Art. 62.6 RIVA)
        en_sii: bool = False,
        redeme: bool = False,
        grupo_iva: bool = False,
        # ISP por supuesto Art. 84.uno.2 LIVA (genera devengado y deducible simultaneo)
        bases_isp: Optional[Dict[str, Dict[str, float]]] = None,
        isp_es_deducible: bool = True,
        # Modificaciones bases imponibles (Art. 80 + 89 LIVA)
        mods_bases: Optional[Dict[str, Dict[str, float]]] = None,
        # Tipos transitorios alimentacion / aceites (RDL 4/2022 + RDL 9/2024)
        bases_transitorias: Optional[Dict[str, float]] = None,
        mes_inicio_periodo: int = 1,   # para validar vigencia tipos transitorios
        # RE — Recargo Equivalencia detector (devuelve bloqueo si aplica)
        re_situacion_laboral: str = "",
        re_cnae: str = "",
        re_iae: str = "",
        re_es_persona_fisica: bool = True,
        re_es_minorista: bool = False,
        re_strict_block: bool = False,  # si True y RE detectado, devuelve solo el bloqueo
        # Metadata
        quarter: int = 1,         # 1-4
        year: int = 2025,
        territory: str = "comun",  # 'comun' | 'araba' | 'bizkaia' | 'gipuzkoa' | 'navarra'
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Compute all Modelo 303 casillas and return the full self-assessment.

        Args:
            base_4: Base imponible al tipo superreducido 4% (casilla 01).
            base_10: Base imponible al tipo reducido 10% (casilla 04).
            base_21: Base imponible al tipo general 21% (casilla 07).
            base_intracomunitarias: Base de adquisiciones intracomunitarias (casilla 10).
            tipo_intracomunitarias: Tipo aplicado a las adquisiciones intracomunitarias (casilla 11),
                expressed as a percentage, e.g. 21.0.  The corresponding cuota (casilla 12)
                is calculated automatically.
            base_inversion_sp: Base de operaciones en inversion del sujeto pasivo (casilla 13).
            tipo_inversion_sp: Tipo aplicado a la ISP (casilla 13 bis), default 21%.
                The cuota (casilla 14) is calculated automatically.
            mod_bases: Modificacion de bases imponibles de periodos anteriores (casilla 15), signed.
            mod_cuotas: Modificacion de cuotas de periodos anteriores (casilla 16), signed.
                Negative value = rectification in favour of the taxpayer.
            base_corrientes_interiores: Base de IVA soportado en operaciones corrientes
                interiores, purely informative (casilla 28).
            cuota_corrientes_interiores: Cuota soportada en operaciones corrientes interiores
                deducible (casilla 29).
            base_inversion_interiores: Base de bienes de inversion interiores (casilla 30),
                informative.
            cuota_inversion_interiores: Cuota deducible de bienes de inversion interiores
                (casilla 31).
            base_importaciones_corrientes: Base de importaciones corrientes (casilla 32),
                informative.
            cuota_importaciones_corrientes: Cuota deducible de importaciones corrientes
                (casilla 33).
            base_importaciones_inversion: Base de importaciones de bienes de inversion
                (casilla 34), informative.
            cuota_importaciones_inversion: Cuota deducible de importaciones de inversion
                (casilla 35).
            base_intracom_corrientes: Base de adquisiciones intracomunitarias corrientes
                (casilla 36), informative.
            cuota_intracom_corrientes: Cuota deducible de adquisiciones intracomunitarias
                corrientes (casilla 37).
            base_intracom_inversion: Base de adquisiciones intracomunitarias de inversion
                (casilla 38), informative.
            cuota_intracom_inversion: Cuota deducible de adquisiciones intracomunitarias
                de inversion (casilla 39).
            base_rectificacion_deducciones: Base de las cuotas deducibles rectificadas
                (casilla 40), informative, signed.
            rectificacion_deducciones: Cuota neta de rectificacion de deducciones (casilla 41),
                signed.  Positive = additional deduction; negative = reduction of prior deduction.
            compensacion_agricultura: Compensaciones del regimen especial de agricultura,
                ganaderia y pesca satisfechas (casilla 42).
            regularizacion_inversion: Regularizacion de bienes de inversion (art. 107-110 LIVA),
                (casilla 43), signed.
            regularizacion_prorrata: Regularizacion por variacion del porcentaje definitivo de
                prorrata (casilla 44), signed.  Only filled in 4T.
            pct_atribucion_estado: Percentage of the result attributable to Estado / territorio
                comun (casilla 65).  100.0 for most declarants.
            iva_aduana_pendiente: Cuotas de IVA a la importacion liquidadas por la Aduana
                pendientes de ingreso (casilla 77).
            cuotas_compensar_anteriores: Cuotas a compensar de periodos anteriores (casilla 78).
                Must be >= 0.
            regularizacion_anual: Regularizacion cuotas art. 80.cinco.5a LIVA (casilla 68).
                Only applicable in 4T.  Signed.
            resultado_anterior_complementaria: Resultado de la declaracion anterior cuando se
                presenta declaracion complementaria (casilla 70).
            quarter: Fiscal quarter (1-4).  Affects whether regularizacion_anual is allowed.
            year: Fiscal year.
            territory: Territory identifier for informational purposes.
                'comun' | 'araba' | 'bizkaia' | 'gipuzkoa' | 'navarra'

        Returns:
            Dict containing every casilla value plus structured breakdowns:
            - casilla_01 … casilla_71: individual form field values
            - total_devengado, total_deducible, resultado_regimen_general
            - resultado_liquidacion: final settlement amount (positive = to pay, negative = to refund/compensate)
            - desglose_devengado: dict with per-rate and per-concept breakdown of output tax
            - desglose_deducible: dict with per-concept breakdown of deductible input tax
            - territory, quarter, year
        """
        # ------------------------------------------------------------------
        # 0. PRE-CHECKS — Regimen Equivalencia + RECC + SII
        # ------------------------------------------------------------------

        # 0.a Recargo Equivalencia: si aplica y strict_block, devuelve bloqueo
        re_aplica = self.is_recargo_equivalencia(
            situacion_laboral=re_situacion_laboral,
            cnae=re_cnae,
            iae=re_iae,
            es_persona_fisica=re_es_persona_fisica,
            es_minorista=re_es_minorista,
        )
        if re_aplica and re_strict_block:
            return {
                "bloqueo_re": True,
                "presenta_303": False,
                "modelo_recomendado": "308 (devolucion intracom/ISP) o ninguno",
                "mensaje": (
                    "Sujeto en Recargo de Equivalencia (Art. 154-163 LIVA). "
                    "NO presentas Modelo 303 — el IVA + RE lo declara y paga "
                    "tu proveedor en cada factura de compra (5,2% / 1,4% / 0,5% / 1,75%). "
                    "Solo presentas Modelo 308 si tienes adquisiciones intracomunitarias "
                    "o ISP que generen derecho a devolucion del recargo."
                ),
                "territory": territory,
                "quarter": quarter,
                "year": year,
            }

        # 0.b RECC: validar elegibilidad si esta activo
        recc_info = self._calc_recc(
            regimen_recc=regimen_recc,
            volumen_ano_anterior=volumen_ano_anterior,
            cobros_pendientes_anteriores=cobros_pendientes_recc,
            pagos_pendientes_anteriores=pagos_pendientes_recc,
            year=year,
        )

        # 0.c SII: detectar obligacion / aviso plazo mensual
        sii_obligatorio = self.requiere_sii(volumen_ano_anterior, redeme=redeme, grupo_iva=grupo_iva)
        sii_aplicado = bool(en_sii or sii_obligatorio)
        sii_info = {
            "obligatorio": sii_obligatorio,
            "aplicado": sii_aplicado,
            "periodicidad": "mensual" if sii_aplicado else "trimestral",
            "umbral_obligatorio": _UMBRAL_SII_OBLIGATORIO,
            "volumen_declarado": volumen_ano_anterior,
            "redeme": redeme,
            "grupo_iva": grupo_iva,
            "warning": (
                "SII: presentacion mensual obligatoria (30 dias naturales del mes "
                "siguiente; agosto excluido)."
            ) if sii_aplicado else None,
        }

        # 0.d ISP por supuesto: genera devengado y (opcionalmente) deducible
        isp_info = self._calc_isp(bases_isp)

        # 0.e Modificaciones bases (Art. 80 + 89 LIVA)
        mods_info = self._calc_mod_bases(mods_bases)

        # 0.f Tipos transitorios alimentacion / aceites
        trans_info = self._calc_transitorios(bases_transitorias, year=year, mes=mes_inicio_periodo)

        # ------------------------------------------------------------------
        # 1. IVA DEVENGADO (output tax)
        # ------------------------------------------------------------------

        # Casillas 01-03: tipo superreducido 4%
        casilla_01 = round(base_4, 2)
        casilla_02 = _TIPO_SUPERREDUCIDO
        casilla_03 = round(base_4 * _TIPO_SUPERREDUCIDO / 100, 2)

        # Casillas 04-06: tipo reducido 10%
        casilla_04 = round(base_10, 2)
        casilla_05 = _TIPO_REDUCIDO
        casilla_06 = round(base_10 * _TIPO_REDUCIDO / 100, 2)

        # Casillas 07-09: tipo general 21%
        casilla_07 = round(base_21, 2)
        casilla_08 = _TIPO_GENERAL
        casilla_09 = round(base_21 * _TIPO_GENERAL / 100, 2)

        # Casillas 10-12: adquisiciones intracomunitarias
        casilla_10 = round(base_intracomunitarias, 2)
        casilla_11 = round(tipo_intracomunitarias, 2)
        casilla_12 = round(base_intracomunitarias * tipo_intracomunitarias / 100, 2)

        # Casillas 13-14: inversion del sujeto pasivo
        casilla_13 = round(base_inversion_sp, 2)
        casilla_14 = round(base_inversion_sp * tipo_inversion_sp / 100, 2)

        # Casillas 15-16: modificacion de bases y cuotas (+/-)
        casilla_15 = round(mod_bases, 2)
        casilla_16 = round(mod_cuotas, 2)

        # P1/P2 — devengado adicional (no rompe casillas existentes):
        # - ISP por supuesto (si bases_isp se especifican, suma a la casilla_14
        #   ya calculada arriba via base_inversion_sp; aqui lo modelamos como
        #   adicional). Para mantener backwards-compat, base_inversion_sp se
        #   conserva como "ISP genericamente" y bases_isp como desglose extra.
        cuota_isp_extra = isp_info["total_cuota_isp"]
        cuota_mod_extra = mods_info["total_cuota_modificaciones"]
        cuota_transitorios = trans_info["cuota_total_transitorios"]

        # RECC: cobros materializados de devengo anterior (devengo diferido)
        # se suman al devengado del periodo
        cuota_recc_devengado = 0.0
        if recc_info["regimen_aplicado"]:
            cuota_recc_devengado = round(cobros_pendientes_recc, 2)

        # Casilla 27: TOTAL IVA DEVENGADO
        casilla_27 = round(
            casilla_03
            + casilla_06
            + casilla_09
            + casilla_12
            + casilla_14
            + casilla_16
            + cuota_isp_extra
            + cuota_mod_extra
            + cuota_transitorios
            + cuota_recc_devengado,
            2,
        )

        # ------------------------------------------------------------------
        # 2. IVA DEDUCIBLE (input tax)
        # ------------------------------------------------------------------

        # Casillas 28-29: bienes/servicios corrientes interiores
        casilla_28 = round(base_corrientes_interiores, 2)       # informative base
        casilla_29 = round(cuota_corrientes_interiores, 2)

        # Casillas 30-31: bienes de inversion interiores
        casilla_30 = round(base_inversion_interiores, 2)        # informative base
        casilla_31 = round(cuota_inversion_interiores, 2)

        # Casillas 32-33: importaciones corrientes
        casilla_32 = round(base_importaciones_corrientes, 2)    # informative base
        casilla_33 = round(cuota_importaciones_corrientes, 2)

        # Casillas 34-35: importaciones de bienes de inversion
        casilla_34 = round(base_importaciones_inversion, 2)     # informative base
        casilla_35 = round(cuota_importaciones_inversion, 2)

        # Casillas 36-37: adquisiciones intracomunitarias corrientes
        casilla_36 = round(base_intracom_corrientes, 2)         # informative base
        casilla_37 = round(cuota_intracom_corrientes, 2)

        # Casillas 38-39: adquisiciones intracomunitarias de inversion
        casilla_38 = round(base_intracom_inversion, 2)          # informative base
        casilla_39 = round(cuota_intracom_inversion, 2)

        # Casillas 40-41: rectificacion de deducciones (+/-)
        casilla_40 = round(base_rectificacion_deducciones, 2)   # informative base
        casilla_41 = round(rectificacion_deducciones, 2)

        # Casilla 42: compensaciones regimen especial agricultura
        casilla_42 = round(compensacion_agricultura, 2)

        # Casilla 43: regularizacion bienes de inversion (+/-)
        casilla_43 = round(regularizacion_inversion, 2)

        # Casilla 44: regularizacion prorrata (+/-)
        casilla_44 = round(regularizacion_prorrata, 2)

        # P1/P2 — deducible adicional:
        # - ISP por supuesto: si la actividad permite deducir, la cuota ISP
        #   tambien es deducible simultaneamente (Art. 84.uno.2).
        # - RECC: pagos materializados generan deduccion en el periodo.
        cuota_isp_deducible = cuota_isp_extra if isp_es_deducible else 0.0
        cuota_recc_deducible = 0.0
        if recc_info["regimen_aplicado"]:
            cuota_recc_deducible = round(pagos_pendientes_recc, 2)

        # Casilla 45: TOTAL A DEDUCIR
        casilla_45 = round(
            casilla_29
            + casilla_31
            + casilla_33
            + casilla_35
            + casilla_37
            + casilla_39
            + casilla_41
            + casilla_42
            + casilla_43
            + casilla_44
            + cuota_isp_deducible
            + cuota_recc_deducible,
            2,
        )

        # ------------------------------------------------------------------
        # 3. RESULTADO
        # ------------------------------------------------------------------

        # Casilla 46: resultado regimen general = devengado - deducible
        casilla_46 = round(casilla_27 - casilla_45, 2)

        # Casilla 64: suma de resultados (= casilla_46; no simplificado)
        casilla_64 = casilla_46

        # Casilla 65: % atribucion territorio comun
        casilla_65 = round(pct_atribucion_estado, 4)

        # Casilla 66: importe atribuible al Estado
        casilla_66 = round(casilla_64 * casilla_65 / 100, 2)

        # Casilla 77: IVA importacion Aduana pendiente de ingreso
        casilla_77 = round(iva_aduana_pendiente, 2)

        # Casilla 78: cuotas a compensar de periodos anteriores (>= 0)
        cuotas_compensar_anteriores = max(0.0, cuotas_compensar_anteriores)
        casilla_78 = round(cuotas_compensar_anteriores, 2)

        # Casilla 68: regularizacion anual (solo 4T; ignored in other quarters)
        if quarter == 4:
            casilla_68 = round(regularizacion_anual, 2)
        else:
            casilla_68 = 0.0

        # Casilla 69: resultado previo = 66 + 77 - 78 + 68
        casilla_69 = round(casilla_66 + casilla_77 - casilla_78 + casilla_68, 2)

        # Casilla 70: resultado declaracion anterior (complementaria)
        casilla_70 = round(resultado_anterior_complementaria, 2)

        # Casilla 71: RESULTADO LIQUIDACION
        casilla_71 = round(casilla_69 - casilla_70, 2)

        # ------------------------------------------------------------------
        # 4. Descriptive breakdowns
        # ------------------------------------------------------------------
        desglose_devengado = {
            "superreducido_4pct": {
                "base": casilla_01,
                "tipo": casilla_02,
                "cuota": casilla_03,
            },
            "reducido_10pct": {
                "base": casilla_04,
                "tipo": casilla_05,
                "cuota": casilla_06,
            },
            "general_21pct": {
                "base": casilla_07,
                "tipo": casilla_08,
                "cuota": casilla_09,
            },
            "intracomunitarias": {
                "base": casilla_10,
                "tipo": casilla_11,
                "cuota": casilla_12,
            },
            "inversion_sujeto_pasivo": {
                "base": casilla_13,
                "cuota": casilla_14,
            },
            "modificacion_bases_cuotas": {
                "bases": casilla_15,
                "cuotas": casilla_16,
            },
            "total_devengado": casilla_27,
        }

        desglose_deducible = {
            "corrientes_interiores": {
                "base_informativa": casilla_28,
                "cuota": casilla_29,
            },
            "inversion_interiores": {
                "base_informativa": casilla_30,
                "cuota": casilla_31,
            },
            "importaciones_corrientes": {
                "base_informativa": casilla_32,
                "cuota": casilla_33,
            },
            "importaciones_inversion": {
                "base_informativa": casilla_34,
                "cuota": casilla_35,
            },
            "intracom_corrientes": {
                "base_informativa": casilla_36,
                "cuota": casilla_37,
            },
            "intracom_inversion": {
                "base_informativa": casilla_38,
                "cuota": casilla_39,
            },
            "rectificacion_deducciones": {
                "base_informativa": casilla_40,
                "cuota": casilla_41,
            },
            "compensacion_agricultura": casilla_42,
            "regularizacion_bienes_inversion": casilla_43,
            "regularizacion_prorrata": casilla_44,
            "total_deducible": casilla_45,
        }

        return {
            # --- IVA devengado ---
            "casilla_01": casilla_01,
            "casilla_02": casilla_02,
            "casilla_03": casilla_03,
            "casilla_04": casilla_04,
            "casilla_05": casilla_05,
            "casilla_06": casilla_06,
            "casilla_07": casilla_07,
            "casilla_08": casilla_08,
            "casilla_09": casilla_09,
            "casilla_10": casilla_10,
            "casilla_11": casilla_11,
            "casilla_12": casilla_12,
            "casilla_13": casilla_13,
            "casilla_14": casilla_14,
            "casilla_15": casilla_15,
            "casilla_16": casilla_16,
            "casilla_27": casilla_27,
            # --- IVA deducible ---
            "casilla_28": casilla_28,
            "casilla_29": casilla_29,
            "casilla_30": casilla_30,
            "casilla_31": casilla_31,
            "casilla_32": casilla_32,
            "casilla_33": casilla_33,
            "casilla_34": casilla_34,
            "casilla_35": casilla_35,
            "casilla_36": casilla_36,
            "casilla_37": casilla_37,
            "casilla_38": casilla_38,
            "casilla_39": casilla_39,
            "casilla_40": casilla_40,
            "casilla_41": casilla_41,
            "casilla_42": casilla_42,
            "casilla_43": casilla_43,
            "casilla_44": casilla_44,
            "casilla_45": casilla_45,
            # --- Resultado ---
            "casilla_46": casilla_46,
            "casilla_64": casilla_64,
            "casilla_65": casilla_65,
            "casilla_66": casilla_66,
            "casilla_68": casilla_68,
            "casilla_69": casilla_69,
            "casilla_70": casilla_70,
            "casilla_71": casilla_71,
            "casilla_77": casilla_77,
            "casilla_78": casilla_78,
            # --- Summary fields ---
            "total_devengado": casilla_27,
            "total_deducible": casilla_45,
            "resultado_regimen_general": casilla_46,
            "resultado_liquidacion": casilla_71,
            # --- Breakdowns ---
            "desglose_devengado": desglose_devengado,
            "desglose_deducible": desglose_deducible,
            # --- P1/P2 EXTENSIONS (audit 2026-05) ---
            "regimen_recc": recc_info,
            "sii": sii_info,
            "isp_desglose": isp_info,
            "modificaciones_bases": mods_info,
            "tipos_transitorios": trans_info,
            "recargo_equivalencia": {
                "detectado": re_aplica,
                "presenta_303": not re_aplica,
                "tipos_re_vigentes": RE_RATES_FULL,
            },
            "warnings": (
                ([recc_info["warning"]] if recc_info["warning"] else [])
                + ([sii_info["warning"]] if sii_info["warning"] else [])
                + trans_info["warnings"]
            ),
            # --- Metadata ---
            "territory": territory,
            "quarter": quarter,
            "year": year,
        }
