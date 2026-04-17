"""Escalas del Impuesto sobre Sociedades por territorio.

Fuentes:
- Regimen comun: Art. 29 LIS (Ley 27/2014), actualizado Ley 7/2024
- Alava: NF 37/2013
- Bizkaia: NF 11/2013
- Gipuzkoa: NF 2/2014
- Navarra: LF 26/2016
- Canarias ZEC: Art. 43 Ley 19/1994
- Ceuta/Melilla: Art. 33.6 LIS
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ISTramo:
    base_hasta: float  # EUR, float("inf") para ilimitado
    tipo: float        # porcentaje (ej: 25.0)


@dataclass(frozen=True)
class ISRegimen:
    nombre: str
    tramos_general: list[ISTramo]
    tramos_pyme: list[ISTramo]         # facturacion <1M
    tramos_nueva_creacion: list[ISTramo]
    bonificacion_cuota: float          # 0.0 o 0.5 (Ceuta/Melilla)
    tipo_zec: float | None             # solo Canarias ZEC


# --- Regimen comun ---
COMUN = ISRegimen(
    nombre="comun",
    tramos_general=[ISTramo(float("inf"), 25.0)],
    tramos_pyme=[ISTramo(50_000, 23.0), ISTramo(float("inf"), 25.0)],
    tramos_nueva_creacion=[ISTramo(50_000, 15.0), ISTramo(float("inf"), 20.0)],
    bonificacion_cuota=0.0,
    tipo_zec=None,
)

# --- Forales ---
ALAVA = ISRegimen(
    nombre="foral_alava",
    tramos_general=[ISTramo(float("inf"), 24.0)],
    tramos_pyme=[ISTramo(50_000, 20.0), ISTramo(float("inf"), 24.0)],
    tramos_nueva_creacion=[ISTramo(50_000, 19.0), ISTramo(float("inf"), 24.0)],
    bonificacion_cuota=0.0,
    tipo_zec=None,
)

BIZKAIA = ISRegimen(
    nombre="foral_bizkaia",
    tramos_general=[ISTramo(float("inf"), 24.0)],
    tramos_pyme=[ISTramo(50_000, 20.0), ISTramo(float("inf"), 24.0)],
    tramos_nueva_creacion=[ISTramo(50_000, 19.0), ISTramo(float("inf"), 24.0)],
    bonificacion_cuota=0.0,
    tipo_zec=None,
)

GIPUZKOA = ISRegimen(
    nombre="foral_gipuzkoa",
    tramos_general=[ISTramo(float("inf"), 24.0)],
    tramos_pyme=[ISTramo(50_000, 20.0), ISTramo(float("inf"), 24.0)],
    tramos_nueva_creacion=[ISTramo(50_000, 19.0), ISTramo(float("inf"), 24.0)],
    bonificacion_cuota=0.0,
    tipo_zec=None,
)

NAVARRA = ISRegimen(
    nombre="foral_navarra",
    tramos_general=[ISTramo(float("inf"), 28.0)],
    tramos_pyme=[ISTramo(50_000, 23.0), ISTramo(float("inf"), 28.0)],
    tramos_nueva_creacion=[ISTramo(50_000, 15.0), ISTramo(float("inf"), 28.0)],
    bonificacion_cuota=0.0,
    tipo_zec=None,
)

CANARIAS_ZEC = ISRegimen(
    nombre="zec_canarias",
    tramos_general=[ISTramo(float("inf"), 4.0)],
    tramos_pyme=[ISTramo(float("inf"), 4.0)],
    tramos_nueva_creacion=[ISTramo(float("inf"), 4.0)],
    bonificacion_cuota=0.0,
    tipo_zec=4.0,
)

CEUTA_MELILLA = ISRegimen(
    nombre="ceuta_melilla",
    tramos_general=[ISTramo(float("inf"), 25.0)],
    tramos_pyme=[ISTramo(50_000, 23.0), ISTramo(float("inf"), 25.0)],
    tramos_nueva_creacion=[ISTramo(50_000, 15.0), ISTramo(float("inf"), 20.0)],
    bonificacion_cuota=0.5,  # 50% bonificacion cuota
    tipo_zec=None,
)


def get_is_regimen(territorio: str, es_zec: bool = False) -> ISRegimen:
    """Devuelve el regimen IS para un territorio.

    Usa los mismos nombres canonicos que ccaa_constants.py.
    """
    from app.utils.ccaa_constants import normalize_ccaa, FORAL_VASCO, CEUTA_MELILLA as CM_SET

    canon = normalize_ccaa(territorio)

    if es_zec and canon == "Canarias":
        return CANARIAS_ZEC
    if canon in FORAL_VASCO:
        return {"Araba": ALAVA, "Bizkaia": BIZKAIA, "Gipuzkoa": GIPUZKOA}[canon]
    if canon == "Navarra":
        return NAVARRA
    if canon in CM_SET:
        return CEUTA_MELILLA
    return COMUN


def calcular_cuota_por_tramos(base_imponible: float, tramos: list[ISTramo]) -> float:
    """Aplica escala progresiva IS y devuelve cuota integra."""
    if base_imponible <= 0:
        return 0.0
    cuota = 0.0
    restante = base_imponible
    prev_hasta = 0.0
    for tramo in tramos:
        ancho = tramo.base_hasta - prev_hasta if tramo.base_hasta != float("inf") else restante
        gravable = min(restante, ancho)
        cuota += gravable * tramo.tipo / 100
        restante -= gravable
        prev_hasta = tramo.base_hasta
        if restante <= 0:
            break
    return round(cuota, 2)


# --- Deducciones IS por territorio ---
@dataclass(frozen=True)
class ISDeduccionParams:
    id_pct: float           # I+D porcentaje
    it_pct: float           # IT porcentaje
    limite_deducciones_pct: float  # limite sobre cuota integra
    reserva_cap_pct: float  # reserva capitalizacion


IS_DEDUCCIONES_COMUN = ISDeduccionParams(id_pct=25.0, it_pct=12.0, limite_deducciones_pct=25.0, reserva_cap_pct=10.0)
IS_DEDUCCIONES_BIZKAIA = ISDeduccionParams(id_pct=30.0, it_pct=15.0, limite_deducciones_pct=35.0, reserva_cap_pct=10.0)
IS_DEDUCCIONES_GIPUZKOA = ISDeduccionParams(id_pct=30.0, it_pct=15.0, limite_deducciones_pct=35.0, reserva_cap_pct=10.0)
IS_DEDUCCIONES_NAVARRA = ISDeduccionParams(id_pct=25.0, it_pct=12.0, limite_deducciones_pct=25.0, reserva_cap_pct=10.0)


def get_is_deduccion_params(territorio: str) -> ISDeduccionParams:
    """Devuelve los parametros de deducciones IS para un territorio."""
    from app.utils.ccaa_constants import normalize_ccaa

    canon = normalize_ccaa(territorio)
    if canon == "Bizkaia":
        return IS_DEDUCCIONES_BIZKAIA
    if canon == "Gipuzkoa":
        return IS_DEDUCCIONES_GIPUZKOA
    if canon == "Navarra":
        return IS_DEDUCCIONES_NAVARRA
    return IS_DEDUCCIONES_COMUN
