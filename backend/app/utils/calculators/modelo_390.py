"""
Modelo 390 — Declaracion-Resumen Anual del IVA.

Norma:
    - Orden EHA/3111/2009 (modelo 390 actual)
    - Modificaciones: Orden HFP/417/2017, Orden HAC/1395/2021, etc.
    - Excepcion exoneracion: Art. 71.7 RIVA (RD 1624/1992) +
      Disp. Adicional unica Orden HFP/417/2017.

Plazo: 1 al 30 de enero del año siguiente al ejercicio declarado.

Variantes territoriales (un sujeto NO presenta 390 si esta en estos regimenes):
    - Canarias  → Modelo 425 (resumen anual IGIC, Gobierno de Canarias)
    - Bizkaia   → Modelo 391 foral (Norma Foral 7/1994 + Decreto Foral)
    - Araba     → Modelo 391 foral
    - Gipuzkoa  → Modelo 391 foral (Hacienda de Gipuzkoa)
    - Navarra   → Modelo F-66 foral (Hacienda Foral de Navarra)
    - Ceuta / Melilla → IPSI (no IVA, no aplica 390)

Sujetos exonerados de presentar 390 (Art. 71.7 RIVA):
    1. Sujetos pasivos incluidos en SII (Suministro Inmediato de Informacion).
       SII es obligatorio si el volumen de operaciones del año anterior
       supera 6.010.121,04 EUR (Art. 121 LIVA).
    2. Inscritos en REDEME (Registro de Devolucion Mensual del IVA).
    3. Grupos de IVA (Cap. IX Tit. IX LIVA).
    4. Sujetos en regimen simplificado o recargo de equivalencia
       exclusivamente, sin obligacion de presentar 303 (sustituido por
       declaracion final 4T con datos adicionales).

Esta calculadora:
    - Agrega 4 modelos 303 trimestrales (T1+T2+T3+T4) → casillas resumen anual.
    - Detecta automaticamente exoneracion por SII / REDEME / grupo IVA / RE puro.
    - Detecta variante territorial (390 / 391 / F-66 / 425) y devuelve el
      modelo aplicable.

NOTA: Solo cubre regimen general. Los apartados informativos detallados
(volumen de operaciones por epigrafe, exenciones, exportaciones agregadas)
quedan para futura iteracion (datos no capturados hoy en `Modelo303Calculator`).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.utils.ccaa_constants import (
    CANARIAS_SET,
    CEUTA_MELILLA,
    FORAL_VASCO,
    FORAL_NAVARRA,
    normalize_ccaa,
)
from app.utils.tax_parameter_repository import TaxParameterRepository

# Umbral SII (volumen operaciones año anterior, Art. 121 LIVA)
UMBRAL_SII_EUR: float = 6_010_121.04

# Regimenes especiales que (exclusivos) exoneran de presentar 390
REGIMENES_EXONERAN_SOLOS = {
    "simplificado",  # Modulos IVA — sustituye 390 por 303 4T+datos
    "recargo_equivalencia",  # RE comerciante minorista
}


class Modelo390Calculator:
    """
    Calcula el Modelo 390 (Resumen Anual IVA) sumando 4 trimestres del 303
    y aplicando las reglas de exoneracion del Art. 71.7 RIVA.
    """

    def __init__(self, repo: Optional[TaxParameterRepository] = None) -> None:
        self._repo = repo

    # ------------------------------------------------------------------ #
    # Helpers de exoneracion (Art. 71.7 RIVA)
    # ------------------------------------------------------------------ #

    @staticmethod
    def check_exoneracion_sii(
        volumen_operaciones_ano_anterior: float = 0.0,
        sii_voluntario: bool = False,
    ) -> Dict[str, Any]:
        """
        Detecta si el sujeto esta obligado a SII y por tanto exonerado del 390.

        Args:
            volumen_operaciones_ano_anterior: facturacion del año anterior (EUR).
            sii_voluntario: True si el sujeto se ha acogido voluntariamente a SII
                aunque no supere el umbral.

        Returns:
            {"exonerado": bool, "motivo": str, "umbral": float}
        """
        if volumen_operaciones_ano_anterior > UMBRAL_SII_EUR:
            return {
                "exonerado": True,
                "motivo": (
                    f"Volumen operaciones ano anterior "
                    f"{volumen_operaciones_ano_anterior:,.2f} EUR > umbral "
                    f"{UMBRAL_SII_EUR:,.2f} EUR (Art. 121 LIVA) — SII obligatorio "
                    f"y exoneracion 390 (Art. 71.7 RIVA)."
                ),
                "umbral": UMBRAL_SII_EUR,
            }
        if sii_voluntario:
            return {
                "exonerado": True,
                "motivo": (
                    "Sujeto acogido voluntariamente a SII — " "exoneracion 390 (Art. 71.7 RIVA)."
                ),
                "umbral": UMBRAL_SII_EUR,
            }
        return {
            "exonerado": False,
            "motivo": "",
            "umbral": UMBRAL_SII_EUR,
        }

    @staticmethod
    def check_redeme(en_redeme: bool = False) -> Dict[str, Any]:
        """
        Detecta exoneracion por inscripcion en REDEME
        (Registro de Devolucion Mensual del IVA).
        """
        if en_redeme:
            return {
                "exonerado": True,
                "motivo": (
                    "Sujeto inscrito en REDEME (Registro de Devolucion Mensual "
                    "del IVA) — exoneracion 390 (Art. 71.7 RIVA)."
                ),
            }
        return {"exonerado": False, "motivo": ""}

    @staticmethod
    def check_grupo_iva(en_grupo_iva: bool = False) -> Dict[str, Any]:
        """Detecta exoneracion por pertenencia a grupo de IVA (Cap. IX Tit. IX LIVA)."""
        if en_grupo_iva:
            return {
                "exonerado": True,
                "motivo": (
                    "Sujeto pertenece a un grupo de IVA (Cap. IX Tit. IX LIVA) — "
                    "exoneracion 390 (Art. 71.7 RIVA)."
                ),
            }
        return {"exonerado": False, "motivo": ""}

    @staticmethod
    def check_regimen_especial_exclusivo(
        regimen_especial: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Detecta exoneracion por estar en regimen simplificado o recargo de
        equivalencia exclusivamente, sin obligacion de presentar 303.
        """
        if regimen_especial in REGIMENES_EXONERAN_SOLOS:
            etiqueta = {
                "simplificado": "regimen simplificado (modulos)",
                "recargo_equivalencia": "Recargo de Equivalencia",
            }[regimen_especial]
            return {
                "exonerado": True,
                "motivo": (
                    f"Sujeto en {etiqueta} exclusivamente — "
                    f"exoneracion 390 (Art. 71.7 RIVA). El resumen anual se "
                    f"sustituye por la declaracion 4T con datos adicionales."
                ),
            }
        return {"exonerado": False, "motivo": ""}

    # ------------------------------------------------------------------ #
    # Variante territorial (390 / 391 / F-66 / 425)
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_variante_territorial(territory: Optional[str]) -> Dict[str, Any]:
        """
        Devuelve el modelo de resumen anual aplicable segun el territorio.

        Returns dict con:
            - modelo: "390" | "391" | "F-66" | "425" | None (si no aplica)
            - hacienda: organo de presentacion
            - aplica_iva: bool (False para Ceuta/Melilla — IPSI)
            - nota: explicacion territorial
        """
        if not territory:
            return {
                "modelo": "390",
                "hacienda": "AEAT (sede.agenciatributaria.gob.es)",
                "aplica_iva": True,
                "nota": "Regimen comun — Modelo 390 AEAT.",
                "territory": None,
            }

        canonical = normalize_ccaa(territory)

        # Canarias → IGIC Modelo 425
        if canonical in CANARIAS_SET:
            return {
                "modelo": "425",
                "hacienda": "Gobierno de Canarias (sede.gobiernodecanarias.org)",
                "aplica_iva": False,
                "nota": (
                    "Canarias aplica IGIC, no IVA. El resumen anual es el " "Modelo 425, NO el 390."
                ),
                "territory": canonical,
            }

        # Ceuta / Melilla → IPSI (no IVA, no 390)
        if canonical in CEUTA_MELILLA:
            return {
                "modelo": None,
                "hacienda": f"Ciudad Autonoma de {canonical}",
                "aplica_iva": False,
                "nota": (
                    f"En {canonical} se aplica IPSI (Impuesto sobre la Produccion, "
                    f"los Servicios y la Importacion), no IVA. No existe modelo "
                    f"390 ni equivalente; las autoliquidaciones IPSI son "
                    f"trimestrales y no hay resumen anual obligatorio."
                ),
                "territory": canonical,
            }

        # Pais Vasco foral
        if canonical in FORAL_VASCO:
            mapping = {
                "Bizkaia": (
                    "Hacienda Foral de Bizkaia (bizkaia.eus)",
                    "Norma Foral 7/1994 + Decreto Foral. Equivalente foral del 390.",
                ),
                "Araba": (
                    "Hacienda Foral de Araba (araba.eus)",
                    "Equivalente foral del 390 en Araba.",
                ),
                "Gipuzkoa": (
                    "Hacienda Foral de Gipuzkoa (gipuzkoa.eus)",
                    "Equivalente foral del 390 en Gipuzkoa.",
                ),
            }
            hacienda, base_note = mapping[canonical]
            return {
                "modelo": "391",
                "hacienda": hacienda,
                "aplica_iva": True,
                "nota": (
                    f"En {canonical} el resumen anual de IVA se presenta como "
                    f"Modelo 391 ante {hacienda}. {base_note}"
                ),
                "territory": canonical,
            }

        # Navarra foral
        if canonical in FORAL_NAVARRA:
            return {
                "modelo": "F-66",
                "hacienda": "Hacienda Foral de Navarra (hacienda.navarra.es)",
                "aplica_iva": True,
                "nota": (
                    "En Navarra el resumen anual de IVA se presenta como "
                    "Modelo F-66 ante Hacienda Foral de Navarra."
                ),
                "territory": canonical,
            }

        # Resto: regimen comun
        return {
            "modelo": "390",
            "hacienda": "AEAT (sede.agenciatributaria.gob.es)",
            "aplica_iva": True,
            "nota": "Regimen comun — Modelo 390 AEAT.",
            "territory": canonical,
        }

    # ------------------------------------------------------------------ #
    # Sumatorio anual a partir de 4 modelos 303 trimestrales
    # ------------------------------------------------------------------ #

    @staticmethod
    def build_from_303_quarterly(
        trimestres: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Agrega 4 resultados de Modelo303Calculator a casillas resumen anual del 390.

        Args:
            trimestres: lista de 4 dicts (uno por trimestre) compatibles con
                la salida de `Modelo303Calculator.calculate()`. Cada dict puede
                incluir las claves `casilla_03`, `casilla_06`, `casilla_09`,
                `casilla_12`, `casilla_14`, `casilla_27` (devengado), `casilla_29`,
                `casilla_31`, `casilla_33`, `casilla_37`, `casilla_45`
                (deducible), `resultado_liquidacion`, etc. Tambien acepta
                la salida del tool `calculate_modelo_303_tool` (con `iva_devengado`
                e `iva_deducible` anidados).

        Returns:
            Dict con casillas resumen anual del 390:
                - cuota_devengada_4 / 10 / 21 (anuales)
                - cuota_devengada_intra
                - cuota_devengada_isp
                - total_devengado_anual
                - cuota_deducible_corrientes / inversion / importaciones / intra
                - total_deducible_anual
                - resultado_liquidacion_anual
                - sumatorio_303 (lista de los 4 resultados trimestrales)
        """
        if not isinstance(trimestres, list) or len(trimestres) != 4:
            raise ValueError(
                f"Se requieren exactamente 4 trimestres del 303 para el "
                f"resumen anual del 390 (recibidos: "
                f"{len(trimestres) if isinstance(trimestres, list) else 'N/A'})"
            )

        def _get(t: Dict[str, Any], *keys: str, default: float = 0.0) -> float:
            """Lookup robusto: busca la clave en el dict plano o en sub-dicts."""
            for k in keys:
                if k in t:
                    val = t[k]
                    if isinstance(val, (int, float)):
                        return float(val)
            # Fallback: estructura del tool calculate_modelo_303_tool
            iva_dev = t.get("iva_devengado") or {}
            iva_ded = t.get("iva_deducible") or {}
            resultado_d = t.get("resultado") or {}
            for src in (iva_dev, iva_ded, resultado_d):
                for k in keys:
                    if k in src:
                        val = src[k]
                        if isinstance(val, (int, float)):
                            return float(val)
            return default

        # IVA devengado anual
        cuota_4_anual = sum(_get(t, "casilla_03", "cuota_4") for t in trimestres)
        cuota_10_anual = sum(_get(t, "casilla_06", "cuota_10") for t in trimestres)
        cuota_21_anual = sum(_get(t, "casilla_09", "cuota_21") for t in trimestres)
        cuota_intra_anual = sum(_get(t, "casilla_12", "cuota_intracomunitaria") for t in trimestres)
        cuota_isp_anual = sum(_get(t, "casilla_14") for t in trimestres)
        total_devengado = sum(_get(t, "casilla_27", "total_devengado") for t in trimestres)

        # IVA deducible anual
        cuota_corrientes = sum(_get(t, "casilla_29", "bienes_corrientes") for t in trimestres)
        cuota_inversion = sum(_get(t, "casilla_31", "bienes_inversion") for t in trimestres)
        cuota_importaciones = sum(_get(t, "casilla_33", "importaciones") for t in trimestres)
        cuota_intra_ded = sum(_get(t, "casilla_37", "intracomunitarias") for t in trimestres)
        total_deducible = sum(_get(t, "casilla_45", "total_deducible") for t in trimestres)

        # Resultado liquidacion anual (suma de resultados trimestrales)
        resultado_anual = sum(
            _get(t, "resultado_liquidacion", "resultado_final") for t in trimestres
        )

        return {
            "cuota_devengada_4": round(cuota_4_anual, 2),
            "cuota_devengada_10": round(cuota_10_anual, 2),
            "cuota_devengada_21": round(cuota_21_anual, 2),
            "cuota_devengada_intra": round(cuota_intra_anual, 2),
            "cuota_devengada_isp": round(cuota_isp_anual, 2),
            "total_devengado_anual": round(total_devengado, 2),
            "cuota_deducible_corrientes": round(cuota_corrientes, 2),
            "cuota_deducible_inversion": round(cuota_inversion, 2),
            "cuota_deducible_importaciones": round(cuota_importaciones, 2),
            "cuota_deducible_intra": round(cuota_intra_ded, 2),
            "total_deducible_anual": round(total_deducible, 2),
            "resultado_liquidacion_anual": round(resultado_anual, 2),
            "sumatorio_303": list(trimestres),
        }

    # ------------------------------------------------------------------ #
    # Validacion completa de obligacion / exoneracion
    # ------------------------------------------------------------------ #

    @classmethod
    def validate_complete(
        cls,
        *,
        territory: Optional[str] = None,
        volumen_operaciones_ano_anterior: float = 0.0,
        en_redeme: bool = False,
        en_grupo_iva: bool = False,
        sii_voluntario: bool = False,
        regimen_especial: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Determina si el sujeto debe presentar 390 (o variante territorial).

        Returns:
            Dict con:
                - obligado: bool
                - modelo: "390" | "391" | "F-66" | "425" | None
                - motivo_exoneracion: str (vacio si obligado)
                - territory_info: salida de get_variante_territorial()
                - exoneraciones_aplicables: list de chequeos individuales
        """
        territory_info = cls.get_variante_territorial(territory)

        # Caso 1: Ceuta/Melilla — no aplica modelo (IPSI, no IVA y no IGIC)
        if territory_info["modelo"] is None:
            return {
                "obligado": False,
                "modelo": None,
                "motivo_exoneracion": territory_info["nota"],
                "territory_info": territory_info,
                "exoneraciones_aplicables": [],
            }

        # Caso 2: Canarias — sustituido por 425 (IGIC, no IVA)
        if territory_info["modelo"] == "425":
            return {
                "obligado": True,  # SI esta obligado, pero al 425 no al 390
                "modelo": "425",
                "motivo_exoneracion": "",
                "territory_info": territory_info,
                "exoneraciones_aplicables": [],
            }

        # Caso 3: chequeos de exoneracion (Art. 71.7 RIVA)
        chequeos: List[Dict[str, Any]] = []

        sii = cls.check_exoneracion_sii(
            volumen_operaciones_ano_anterior=volumen_operaciones_ano_anterior,
            sii_voluntario=sii_voluntario,
        )
        if sii["exonerado"]:
            chequeos.append({"chequeo": "SII", **sii})

        redeme = cls.check_redeme(en_redeme=en_redeme)
        if redeme["exonerado"]:
            chequeos.append({"chequeo": "REDEME", **redeme})

        grupo = cls.check_grupo_iva(en_grupo_iva=en_grupo_iva)
        if grupo["exonerado"]:
            chequeos.append({"chequeo": "Grupo IVA", **grupo})

        regimen = cls.check_regimen_especial_exclusivo(regimen_especial=regimen_especial)
        if regimen["exonerado"]:
            chequeos.append({"chequeo": "Regimen especial exclusivo", **regimen})

        if chequeos:
            motivos = " | ".join(c["motivo"] for c in chequeos)
            return {
                "obligado": False,
                "modelo": territory_info["modelo"],
                "motivo_exoneracion": motivos,
                "territory_info": territory_info,
                "exoneraciones_aplicables": chequeos,
            }

        return {
            "obligado": True,
            "modelo": territory_info["modelo"],
            "motivo_exoneracion": "",
            "territory_info": territory_info,
            "exoneraciones_aplicables": [],
        }

    # ------------------------------------------------------------------ #
    # API principal: calculate
    # ------------------------------------------------------------------ #

    async def calculate(
        self,
        *,
        trimestres_303: Optional[List[Dict[str, Any]]] = None,
        territory: Optional[str] = None,
        volumen_operaciones_ano_anterior: float = 0.0,
        en_redeme: bool = False,
        en_grupo_iva: bool = False,
        sii_voluntario: bool = False,
        regimen_especial: Optional[str] = None,
        year: int = 2025,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Calculo completo del Modelo 390:
            1. Determina variante territorial.
            2. Aplica chequeos de exoneracion (Art. 71.7 RIVA).
            3. Si esta obligado, agrega los 4 trimestres del 303 a casillas anuales.

        Args:
            trimestres_303: lista de 4 resultados del Modelo303Calculator.
                Solo necesario si el sujeto esta obligado.
            territory: CCAA o territorio del usuario.
            volumen_operaciones_ano_anterior: facturacion del año anterior (EUR).
            en_redeme: True si esta inscrito en REDEME.
            en_grupo_iva: True si pertenece a grupo de IVA.
            sii_voluntario: True si voluntariamente acogido a SII.
            regimen_especial: 'simplificado' | 'recargo_equivalencia' | None.
            year: ejercicio del resumen anual.

        Returns:
            Dict con:
                - obligado: bool
                - modelo: identificador del modelo aplicable
                - motivo_exoneracion: str
                - territory_info, exoneraciones_aplicables
                - resumen_anual: dict con casillas anuales (None si exonerado)
                - year, plazo, hacienda
        """
        validacion = self.validate_complete(
            territory=territory,
            volumen_operaciones_ano_anterior=volumen_operaciones_ano_anterior,
            en_redeme=en_redeme,
            en_grupo_iva=en_grupo_iva,
            sii_voluntario=sii_voluntario,
            regimen_especial=regimen_especial,
        )

        result: Dict[str, Any] = {
            "obligado": validacion["obligado"],
            "modelo": validacion["modelo"],
            "motivo_exoneracion": validacion["motivo_exoneracion"],
            "territory_info": validacion["territory_info"],
            "exoneraciones_aplicables": validacion["exoneraciones_aplicables"],
            "year": year,
            "plazo": f"1 al 30 de enero de {year + 1}",
            "hacienda": validacion["territory_info"]["hacienda"],
            "resumen_anual": None,
        }

        # Si esta exonerado o no aplica modelo, devolvemos sin sumatorio
        if not validacion["obligado"] or validacion["modelo"] is None:
            return result

        # Canarias: el calculo del 425 vive en Modelo420Calculator (anual)
        # y queda fuera de este calculator. Devolvemos solo la indicacion.
        if validacion["modelo"] == "425":
            return result

        # Sujeto obligado a 390/391/F-66 sin trimestres — devuelve solo metadata
        if not trimestres_303:
            return result

        result["resumen_anual"] = self.build_from_303_quarterly(trimestres_303)
        return result
