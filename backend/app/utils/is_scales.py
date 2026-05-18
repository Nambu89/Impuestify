"""Escalas del Impuesto sobre Sociedades por territorio y ejercicio.

Fuentes:
- Regimen comun: Art. 29 LIS (Ley 27/2014), reformado por Ley 7/2024 (BOE-A-2024-26694, Disp. Final 8a)
- RDL 4/2024 (microempresa 23% ejercicio 2024)
- Ley 7/2024 (microempresa 17%/20% + ERD transitoria + reserva capitalizacion 20-30% + tributacion minima)
- Alava: NF 37/2013
- Bizkaia: NF 11/2013
- Gipuzkoa: NF 2/2014 + reforma NF 1/2025 (19%/17%/15% segun plantilla)
- Navarra: LF 26/2016 (microempresa 19%)
- Canarias ZEC: Art. 43 Ley 19/1994
- Ceuta/Melilla: Art. 33.6 LIS
- Donativos Sociedades: Art. 20 Ley 49/2002 (40% / 50% fidelizacion)
- BIN: Art. 26 LIS (suelo 1M, escala segun INCN)
- Reserva capitalizacion: Art. 25 LIS (15% 2024 / 20-30% 2025)
- Tributacion minima: Art. 30 bis LIS (15% BI / 10% nueva creacion)

Auditoria: docs/audits/modelo_200_validation_2026-05.md
"""

from __future__ import annotations
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Tramos / Regimen
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ISTramo:
    base_hasta: float  # EUR, float("inf") para ilimitado
    tipo: float  # porcentaje (ej: 25.0)


@dataclass(frozen=True)
class ISRegimen:
    """Escalas IS por regimen + ejercicio.

    `tramos_microempresa` corresponde a INCN < 1.000.000 EUR.
    `tramos_erd`         corresponde a 1.000.000 <= INCN < 10.000.000 EUR (Empresa Reducida Dimension).
    `tramos_general`     corresponde a INCN >= 10.000.000 EUR (o desconocido).
    `tramos_nueva_creacion` aplica a las primeras 2 ejercicios con BI positiva.
    """

    nombre: str
    tramos_general: list[ISTramo]
    tramos_microempresa: list[ISTramo]
    tramos_erd: list[ISTramo]
    tramos_nueva_creacion: list[ISTramo]
    bonificacion_cuota: float  # 0.0 o 0.5 (Ceuta/Melilla)
    tipo_zec: float | None  # solo Canarias ZEC


# ---------------------------------------------------------------------------
# Escalas por ejercicio (ordenadas para facil mantenimiento)
# ---------------------------------------------------------------------------

# --- Ejercicio 2024 (RDL 4/2024 vigente) ---
_COMUN_2024 = ISRegimen(
    nombre="comun",
    tramos_general=[ISTramo(float("inf"), 25.0)],
    # RDL 4/2024: microempresa 23/25 (50k al 23%, resto al 25%)
    tramos_microempresa=[ISTramo(50_000, 23.0), ISTramo(float("inf"), 25.0)],
    # ERD 1M-10M: 25% (sin reduccion especifica salvo reserva nivelacion Art. 105)
    tramos_erd=[ISTramo(float("inf"), 25.0)],
    # Art. 29.1 LIS pre-Ley 7/2024: nueva creacion 15/20 (50k al 15%, resto al 20%)
    tramos_nueva_creacion=[ISTramo(50_000, 15.0), ISTramo(float("inf"), 20.0)],
    bonificacion_cuota=0.0,
    tipo_zec=None,
)

# --- Ejercicio 2025 (Ley 7/2024) ---
_COMUN_2025 = ISRegimen(
    nombre="comun",
    tramos_general=[ISTramo(float("inf"), 25.0)],
    # Ley 7/2024 Disp. Final 8a: microempresa 17% (primeros 50k) + 20% (resto)
    tramos_microempresa=[ISTramo(50_000, 17.0), ISTramo(float("inf"), 20.0)],
    # ERD transitoria 2025-2029: arranca 24% en 2025, baja 1pp/ano hasta 20% en 2029
    tramos_erd=[ISTramo(float("inf"), 24.0)],
    tramos_nueva_creacion=[ISTramo(float("inf"), 15.0)],
    bonificacion_cuota=0.0,
    tipo_zec=None,
)

# --- Ejercicios 2026-2029 (calendario transitorio Ley 7/2024) ---
_COMUN_2026 = ISRegimen(
    nombre="comun",
    tramos_general=[ISTramo(float("inf"), 25.0)],
    # Microempresa transitoria: 17/20 ya estable desde 2025
    tramos_microempresa=[ISTramo(50_000, 17.0), ISTramo(float("inf"), 20.0)],
    # ERD 2026: 23%
    tramos_erd=[ISTramo(float("inf"), 23.0)],
    tramos_nueva_creacion=[ISTramo(float("inf"), 15.0)],
    bonificacion_cuota=0.0,
    tipo_zec=None,
)

# --- Forales 2024 ---
_ALAVA_2024 = ISRegimen(
    nombre="foral_alava",
    tramos_general=[ISTramo(float("inf"), 24.0)],
    tramos_microempresa=[ISTramo(50_000, 20.0), ISTramo(float("inf"), 24.0)],
    tramos_erd=[ISTramo(50_000, 20.0), ISTramo(float("inf"), 24.0)],
    tramos_nueva_creacion=[ISTramo(50_000, 19.0), ISTramo(float("inf"), 24.0)],
    bonificacion_cuota=0.0,
    tipo_zec=None,
)
_BIZKAIA_2024 = ISRegimen(
    nombre="foral_bizkaia",
    tramos_general=[ISTramo(float("inf"), 24.0)],
    tramos_microempresa=[ISTramo(50_000, 20.0), ISTramo(float("inf"), 24.0)],
    tramos_erd=[ISTramo(50_000, 20.0), ISTramo(float("inf"), 24.0)],
    tramos_nueva_creacion=[ISTramo(50_000, 19.0), ISTramo(float("inf"), 24.0)],
    bonificacion_cuota=0.0,
    tipo_zec=None,
)
_GIPUZKOA_2024 = ISRegimen(
    nombre="foral_gipuzkoa",
    tramos_general=[ISTramo(float("inf"), 24.0)],
    tramos_microempresa=[ISTramo(50_000, 20.0), ISTramo(float("inf"), 24.0)],
    tramos_erd=[ISTramo(50_000, 20.0), ISTramo(float("inf"), 24.0)],
    tramos_nueva_creacion=[ISTramo(50_000, 19.0), ISTramo(float("inf"), 24.0)],
    bonificacion_cuota=0.0,
    tipo_zec=None,
)
# Gipuzkoa NF 1/2025: tipos 19% (general), 17% (incremento plantilla),
# 15% (microempresa con incremento plantilla).
# El simulador no conoce el incremento de plantilla, por lo que aplica
# el escenario base 19%/17%/15% como aproximacion conservadora.
_GIPUZKOA_2025 = ISRegimen(
    nombre="foral_gipuzkoa",
    tramos_general=[ISTramo(float("inf"), 19.0)],  # NF 1/2025
    tramos_microempresa=[ISTramo(50_000, 15.0), ISTramo(float("inf"), 17.0)],
    tramos_erd=[ISTramo(50_000, 15.0), ISTramo(float("inf"), 17.0)],
    tramos_nueva_creacion=[ISTramo(50_000, 15.0), ISTramo(float("inf"), 19.0)],
    bonificacion_cuota=0.0,
    tipo_zec=None,
)
_NAVARRA_2024 = ISRegimen(
    nombre="foral_navarra",
    tramos_general=[ISTramo(float("inf"), 28.0)],
    # Navarra 2024 mantiene escala 23/28 microempresa (LF 26/2016 sin aplicar
    # microempresa unica 19% hasta su entrada efectiva). Aplicar 19% requiere
    # ejercicio futuro mapeado en SCALES_BY_YEAR.
    tramos_microempresa=[ISTramo(50_000, 23.0), ISTramo(float("inf"), 28.0)],
    tramos_erd=[ISTramo(50_000, 23.0), ISTramo(float("inf"), 28.0)],
    tramos_nueva_creacion=[ISTramo(50_000, 15.0), ISTramo(float("inf"), 28.0)],
    bonificacion_cuota=0.0,
    tipo_zec=None,
)
# Navarra 2025 — microempresa 19% (LF 26/2016 plenamente vigente).
_NAVARRA_2025 = ISRegimen(
    nombre="foral_navarra",
    tramos_general=[ISTramo(float("inf"), 28.0)],
    tramos_microempresa=[ISTramo(float("inf"), 19.0)],
    tramos_erd=[ISTramo(50_000, 23.0), ISTramo(float("inf"), 28.0)],
    tramos_nueva_creacion=[ISTramo(50_000, 15.0), ISTramo(float("inf"), 28.0)],
    bonificacion_cuota=0.0,
    tipo_zec=None,
)
_CANARIAS_ZEC = ISRegimen(
    nombre="zec_canarias",
    tramos_general=[ISTramo(float("inf"), 4.0)],
    tramos_microempresa=[ISTramo(float("inf"), 4.0)],
    tramos_erd=[ISTramo(float("inf"), 4.0)],
    tramos_nueva_creacion=[ISTramo(float("inf"), 4.0)],
    bonificacion_cuota=0.0,
    tipo_zec=4.0,
)
_CEUTA_MELILLA_2024 = ISRegimen(
    nombre="ceuta_melilla",
    tramos_general=[ISTramo(float("inf"), 25.0)],
    tramos_microempresa=[ISTramo(float("inf"), 23.0)],
    tramos_erd=[ISTramo(float("inf"), 25.0)],
    tramos_nueva_creacion=[ISTramo(float("inf"), 15.0)],
    bonificacion_cuota=0.5,  # 50% bonificacion cuota
    tipo_zec=None,
)
_CEUTA_MELILLA_2025 = ISRegimen(
    nombre="ceuta_melilla",
    tramos_general=[ISTramo(float("inf"), 25.0)],
    tramos_microempresa=[ISTramo(50_000, 17.0), ISTramo(float("inf"), 20.0)],
    tramos_erd=[ISTramo(float("inf"), 24.0)],
    tramos_nueva_creacion=[ISTramo(float("inf"), 15.0)],
    bonificacion_cuota=0.5,
    tipo_zec=None,
)


# Mapa por (regimen_nombre, ejercicio) — falla a la version mas cercana <=
SCALES_BY_YEAR: dict[int, dict[str, ISRegimen]] = {
    2024: {
        "comun": _COMUN_2024,
        "foral_alava": _ALAVA_2024,
        "foral_bizkaia": _BIZKAIA_2024,
        "foral_gipuzkoa": _GIPUZKOA_2024,
        "foral_navarra": _NAVARRA_2024,
        "zec_canarias": _CANARIAS_ZEC,
        "ceuta_melilla": _CEUTA_MELILLA_2024,
    },
    2025: {
        "comun": _COMUN_2025,
        "foral_alava": _ALAVA_2024,  # sin cambios reportados
        "foral_bizkaia": _BIZKAIA_2024,  # sin cambios reportados
        "foral_gipuzkoa": _GIPUZKOA_2025,  # NF 1/2025
        "foral_navarra": _NAVARRA_2025,  # LF 26/2016 microempresa 19%
        "zec_canarias": _CANARIAS_ZEC,
        "ceuta_melilla": _CEUTA_MELILLA_2025,
    },
    2026: {
        "comun": _COMUN_2026,
        "foral_alava": _ALAVA_2024,
        "foral_bizkaia": _BIZKAIA_2024,
        "foral_gipuzkoa": _GIPUZKOA_2025,
        "foral_navarra": _NAVARRA_2025,
        "zec_canarias": _CANARIAS_ZEC,
        "ceuta_melilla": _CEUTA_MELILLA_2025,
    },
}

# Default por compatibilidad — 2024 mantiene escalas pre-Ley 7/2024 (default
# retro-compat). Para aplicar Ley 7/2024, callers deben pasar `ejercicio=2025`.
DEFAULT_EJERCICIO = 2024


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _regimen_key(territorio: str, es_zec: bool) -> str:
    """Devuelve la clave de regimen segun territorio."""
    from app.utils.ccaa_constants import normalize_ccaa, FORAL_VASCO, CEUTA_MELILLA as CM_SET

    canon = normalize_ccaa(territorio)
    if es_zec and canon == "Canarias":
        return "zec_canarias"
    if canon in FORAL_VASCO:
        return {"Araba": "foral_alava", "Bizkaia": "foral_bizkaia", "Gipuzkoa": "foral_gipuzkoa"}[
            canon
        ]
    if canon == "Navarra":
        return "foral_navarra"
    if canon in CM_SET:
        return "ceuta_melilla"
    return "comun"


def get_is_regimen(
    territorio: str,
    es_zec: bool = False,
    ejercicio: int = DEFAULT_EJERCICIO,
) -> ISRegimen:
    """Devuelve el regimen IS para un territorio y ejercicio.

    Si el ejercicio no esta en `SCALES_BY_YEAR`, busca el ano <= mas reciente
    (fallback conservador). Si el ano es < 2024, usa 2024.
    """
    key = _regimen_key(territorio, es_zec)
    # Ano exacto?
    if ejercicio in SCALES_BY_YEAR:
        return SCALES_BY_YEAR[ejercicio][key]
    # Fallback: ano disponible mas cercano (<= ejercicio)
    available = sorted(SCALES_BY_YEAR.keys())
    if ejercicio < available[0]:
        return SCALES_BY_YEAR[available[0]][key]
    # Ejercicio futuro no mapeado: usar el ultimo disponible
    candidate = max(y for y in available if y <= ejercicio)
    return SCALES_BY_YEAR[candidate][key]


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


# ---------------------------------------------------------------------------
# Deducciones IS por territorio + ejercicio
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ISDeduccionParams:
    id_pct: float  # I+D porcentaje base (Art. 35.1.b LIS)
    it_pct: float  # IT porcentaje (Art. 35.2 LIS)
    limite_deducciones_pct: float  # limite global sobre cuota integra (Art. 39.1)
    reserva_cap_pct: float  # reserva capitalizacion (Art. 25 LIS)
    reserva_cap_limite_pct: float  # limite reserva capitalizacion sobre BI previa
    donativos_pct: float  # donativos Sociedades (Art. 20 Ley 49/2002)


# --- Comun por ejercicio ---
# 2024 (Art. 25 LIS pre-RDL 4/2024): reserva capitalizacion 10%, limite 10% BI.
#                                     donativos Sociedades 40%.
# Nota: RDL 4/2024 elevo al 15% en algunos casos pero la jurisprudencia AEAT
# mantiene el calculo conservador al 10% para retro-compat con declaraciones
# pre-2025. Para 2025+ usar _DED_COMUN_2025 (Ley 7/2024).
_DED_COMUN_2024 = ISDeduccionParams(
    id_pct=25.0,
    it_pct=12.0,
    limite_deducciones_pct=25.0,
    reserva_cap_pct=10.0,
    reserva_cap_limite_pct=10.0,
    donativos_pct=40.0,
)
# 2025 (Ley 7/2024): reserva capitalizacion 20% base + escala plantilla (23/26.5/30%).
#                    limite 20% BI previa (25% si INCN<1M).
_DED_COMUN_2025 = ISDeduccionParams(
    id_pct=25.0,
    it_pct=12.0,
    limite_deducciones_pct=25.0,
    reserva_cap_pct=20.0,
    reserva_cap_limite_pct=20.0,
    donativos_pct=40.0,
)

# Forales (sin cambios significativos por Ley 7/2024 para deducciones genericas)
_DED_BIZKAIA = ISDeduccionParams(
    id_pct=30.0,
    it_pct=15.0,
    limite_deducciones_pct=35.0,
    reserva_cap_pct=10.0,
    reserva_cap_limite_pct=10.0,
    donativos_pct=40.0,
)
_DED_GIPUZKOA = ISDeduccionParams(
    id_pct=30.0,
    it_pct=15.0,
    limite_deducciones_pct=35.0,
    reserva_cap_pct=10.0,
    reserva_cap_limite_pct=10.0,
    donativos_pct=40.0,
)
_DED_NAVARRA = ISDeduccionParams(
    id_pct=25.0,
    it_pct=12.0,
    limite_deducciones_pct=25.0,
    reserva_cap_pct=10.0,
    reserva_cap_limite_pct=10.0,
    donativos_pct=40.0,
)


def get_is_deduccion_params(
    territorio: str,
    ejercicio: int = DEFAULT_EJERCICIO,
) -> ISDeduccionParams:
    """Devuelve los parametros de deducciones IS para un territorio + ejercicio."""
    from app.utils.ccaa_constants import normalize_ccaa

    canon = normalize_ccaa(territorio)
    if canon == "Bizkaia":
        return _DED_BIZKAIA
    if canon == "Gipuzkoa":
        return _DED_GIPUZKOA
    if canon == "Navarra":
        return _DED_NAVARRA
    # Comun + Ceuta/Melilla + Araba + Canarias siguen tabla comun
    if ejercicio >= 2025:
        return _DED_COMUN_2025
    return _DED_COMUN_2024


# ---------------------------------------------------------------------------
# Helpers Ley 7/2024 — incremento plantilla (reserva capitalizacion)
# ---------------------------------------------------------------------------


def reserva_capitalizacion_pct_2025(incremento_plantilla_pct: float) -> float:
    """Devuelve el % de reserva de capitalizacion para 2025 segun incremento de plantilla.

    Art. 25 LIS modificado por Ley 7/2024:
    - 20%  base
    - 23%  si incremento plantilla media  >=  2% y < 5%
    - 26.5% si  >= 5% y < 10%
    - 30%  si  >= 10%
    """
    if incremento_plantilla_pct >= 10.0:
        return 30.0
    if incremento_plantilla_pct >= 5.0:
        return 26.5
    if incremento_plantilla_pct >= 2.0:
        return 23.0
    return 20.0


# ---------------------------------------------------------------------------
# BIN (Art. 26 LIS) — Tramos por INCN, ejercicio comun
# ---------------------------------------------------------------------------

# Suelo siempre compensable (parrafo 2 Art. 26.1)
BIN_SUELO_EUR: float = 1_000_000.0


def bin_limite_pct(facturacion_anual: float) -> float:
    """Devuelve el % de limite de compensacion BIN segun INCN.

    Art. 26 LIS:
    - INCN < 20M     : 100% (sin limite porcentual; aplica suelo 1M siempre)
    - 20M <= INCN < 60M : 70%
    - INCN >= 60M    : 50%   (el que faltaba en TaxIA)
    """
    if facturacion_anual >= 60_000_000:
        return 50.0
    if facturacion_anual >= 20_000_000:
        return 70.0
    return 100.0


# ---------------------------------------------------------------------------
# Tributacion minima (Art. 30 bis LIS)
# ---------------------------------------------------------------------------


def tributacion_minima_pct(
    es_nueva_creacion: bool = False,
    es_banca_hidrocarburos: bool = False,
) -> float:
    """Cuota liquida minima como % de la BI (Art. 30 bis LIS, RDL 4/2024).

    - 18% para entidades de credito y exploracion/produccion hidrocarburos
    - 10% para entidades nueva creacion
    - 15% en general
    """
    if es_banca_hidrocarburos:
        return 18.0
    if es_nueva_creacion:
        return 10.0
    return 15.0


# ---------------------------------------------------------------------------
# Tributacion minima — umbrales de aplicabilidad (Art. 30 bis LIS)
# ---------------------------------------------------------------------------

# La tributacion minima Art. 30 bis aplica a:
#  (a) Contribuyentes con INCN >= 20.000.000 EUR en los 12 meses anteriores.
#  (b) Contribuyentes en regimen de consolidacion fiscal (cualquier INCN).
TRIBUTACION_MINIMA_INCN_THRESHOLD: float = 20_000_000.0


def aplica_tributacion_minima(
    facturacion_anual: float,
    grupo_consolidado: bool = False,
) -> bool:
    """Devuelve True si aplica el calculo de cuota liquida minima Art. 30 bis."""
    if grupo_consolidado:
        return True
    return facturacion_anual >= TRIBUTACION_MINIMA_INCN_THRESHOLD


# ---------------------------------------------------------------------------
# Reserva de nivelacion (Art. 105 LIS) — solo ERD (INCN < 10M)
# ---------------------------------------------------------------------------

# Empresas de Reducida Dimension (INCN < 10M) pueden minorar BI hasta el 10%
# de la base imponible positiva, con un maximo absoluto de 1.000.000 EUR.
# Importe indisponible 5 anos; revierte si genera BIN posterior.
RESERVA_NIVELACION_PCT: float = 10.0
RESERVA_NIVELACION_MAX_EUR: float = 1_000_000.0
ERD_INCN_THRESHOLD: float = 10_000_000.0


def aplica_reserva_nivelacion(facturacion_anual: float) -> bool:
    """ERD (INCN < 10.000.000 EUR) puede aplicar reserva nivelacion Art. 105."""
    return 0 < facturacion_anual < ERD_INCN_THRESHOLD


# ---------------------------------------------------------------------------
# Cooperativas (Ley 20/1990)
# ---------------------------------------------------------------------------

# Cooperativas fiscalmente protegidas: 20% sobre la BI cooperativa
# (Art. 28 Ley 20/1990).  Cooperativas de credito/seguros: 25%.
COOPERATIVA_TIPO_PROTEGIDA: float = 20.0
COOPERATIVA_TIPO_NO_PROTEGIDA: float = 25.0

# Cooperativas especialmente protegidas: 50% bonificacion sobre cuota integra
# (Art. 34.2 Ley 20/1990).
COOPERATIVA_ESP_PROTEGIDA_BONIFICACION_PCT: float = 0.50


# ---------------------------------------------------------------------------
# I+D — exceso sobre media 2 anos anteriores (Art. 35.1.b LIS)
# ---------------------------------------------------------------------------

# Sobre el gasto I+D que supere la media de los 2 ejercicios anteriores se
# aplica el 42% en lugar del 25% base.
ID_PCT_EXCESO_MEDIA: float = 42.0


# ---------------------------------------------------------------------------
# Pago fraccionado minimo (DA 14a LIS) — INCN >= 10M, modalidad art40_3
# ---------------------------------------------------------------------------

# 23% del resultado contable positivo del periodo (con ajustes positivos).
# 25% para entidades de credito y exploracion/produccion hidrocarburos.
PAGO_FRACC_MINIMO_PCT_GENERAL: float = 23.0
PAGO_FRACC_MINIMO_PCT_BANCA: float = 25.0
PAGO_FRACC_MINIMO_INCN_THRESHOLD: float = 10_000_000.0


# ---------------------------------------------------------------------------
# ZEC Canarias — techo base bonificable por empleos creados (Art. 43 Ley 19/1994)
# ---------------------------------------------------------------------------

# Tipo IS ZEC: 4%.  Solo aplica al tramo de BI no superior al techo.
# El exceso tributa al tipo general (25%).
ZEC_TIPO_IS: float = 4.0
ZEC_TECHO_BASE_PRIMEROS_5_EMPLEOS: float = 1_800_000.0  # primeros 5 empleos
ZEC_TECHO_INCREMENTO_POR_EMPLEO_EXTRA: float = 500_000.0  # cada empleo adicional
ZEC_EMPLEOS_MINIMOS: int = 5
ZEC_EMPLEOS_MAX_COMPUTABLES: int = 50


def zec_techo_base(empleos_creados: int) -> float:
    """Techo de base imponible bonificable al 4% segun empleos ZEC creados.

    Art. 43 Ley 19/1994:
    - 1.800.000 EUR por los primeros 5 empleos creados.
    - +500.000 EUR por cada empleo adicional hasta un maximo de 50.

    Si empleos < 5 → no se cumple requisito ZEC, devuelve 0.
    """
    if empleos_creados < ZEC_EMPLEOS_MINIMOS:
        return 0.0
    empleos_extra = min(empleos_creados, ZEC_EMPLEOS_MAX_COMPUTABLES) - ZEC_EMPLEOS_MINIMOS
    return ZEC_TECHO_BASE_PRIMEROS_5_EMPLEOS + empleos_extra * ZEC_TECHO_INCREMENTO_POR_EMPLEO_EXTRA


# ---------------------------------------------------------------------------
# Deducciones cinematograficas (Art. 36 LIS)
# ---------------------------------------------------------------------------

# Producciones espanolas (Art. 36.1):
#  - 30% sobre el primer millon de base de deduccion
#  - 25% sobre el exceso
#  - Limite 20.000.000 EUR (40.000.000 EUR en CSI o si rodadas en Cataluna
#    con porcentaje de gasto territorial reforzado).
CINE_ESPANOLA_PCT_PRIMER_MILLON: float = 30.0
CINE_ESPANOLA_PCT_RESTO: float = 25.0
CINE_ESPANOLA_BASE_PRIMER_TRAMO: float = 1_000_000.0
CINE_ESPANOLA_LIMITE_GENERAL: float = 20_000_000.0
CINE_ESPANOLA_LIMITE_REFORZADO: float = 40_000_000.0  # CSI / Cataluna

# Producciones extranjeras (Art. 36.2):
#  - 30% sobre el gasto en territorio espanol
#  - Base minima 1.000.000 EUR
#  - Limite 20.000.000 EUR
CINE_EXTRANJERA_PCT: float = 30.0
CINE_EXTRANJERA_BASE_MINIMA: float = 1_000_000.0
CINE_EXTRANJERA_LIMITE: float = 20_000_000.0

# Series TV (Art. 36.1 primera produccion en serie):
CINE_SERIES_TV_PCT: float = 25.0


def calcular_deduccion_cine(
    gasto: float,
    tipo_produccion: str = "espanola",
    csi_o_cataluna: bool = False,
) -> float:
    """Calcula la deduccion por inversion en producciones cinematograficas.

    Args:
        gasto: base de deduccion (gasto admitido).
        tipo_produccion: "espanola" | "extranjera" | "serie".
        csi_o_cataluna: True si aplica techo reforzado 40M (CSI / Cataluna).

    Returns:
        Importe de la deduccion antes de aplicar limite cuota.
    """
    if gasto <= 0:
        return 0.0

    if tipo_produccion == "espanola":
        if gasto <= CINE_ESPANOLA_BASE_PRIMER_TRAMO:
            ded = gasto * CINE_ESPANOLA_PCT_PRIMER_MILLON / 100
        else:
            ded = (
                CINE_ESPANOLA_BASE_PRIMER_TRAMO * CINE_ESPANOLA_PCT_PRIMER_MILLON / 100
                + (gasto - CINE_ESPANOLA_BASE_PRIMER_TRAMO) * CINE_ESPANOLA_PCT_RESTO / 100
            )
        techo = CINE_ESPANOLA_LIMITE_REFORZADO if csi_o_cataluna else CINE_ESPANOLA_LIMITE_GENERAL
        return round(min(ded, techo), 2)

    if tipo_produccion == "extranjera":
        if gasto < CINE_EXTRANJERA_BASE_MINIMA:
            return 0.0
        ded = gasto * CINE_EXTRANJERA_PCT / 100
        return round(min(ded, CINE_EXTRANJERA_LIMITE), 2)

    if tipo_produccion == "serie":
        return round(gasto * CINE_SERIES_TV_PCT / 100, 2)

    return 0.0
