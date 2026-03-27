"""
Plusvalia Municipal Calculator (IIVTNU)

Impuesto sobre el Incremento de Valor de los Terrenos de Naturaleza Urbana.

Normativa:
- RDL 26/2021 (post STC 182/2021)
- Coeficientes maximos actualizados 2024 (Orden HFP/1177/2023)
- Tipo impositivo maximo: 30%
- El contribuyente elige el metodo (objetivo o real) que resulte menor

Exenciones (Art. 105 TRLRHL):
- Transmisiones entre conyuges por divorcio
- Dacion en pago de vivienda habitual
- Aportaciones a sociedad conyugal
"""
from typing import Dict, Any
import logging
import math

logger = logging.getLogger(__name__)

# Coeficientes maximos RDL 26/2021 actualizados 2024
# Key = anos completos de tenencia, Value = coeficiente maximo
COEFICIENTES_MAXIMOS: Dict[int, float] = {
    0: 0.15,   # Menos de 1 ano
    1: 0.15,
    2: 0.14,
    3: 0.15,
    4: 0.17,
    5: 0.20,
    6: 0.20,
    7: 0.20,
    8: 0.22,
    9: 0.22,
    10: 0.22,
    11: 0.22,
    12: 0.23,
    13: 0.26,
    14: 0.36,
    15: 0.45,
    16: 0.52,
    17: 0.60,
    18: 0.60,
    19: 0.60,
    20: 0.60,  # >= 20 anos: maximo 0.60
}

TIPO_IMPOSITIVO_MAXIMO = 30.0  # %


class PlusvaliaMunicipalCalculator:
    """
    Calcula el IIVTNU (plusvalia municipal) segun RDL 26/2021.

    Dos metodos de calculo:
    1. Metodo objetivo: Valor catastral suelo x Coeficiente x Tipo municipal
    2. Metodo real: (Precio venta - Precio adquisicion) x % suelo x Tipo municipal

    El contribuyente elige el que resulte en menor impuesto.
    """

    def _get_coeficiente(self, anos_tenencia: int) -> float:
        """Obtiene el coeficiente maximo para los anos de tenencia dados."""
        if anos_tenencia < 0:
            return 0.0
        capped = min(anos_tenencia, 20)
        return COEFICIENTES_MAXIMOS.get(capped, 0.60)

    def _calcular_metodo_objetivo(
        self,
        valor_catastral_suelo: float,
        anos_tenencia: int,
        tipo_impositivo: float,
    ) -> Dict[str, Any]:
        """
        Metodo objetivo (coeficientes).

        Base imponible = Valor catastral suelo x Coeficiente
        Cuota = Base imponible x Tipo impositivo
        """
        coeficiente = self._get_coeficiente(anos_tenencia)
        base_imponible = valor_catastral_suelo * coeficiente
        cuota = base_imponible * (tipo_impositivo / 100.0)

        return {
            "metodo": "objetivo",
            "valor_catastral_suelo": round(valor_catastral_suelo, 2),
            "coeficiente": coeficiente,
            "anos_tenencia": anos_tenencia,
            "base_imponible": round(base_imponible, 2),
            "tipo_impositivo": round(tipo_impositivo, 2),
            "cuota": round(cuota, 2),
        }

    def _calcular_metodo_real(
        self,
        precio_venta: float,
        precio_adquisicion: float,
        valor_catastral_suelo: float,
        valor_catastral_total: float,
        tipo_impositivo: float,
    ) -> Dict[str, Any]:
        """
        Metodo real (plusvalia efectiva).

        Porcentaje suelo = Valor catastral suelo / Valor catastral total
        Base imponible = (Precio venta - Precio adquisicion) x Porcentaje suelo
        Si base < 0 -> no hay plusvalia (STC 182/2021)
        Cuota = Base imponible x Tipo impositivo
        """
        if valor_catastral_total <= 0:
            return {
                "metodo": "real",
                "plusvalia_total": 0.0,
                "porcentaje_suelo": 0.0,
                "base_imponible": 0.0,
                "tipo_impositivo": round(tipo_impositivo, 2),
                "cuota": 0.0,
                "hay_plusvalia": False,
            }

        plusvalia_total = precio_venta - precio_adquisicion
        porcentaje_suelo = valor_catastral_suelo / valor_catastral_total
        base_imponible = plusvalia_total * porcentaje_suelo
        hay_plusvalia = base_imponible > 0

        if not hay_plusvalia:
            cuota = 0.0
            base_imponible = 0.0
        else:
            cuota = base_imponible * (tipo_impositivo / 100.0)

        return {
            "metodo": "real",
            "precio_venta": round(precio_venta, 2),
            "precio_adquisicion": round(precio_adquisicion, 2),
            "plusvalia_total": round(plusvalia_total, 2),
            "porcentaje_suelo": round(porcentaje_suelo, 4),
            "base_imponible": round(base_imponible, 2),
            "tipo_impositivo": round(tipo_impositivo, 2),
            "cuota": round(cuota, 2),
            "hay_plusvalia": hay_plusvalia,
        }

    async def calculate(
        self,
        *,
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
        Calcula el IIVTNU (plusvalia municipal) por ambos metodos
        y devuelve el mas favorable para el contribuyente.

        Args:
            precio_venta: Precio de transmision en euros.
            precio_adquisicion: Precio de adquisicion en euros.
            valor_catastral_total: Valor catastral total del inmueble.
            valor_catastral_suelo: Valor catastral del suelo.
            anos_tenencia: Anos completos de tenencia (0-20+).
            tipo_impositivo_municipal: Tipo impositivo del municipio (max 30%).
            es_vivienda_habitual_dacion: True si es dacion en pago de vivienda habitual.
            es_divorcio: True si es transmision entre conyuges por divorcio.

        Returns:
            Dict con desglose de ambos metodos, metodo elegido, cuota final,
            y posible exencion.
        """
        # --- Validacion de inputs ---
        if valor_catastral_suelo < 0 or valor_catastral_total < 0:
            return {
                "success": False,
                "error": "Los valores catastrales no pueden ser negativos.",
            }

        if anos_tenencia < 0:
            return {
                "success": False,
                "error": "Los anos de tenencia no pueden ser negativos.",
            }

        # Clamp tipo impositivo al maximo legal
        tipo = min(tipo_impositivo_municipal, TIPO_IMPOSITIVO_MAXIMO)
        if tipo <= 0:
            return {
                "success": False,
                "error": "El tipo impositivo municipal debe ser positivo.",
            }

        # --- Exenciones ---
        exento = False
        motivo_exencion = None

        if es_divorcio:
            exento = True
            motivo_exencion = (
                "Transmision entre conyuges por disolucion matrimonial "
                "(Art. 104.3 TRLRHL). Exenta de plusvalia municipal."
            )

        if es_vivienda_habitual_dacion:
            exento = True
            motivo_exencion = (
                "Dacion en pago de vivienda habitual "
                "(Art. 105.1.c TRLRHL). Exenta de plusvalia municipal."
            )

        if exento:
            return {
                "success": True,
                "exento": True,
                "motivo_exencion": motivo_exencion,
                "cuota_final": 0.0,
                "metodo_objetivo": None,
                "metodo_real": None,
                "metodo_elegido": None,
                "formatted_response": (
                    f"**Exento de plusvalia municipal**\n\n"
                    f"{motivo_exencion}\n\n"
                    f"Cuota a pagar: **0,00 EUR**"
                ),
            }

        # --- Calculo metodo objetivo ---
        objetivo = self._calcular_metodo_objetivo(
            valor_catastral_suelo=valor_catastral_suelo,
            anos_tenencia=anos_tenencia,
            tipo_impositivo=tipo,
        )

        # --- Calculo metodo real ---
        real = self._calcular_metodo_real(
            precio_venta=precio_venta,
            precio_adquisicion=precio_adquisicion,
            valor_catastral_suelo=valor_catastral_suelo,
            valor_catastral_total=valor_catastral_total,
            tipo_impositivo=tipo,
        )

        # --- STC 182/2021: Si no hay plusvalia real, no se paga ---
        if not real.get("hay_plusvalia", True) and precio_venta <= precio_adquisicion:
            return {
                "success": True,
                "exento": True,
                "motivo_exencion": (
                    "No existe incremento de valor del terreno (STC 182/2021). "
                    "Si el precio de venta es inferior o igual al de adquisicion, "
                    "no procede el pago del impuesto."
                ),
                "cuota_final": 0.0,
                "metodo_objetivo": objetivo,
                "metodo_real": real,
                "metodo_elegido": "ninguno",
                "formatted_response": (
                    f"**No procede el pago de plusvalia municipal (STC 182/2021)**\n\n"
                    f"Precio de venta: {precio_venta:,.2f} EUR\n"
                    f"Precio de adquisicion: {precio_adquisicion:,.2f} EUR\n"
                    f"No existe incremento de valor del terreno.\n\n"
                    f"Cuota a pagar: **0,00 EUR**"
                ),
            }

        # --- Elegir el metodo mas favorable ---
        cuota_objetivo = objetivo["cuota"]
        cuota_real = real["cuota"]

        # Si real no tiene plusvalia pero objetivo si, solo aplica objetivo
        if not real.get("hay_plusvalia", True):
            metodo_elegido = "objetivo"
            cuota_final = cuota_objetivo
        elif cuota_real <= cuota_objetivo:
            metodo_elegido = "real"
            cuota_final = cuota_real
        else:
            metodo_elegido = "objetivo"
            cuota_final = cuota_objetivo

        # --- Respuesta formateada ---
        formatted = (
            f"**Plusvalia Municipal (IIVTNU)**\n\n"
            f"**Metodo objetivo:**\n"
            f"- Valor catastral suelo: {valor_catastral_suelo:,.2f} EUR\n"
            f"- Coeficiente ({anos_tenencia} anos): {objetivo['coeficiente']}\n"
            f"- Base imponible: {objetivo['base_imponible']:,.2f} EUR\n"
            f"- Cuota (tipo {tipo:.1f}%): **{cuota_objetivo:,.2f} EUR**\n\n"
            f"**Metodo real:**\n"
            f"- Plusvalia total: {real.get('plusvalia_total', 0):,.2f} EUR\n"
            f"- Porcentaje suelo: {real.get('porcentaje_suelo', 0) * 100:.1f}%\n"
            f"- Base imponible: {real['base_imponible']:,.2f} EUR\n"
            f"- Cuota (tipo {tipo:.1f}%): **{cuota_real:,.2f} EUR**\n\n"
            f"**Metodo elegido: {metodo_elegido}** (el mas favorable)\n"
            f"**Cuota final a pagar: {cuota_final:,.2f} EUR**\n\n"
            f"_El contribuyente puede elegir el metodo que resulte en menor impuesto "
            f"(RDL 26/2021)._"
        )

        return {
            "success": True,
            "exento": False,
            "motivo_exencion": None,
            "cuota_final": round(cuota_final, 2),
            "metodo_objetivo": objetivo,
            "metodo_real": real,
            "metodo_elegido": metodo_elegido,
            "formatted_response": formatted,
        }
