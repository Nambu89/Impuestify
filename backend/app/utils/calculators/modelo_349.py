"""
Modelo 349 — Declaracion recapitulativa de operaciones intracomunitarias.

Normativa:
- Orden EHA/769/2010 (modelo vigente, modificada por HFP/417/2017 y HAC/174/2020).
- Reglamento IVA RD 1624/1992 Arts. 78-81.
- Ley IVA 37/1992 Art. 25 (exencion EIB), Art. 69.uno.1 (B2B servicios).
- Directiva 2006/112/CE Arts. 262-271.

Claves de operacion (Art. 4 Orden EHA/769/2010):
    E - Entrega intracomunitaria de bienes.
    A - Adquisicion intracomunitaria de bienes.
    T - Operacion triangular (operador intermediario).
    S - Prestacion intracomunitaria de servicios (Art. 69.uno.1 LIVA).
    I - Adquisicion intracomunitaria de servicios.
    M - Entregas posteriores a importacion (Art. 27.12 LIVA).
    H - Sujeto pasivo representante en entregas posteriores a importacion.
    R - Transferencias en regimen de consignacion / call-off stock (Art. 9 bis LIVA).
    D - Devoluciones de mercancias en regimen de consignacion.
    C - Sustituciones de adquirente en regimen de consignacion.
    N - NIF-IVA inexistente o erroneo (rectificaciones por defecto formal).

Periodicidad (Art. 10 Orden EHA/769/2010):
    Mensual: si entregas (E + S + T + M + H) + adquisiciones (A + I) > 50.000 EUR
        en el trimestre actual o en alguno de los 4 anteriores.
    Trimestral: por defecto, cuando no aplica mensual.
    Anual: si volumen total anual <= 35.000 EUR Y entregas (E + S) <= 15.000 EUR/ano.

Plazos:
    Mensual: dias 1-20 del mes siguiente.
        Excepciones: julio se presenta 1-20 agosto (sin extension de verano);
        diciembre se presenta 1-30 enero del ano siguiente.
    Trimestral: 1T abril 20, 2T julio 20, 3T octubre 20, 4T enero 30.
    Anual: 1-30 enero del ano siguiente.

VIES (Censo de operadores intracomunitarios):
    Endpoint REST oficial: https://ec.europa.eu/taxation_customs/vies/rest-api/check-vat-number
    Validacion obligatoria del NIF-IVA del operador UE en el momento del devengo
    para aplicar la exencion del Art. 25 LIVA. STJUE C-146/05 (Collee) admite
    sustancia > forma, pero AEAT exige la consulta como diligencia debida.

Cuadre 303 <-> 349 (causa nº1 de requerimientos AEAT):
    303 casilla 60 (informativa, EIB exentas) deberia coincidir con suma 349
    de claves E + T + M + H del mismo periodo.
    303 casilla 38 (base AIB inversion) + casilla 36 (base AIB corrientes)
    deberian coincidir con suma 349 de clave A.
    Diferencias > 0,5 EUR generan paralela.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Constantes normativas
# --------------------------------------------------------------------------- #

# Claves validas (Art. 4 Orden EHA/769/2010)
CLAVES_VALIDAS: Tuple[str, ...] = (
    "E",
    "A",
    "T",
    "S",
    "I",
    "M",
    "H",
    "R",
    "D",
    "C",
    "N",
)

# Subconjuntos para calculos de umbral y cuadre 303
ENTREGAS_BIENES_CLAVES: Tuple[str, ...] = ("E", "T", "M", "H")
ADQUISICIONES_BIENES_CLAVES: Tuple[str, ...] = ("A",)
ENTREGAS_SERVICIOS_CLAVES: Tuple[str, ...] = ("S",)
ADQUISICIONES_SERVICIOS_CLAVES: Tuple[str, ...] = ("I",)
CONSIGNACION_CLAVES: Tuple[str, ...] = ("R", "D", "C")
RECTIFICACION_CLAVES: Tuple[str, ...] = ("N",)

# Umbrales (Art. 10 Orden EHA/769/2010)
UMBRAL_MENSUAL_TRIMESTRE: float = 50_000.0
UMBRAL_ANUAL_TOTAL: float = 35_000.0
UMBRAL_ANUAL_ENTREGAS: float = 15_000.0

# Tolerancia para cuadre 303 <-> 349 (en euros)
CUADRE_TOLERANCIA_EUR: float = 0.5

# Codigos ISO de los Estados miembro de la UE (al 2026, Brexit ya aplicado)
EU_COUNTRY_CODES: Tuple[str, ...] = (
    "AT",
    "BE",
    "BG",
    "CY",
    "CZ",
    "DE",
    "DK",
    "EE",
    "EL",
    "ES",
    "FI",
    "FR",
    "HR",
    "HU",
    "IE",
    "IT",
    "LT",
    "LU",
    "LV",
    "MT",
    "NL",
    "PL",
    "PT",
    "RO",
    "SE",
    "SI",
    "SK",
    # XI = Irlanda del Norte (acuerdo bienes post-Brexit, no servicios)
    "XI",
)

# Formato del NIF-IVA por pais (longitud y caracteres permitidos despues del
# prefijo ISO). Datos extraidos de la Comision Europea (TAXUD), simplificados.
# Notar que la validacion final de checksum la hace VIES.
_VAT_FORMATS: Dict[str, re.Pattern[str]] = {
    "AT": re.compile(r"^U\d{8}$"),
    "BE": re.compile(r"^[01]\d{9}$"),
    "BG": re.compile(r"^\d{9,10}$"),
    "CY": re.compile(r"^\d{8}[A-Z]$"),
    "CZ": re.compile(r"^\d{8,10}$"),
    "DE": re.compile(r"^\d{9}$"),
    "DK": re.compile(r"^\d{8}$"),
    "EE": re.compile(r"^\d{9}$"),
    "EL": re.compile(r"^\d{9}$"),
    "ES": re.compile(r"^[A-Z0-9]\d{7}[A-Z0-9]$"),
    "FI": re.compile(r"^\d{8}$"),
    "FR": re.compile(r"^[A-Z0-9]{2}\d{9}$"),
    "HR": re.compile(r"^\d{11}$"),
    "HU": re.compile(r"^\d{8}$"),
    "IE": re.compile(r"^\d[A-Z0-9\+\*]\d{5}[A-Z]{1,2}$"),
    "IT": re.compile(r"^\d{11}$"),
    "LT": re.compile(r"^(\d{9}|\d{12})$"),
    "LU": re.compile(r"^\d{8}$"),
    "LV": re.compile(r"^\d{11}$"),
    "MT": re.compile(r"^\d{8}$"),
    "NL": re.compile(r"^\d{9}B\d{2}$"),
    "PL": re.compile(r"^\d{10}$"),
    "PT": re.compile(r"^\d{9}$"),
    "RO": re.compile(r"^\d{2,10}$"),
    "SE": re.compile(r"^\d{12}$"),
    "SI": re.compile(r"^\d{8}$"),
    "SK": re.compile(r"^\d{10}$"),
    "XI": re.compile(r"^(\d{9}|\d{12}|GD\d{3}|HA\d{3})$"),
}


# --------------------------------------------------------------------------- #
# Modelos de datos
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Operacion349:
    """Operacion individual del Modelo 349.

    importe es siempre en EUR. Para la clave N (rectificacion) admite valor
    negativo. Para el resto, se espera valor positivo (la rectificacion al alza
    se modela como N positivo, la baja como N negativo).
    """

    nif_operador: str
    nombre: str
    clave: str
    importe: float
    pais_codigo: Optional[str] = None  # Auto-derivado del prefijo NIF-IVA si no se pasa
    periodo_rectificado: Optional[str] = None  # Solo para clave N o C
    base_anterior_declarada: Optional[float] = None  # Solo para clave N

    def __post_init__(self) -> None:  # pragma: no cover - dataclass init
        # Validaciones minimas (no bloquean la creacion del objeto)
        if self.clave not in CLAVES_VALIDAS:
            logger.warning(
                "Operacion349 con clave invalida '%s' (operador=%s)",
                self.clave,
                self.nif_operador,
            )


@dataclass
class CuadreResult:
    """Resultado del cuadre 303 <-> 349 para un periodo."""

    diff_entregas_bienes: float = 0.0  # 303 c.60 vs sum(E+T+M+H)
    diff_adquisiciones_bienes: float = 0.0  # 303 c.36+38 vs sum(A)
    diff_servicios_prestados: float = 0.0  # info, no hay casilla 303 explicita
    diff_servicios_adquiridos: float = 0.0  # info, no hay casilla 303 explicita
    warnings: List[str] = field(default_factory=list)
    cuadre_ok: bool = True


# --------------------------------------------------------------------------- #
# Calculator
# --------------------------------------------------------------------------- #


class Modelo349Calculator:
    """Calculadora del Modelo 349 (no genera fichero, solo computa amounts).

    Patron:
    - Stateless en lo logico, pero mantiene un cache LRU per-instance del
      validador VIES para no machacar el servicio europeo.
    - VIES validation es opcional: se debe llamar explicitamente desde el
      caller con `await calc.validate_nif_iva_vies(nif)`. La calculadora
      principal no la dispara para mantener determinismo en tests.
    """

    # Tamano maximo del cache VIES per-instance (LRU manual).
    _VIES_CACHE_MAX: int = 2048
    _VIES_TIMEOUT_SECONDS: float = 5.0
    _VIES_ENDPOINT: str = "https://ec.europa.eu/taxation_customs/vies/rest-api/check-vat-number"

    def __init__(self, repo: Any = None) -> None:
        # `repo` se acepta por consistencia con el resto de calculadoras pero
        # no se usa (el 349 no depende de TaxParameterRepository).
        self._repo = repo
        # Cache: nif_iva_normalizado -> {"valid": bool, "nombre": str, "direccion": str, "fetched_at": float}
        self._vies_cache: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------ #
    # Validacion de claves de operacion
    # ------------------------------------------------------------------ #

    @staticmethod
    def validate_clave(clave: str) -> bool:
        """Devuelve True si la clave esta en CLAVES_VALIDAS."""
        return isinstance(clave, str) and clave.upper() in CLAVES_VALIDAS

    # ------------------------------------------------------------------ #
    # Validacion del NIF-IVA — formato (sin VIES)
    # ------------------------------------------------------------------ #

    @staticmethod
    def normalize_nif_iva(nif: str) -> str:
        """Quita espacios, guiones y puntos; pasa a mayusculas."""
        if not nif:
            return ""
        return re.sub(r"[\s\-\.]", "", str(nif)).upper()

    @classmethod
    def validate_nif_iva_format(cls, nif: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Valida el formato (longitud, caracteres) del NIF-IVA UE.

        Devuelve `(es_valido, codigo_pais, motivo)`. `codigo_pais` es ISO de 2
        letras (ES, DE, FR, ...). `motivo` es None si valido o un string si no.

        NO consulta VIES — solo validacion sintactica per pais.
        """
        normalized = cls.normalize_nif_iva(nif)
        if len(normalized) < 4:
            return False, None, "NIF-IVA demasiado corto"
        country = normalized[:2]
        body = normalized[2:]
        if country not in EU_COUNTRY_CODES:
            return False, country, f"Codigo de pais '{country}' no es UE"
        pattern = _VAT_FORMATS.get(country)
        if pattern is None:
            # Pais UE conocido pero sin patron registrado — admitimos longitud minima
            if len(body) < 7:
                return False, country, "Cuerpo del NIF-IVA demasiado corto"
            return True, country, None
        if not pattern.match(body):
            return False, country, f"Formato invalido para {country}"
        return True, country, None

    # ------------------------------------------------------------------ #
    # Validacion VIES (REST, sincrono via httpx)
    # ------------------------------------------------------------------ #

    async def validate_nif_iva_vies(
        self,
        nif: str,
        *,
        fail_open: bool = True,
        client: Any = None,
    ) -> Dict[str, Any]:
        """Consulta el servicio VIES (REST) de la Comision Europea.

        Estrategia:
        1. Validacion sintactica primero (rapida, gratis).
        2. Si format OK -> mira cache LRU.
        3. Si miss -> llama al endpoint con timeout 5s.
        4. Si fail_open=True (default) y VIES no responde, devuelve
           `{"valid": True, "vies_unavailable": True, "warning": "..."}`.

        Devuelve siempre dict con keys: valid (bool), nif_iva, country,
        nombre, direccion, source, vies_unavailable (bool), warning, error.
        """
        normalized = self.normalize_nif_iva(nif)
        ok_format, country, motivo = self.validate_nif_iva_format(normalized)

        result: Dict[str, Any] = {
            "valid": False,
            "nif_iva": normalized,
            "country": country,
            "nombre": None,
            "direccion": None,
            "source": "format",
            "vies_unavailable": False,
            "warning": None,
            "error": None,
        }

        if not ok_format:
            result["error"] = motivo or "Formato NIF-IVA invalido"
            return result

        # Cache hit
        if normalized in self._vies_cache:
            cached = self._vies_cache[normalized]
            result.update(cached)
            result["source"] = "cache"
            return result

        # Llamada al endpoint
        try:
            import httpx  # type: ignore

            # Permitir inyeccion de cliente para tests
            owns_client = False
            if client is None:
                client = httpx.AsyncClient(timeout=self._VIES_TIMEOUT_SECONDS)
                owns_client = True

            try:
                response = await client.post(
                    self._VIES_ENDPOINT,
                    json={"countryCode": country, "vatNumber": normalized[2:]},
                    headers={"Content-Type": "application/json"},
                )
            finally:
                if owns_client:
                    await client.aclose()

            if response.status_code != 200:
                if fail_open:
                    result["valid"] = True
                    result["vies_unavailable"] = True
                    result["warning"] = (
                        f"VIES devolvio HTTP {response.status_code}; "
                        "no se pudo validar online. Validacion sintactica OK."
                    )
                    result["source"] = "fail_open"
                    return result
                result["error"] = f"VIES HTTP {response.status_code}"
                return result

            data = response.json()
            valid = bool(data.get("valid", data.get("isValid", False)))
            nombre = data.get("name") or data.get("traderName")
            direccion = data.get("address") or data.get("traderAddress")

            cached_entry = {
                "valid": valid,
                "nombre": nombre,
                "direccion": direccion,
            }
            # LRU naive: si llenamos el cache, drop the oldest insert
            if len(self._vies_cache) >= self._VIES_CACHE_MAX:
                oldest = next(iter(self._vies_cache))
                self._vies_cache.pop(oldest, None)
            self._vies_cache[normalized] = cached_entry

            result.update(cached_entry)
            result["source"] = "vies"
            return result

        except ImportError:
            # httpx deberia estar instalado, pero degradar gracefully
            if fail_open:
                result["valid"] = True
                result["vies_unavailable"] = True
                result["warning"] = (
                    "httpx no disponible; validacion VIES omitida. "
                    "Solo se valido formato sintactico."
                )
                result["source"] = "fail_open"
                return result
            result["error"] = "httpx no disponible"
            return result

        except Exception as exc:  # noqa: BLE001 - VIES puede fallar de mil formas
            logger.warning("VIES check fallo para %s: %s", normalized, exc)
            if fail_open:
                result["valid"] = True
                result["vies_unavailable"] = True
                result["warning"] = (
                    f"VIES no disponible ({exc.__class__.__name__}); "
                    "se acepta por fail-open. Reintentar antes de presentar."
                )
                result["source"] = "fail_open"
                return result
            result["error"] = str(exc)
            return result

    # ------------------------------------------------------------------ #
    # Periodicidad (Art. 10 Orden EHA/769/2010)
    # ------------------------------------------------------------------ #

    @classmethod
    def detect_periodicidad(
        cls,
        *,
        operaciones_actual: Iterable[Operacion349],
        importes_4_trimestres_anteriores: Optional[List[float]] = None,
        operaciones_anuales: Optional[Iterable[Operacion349]] = None,
        forzar_anual: bool = False,
    ) -> Dict[str, Any]:
        """Determina la periodicidad del 349 segun umbrales legales.

        Args:
            operaciones_actual: operaciones del trimestre/mes en curso.
            importes_4_trimestres_anteriores: lista (max 4) con la suma
                EIB+EIS+AIB+AIS de cada trimestre anterior. Si alguna supera
                50.000 EUR -> mensual.
            operaciones_anuales: si se pasa, sirve para evaluar elegibilidad
                anual (todas las operaciones del ano natural en curso).
            forzar_anual: bypass de la deteccion para usuarios que ya hayan
                optado por la modalidad anual.

        Returns:
            dict con keys: periodicidad ('mensual'|'trimestral'|'anual'),
            motivo (str), umbral_aplicado (float), volumen_actual (float),
            volumen_anterior_max (float), volumen_anual (float|None).
        """
        if forzar_anual:
            return {
                "periodicidad": "anual",
                "motivo": "Solicitud expresa del declarante (modalidad anual).",
                "umbral_aplicado": UMBRAL_ANUAL_TOTAL,
                "volumen_actual": 0.0,
                "volumen_anterior_max": 0.0,
                "volumen_anual": None,
            }

        ops_actual = list(operaciones_actual)
        volumen_actual = cls._volumen_relevante(ops_actual)

        anteriores = list(importes_4_trimestres_anteriores or [])
        volumen_anterior_max = max(anteriores) if anteriores else 0.0

        # Mensual si el trimestre actual o cualquiera de los 4 anteriores supera 50.000 EUR
        if (
            volumen_actual > UMBRAL_MENSUAL_TRIMESTRE
            or volumen_anterior_max > UMBRAL_MENSUAL_TRIMESTRE
        ):
            motivo_origen = (
                "trimestre actual"
                if volumen_actual > UMBRAL_MENSUAL_TRIMESTRE
                else "alguno de los 4 trimestres anteriores"
            )
            return {
                "periodicidad": "mensual",
                "motivo": (
                    f"Volumen EIB+PIS+AIB+AIS supera 50.000 EUR en {motivo_origen} "
                    "(Art. 10.1 Orden EHA/769/2010)."
                ),
                "umbral_aplicado": UMBRAL_MENSUAL_TRIMESTRE,
                "volumen_actual": round(volumen_actual, 2),
                "volumen_anterior_max": round(volumen_anterior_max, 2),
                "volumen_anual": None,
            }

        # Anual si volumen anual <= 35.000 EUR Y entregas (E+S) <= 15.000 EUR
        if operaciones_anuales is not None:
            ops_anuales = list(operaciones_anuales)
            volumen_anual_total = cls._volumen_relevante(ops_anuales)
            volumen_entregas_anual = cls._volumen_por_claves(
                ops_anuales,
                ENTREGAS_BIENES_CLAVES + ENTREGAS_SERVICIOS_CLAVES,
            )
            if (
                volumen_anual_total <= UMBRAL_ANUAL_TOTAL
                and volumen_entregas_anual <= UMBRAL_ANUAL_ENTREGAS
            ):
                return {
                    "periodicidad": "anual",
                    "motivo": (
                        "Volumen anual <= 35.000 EUR y entregas intracomunitarias "
                        "<= 15.000 EUR (Art. 10.3 Orden EHA/769/2010)."
                    ),
                    "umbral_aplicado": UMBRAL_ANUAL_TOTAL,
                    "volumen_actual": round(volumen_actual, 2),
                    "volumen_anterior_max": round(volumen_anterior_max, 2),
                    "volumen_anual": round(volumen_anual_total, 2),
                }

        return {
            "periodicidad": "trimestral",
            "motivo": "Por defecto (Art. 10.2 Orden EHA/769/2010).",
            "umbral_aplicado": UMBRAL_MENSUAL_TRIMESTRE,
            "volumen_actual": round(volumen_actual, 2),
            "volumen_anterior_max": round(volumen_anterior_max, 2),
            "volumen_anual": None,
        }

    # ------------------------------------------------------------------ #
    # Plazos de presentacion
    # ------------------------------------------------------------------ #

    @staticmethod
    def plazo_presentacion(
        periodicidad: str,
        periodo: str,
        year: int,
    ) -> str:
        """Devuelve el plazo de presentacion en formato humano.

        Args:
            periodicidad: 'mensual' | 'trimestral' | 'anual'.
            periodo: '01'..'12' para mensual; '1T'..'4T' para trimestral;
                'anual' para anual.
            year: ano del periodo declarado.
        """
        if periodicidad == "mensual":
            mes = periodo.zfill(2)
            try:
                mes_int = int(mes)
            except ValueError:
                return f"Dias 1-20 del mes siguiente a {periodo}."
            if mes_int == 12:
                return f"1 al 30 de enero de {year + 1} (mes 12 {year})."
            if mes_int == 7:
                return f"1 al 20 de agosto de {year} (mes 7 {year})."
            siguiente = mes_int + 1
            return f"1 al 20 del mes {siguiente:02d}/{year} (mes {mes_int:02d} {year})."

        if periodicidad == "trimestral":
            mapa = {
                "1T": f"1 al 20 de abril de {year}",
                "2T": f"1 al 20 de julio de {year}",
                "3T": f"1 al 20 de octubre de {year}",
                "4T": f"1 al 30 de enero de {year + 1}",
            }
            return mapa.get(periodo.upper(), f"Dias 1-20 mes siguiente al {periodo}.")

        if periodicidad == "anual":
            return f"1 al 30 de enero de {year + 1} (anual {year})."

        return "Consultar calendario AEAT."

    # ------------------------------------------------------------------ #
    # Resumen y construccion
    # ------------------------------------------------------------------ #

    @classmethod
    def build_resumen(
        cls,
        operaciones: Iterable[Operacion349],
    ) -> Dict[str, Any]:
        """Agrupa por clave y devuelve totales + numero de operadores.

        Returns:
            {
              "por_clave": { "E": {"importe": ..., "n_operaciones": N, "n_operadores": M}, ... },
              "totales": {
                "entregas_bienes": float, "adquisiciones_bienes": float,
                "servicios_prestados": float, "servicios_adquiridos": float,
                "consignacion": float, "rectificaciones": float,
                "volumen_relevante": float, "total_general": float,
              },
              "operadores_unicos": int,
              "operaciones_count": int,
              "errores": [...],
            }
        """
        ops = list(operaciones)
        por_clave: Dict[str, Dict[str, Any]] = {
            clave: {"importe": 0.0, "n_operaciones": 0, "operadores": set()}
            for clave in CLAVES_VALIDAS
        }
        errores: List[str] = []
        operadores_global: set = set()

        for op in ops:
            clave = (op.clave or "").upper()
            if clave not in CLAVES_VALIDAS:
                errores.append(f"Clave invalida '{op.clave}' en operador {op.nif_operador}")
                continue
            por_clave[clave]["importe"] += float(op.importe or 0.0)
            por_clave[clave]["n_operaciones"] += 1
            nif_norm = cls.normalize_nif_iva(op.nif_operador)
            if nif_norm:
                por_clave[clave]["operadores"].add(nif_norm)
                operadores_global.add(nif_norm)

        # Convertir set a count + redondeos
        por_clave_serializable: Dict[str, Dict[str, Any]] = {}
        for clave, data in por_clave.items():
            n_operadores = len(data["operadores"])
            por_clave_serializable[clave] = {
                "importe": round(data["importe"], 2),
                "n_operaciones": data["n_operaciones"],
                "n_operadores": n_operadores,
            }

        totales = {
            "entregas_bienes": round(
                sum(por_clave_serializable[c]["importe"] for c in ENTREGAS_BIENES_CLAVES),
                2,
            ),
            "adquisiciones_bienes": round(
                sum(por_clave_serializable[c]["importe"] for c in ADQUISICIONES_BIENES_CLAVES),
                2,
            ),
            "servicios_prestados": round(
                sum(por_clave_serializable[c]["importe"] for c in ENTREGAS_SERVICIOS_CLAVES),
                2,
            ),
            "servicios_adquiridos": round(
                sum(por_clave_serializable[c]["importe"] for c in ADQUISICIONES_SERVICIOS_CLAVES),
                2,
            ),
            "consignacion": round(
                sum(por_clave_serializable[c]["importe"] for c in CONSIGNACION_CLAVES),
                2,
            ),
            "rectificaciones": round(
                sum(por_clave_serializable[c]["importe"] for c in RECTIFICACION_CLAVES),
                2,
            ),
        }
        totales["volumen_relevante"] = round(
            totales["entregas_bienes"]
            + totales["adquisiciones_bienes"]
            + totales["servicios_prestados"]
            + totales["servicios_adquiridos"],
            2,
        )
        totales["total_general"] = round(
            sum(por_clave_serializable[c]["importe"] for c in CLAVES_VALIDAS),
            2,
        )

        return {
            "por_clave": por_clave_serializable,
            "totales": totales,
            "operadores_unicos": len(operadores_global),
            "operaciones_count": len(ops),
            "errores": errores,
        }

    # ------------------------------------------------------------------ #
    # Cuadre 303 <-> 349
    # ------------------------------------------------------------------ #

    @classmethod
    def cuadrar_con_303(
        cls,
        *,
        operaciones_349: Iterable[Operacion349],
        casillas_303: Optional[Dict[str, float]] = None,
        tolerancia: float = CUADRE_TOLERANCIA_EUR,
    ) -> CuadreResult:
        """Cruza el 349 con las casillas relevantes del 303 del mismo periodo.

        Mapping (Modelo 303 vigente 2026):
            casilla 60 (informativa) = base entregas intracomunitarias exentas.
            casilla 36 + casilla 38 = base adquisiciones intracomunitarias
                (corrientes + bienes inversion).

        Args:
            operaciones_349: operaciones del periodo a cuadrar.
            casillas_303: dict con keys opcionales:
                'casilla_60' (EIB exentas), 'casilla_36' (AIB corrientes),
                'casilla_38' (AIB inversion).
            tolerancia: diferencia maxima admisible en EUR (default 0,5).

        Returns:
            CuadreResult con diffs y warnings cuando exceden la tolerancia.
        """
        casillas = casillas_303 or {}
        ops = list(operaciones_349)

        # Suma 349 entregas bienes (E + T + M + H)
        suma_eib_349 = cls._volumen_por_claves(ops, ENTREGAS_BIENES_CLAVES)
        # Suma 349 adquisiciones bienes (A)
        suma_aib_349 = cls._volumen_por_claves(ops, ADQUISICIONES_BIENES_CLAVES)
        # Suma 349 servicios (S, I) — informativas, sin casilla 303 directa
        suma_eis_349 = cls._volumen_por_claves(ops, ENTREGAS_SERVICIOS_CLAVES)
        suma_ais_349 = cls._volumen_por_claves(ops, ADQUISICIONES_SERVICIOS_CLAVES)

        c60 = float(casillas.get("casilla_60", 0.0) or 0.0)
        c36 = float(casillas.get("casilla_36", 0.0) or 0.0)
        c38 = float(casillas.get("casilla_38", 0.0) or 0.0)
        suma_aib_303 = round(c36 + c38, 2)

        diff_entregas = round(c60 - suma_eib_349, 2)
        diff_adquisiciones = round(suma_aib_303 - suma_aib_349, 2)

        warnings_list: List[str] = []
        cuadre_ok = True

        if abs(diff_entregas) > tolerancia:
            cuadre_ok = False
            warnings_list.append(
                f"Cuadre EIB: 303 casilla 60 = {c60:,.2f} EUR vs. 349 (E+T+M+H) "
                f"= {suma_eib_349:,.2f} EUR. Diferencia {diff_entregas:+.2f} EUR "
                "(causa habitual de paralela AEAT)."
            )

        if abs(diff_adquisiciones) > tolerancia:
            cuadre_ok = False
            warnings_list.append(
                f"Cuadre AIB: 303 casillas 36+38 = {suma_aib_303:,.2f} EUR vs. "
                f"349 (clave A) = {suma_aib_349:,.2f} EUR. Diferencia "
                f"{diff_adquisiciones:+.2f} EUR."
            )

        return CuadreResult(
            diff_entregas_bienes=diff_entregas,
            diff_adquisiciones_bienes=diff_adquisiciones,
            diff_servicios_prestados=round(suma_eis_349, 2),  # informativa
            diff_servicios_adquiridos=round(suma_ais_349, 2),
            warnings=warnings_list,
            cuadre_ok=cuadre_ok,
        )

    # ------------------------------------------------------------------ #
    # Helpers internos
    # ------------------------------------------------------------------ #

    @classmethod
    def _volumen_relevante(cls, ops: Iterable[Operacion349]) -> float:
        """Volumen para el umbral de 50.000 EUR: EIB+EIS+AIB+AIS.

        Las operaciones de consignacion (R/D/C) y rectificaciones (N) NO
        cuentan para el umbral de periodicidad.
        """
        relevantes = (
            ENTREGAS_BIENES_CLAVES
            + ENTREGAS_SERVICIOS_CLAVES
            + ADQUISICIONES_BIENES_CLAVES
            + ADQUISICIONES_SERVICIOS_CLAVES
        )
        return cls._volumen_por_claves(ops, relevantes)

    @staticmethod
    def _volumen_por_claves(
        ops: Iterable[Operacion349],
        claves: Iterable[str],
    ) -> float:
        claves_set = {c.upper() for c in claves}
        total = 0.0
        for op in ops:
            if (op.clave or "").upper() in claves_set:
                total += float(op.importe or 0.0)
        return round(total, 2)
