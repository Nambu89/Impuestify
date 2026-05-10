"""
Modelo 450 Calculator — AIEM (Arbitrio sobre Importaciones y Entregas de
Mercancias en las Islas Canarias).

Legal basis (vigente 2025+):
- Decreto Legislativo 1/2025, de 13 de octubre, por el que se aprueba el
  Texto Refundido de la Comunidad Autonoma de Canarias del IGIC y AIEM
  (BOC nº 207 de 2025-10-20, vigor 2025-10-21). Refunde la regulacion AIEM
  previamente dispersa entre Ley 4/2014 y Ley 20/1991.
- Ley 4/2014, de 26 de junio, por la que se modifica la regulacion del AIEM
  (origen de la lista vigente de bienes sometidos al gravamen).
- Decision 377/2014/UE del Consejo (autorizacion europea del regimen).
- Orden anual de la Consejeria de Hacienda de Canarias (modelo 450 vigente).

Marco general:
- AIEM grava la entrega de mercancias en Canarias por su productor y la
  importacion de mercancias en las Islas. NO grava las entregas internas
  posteriores (a diferencia del IGIC, que opera en cada eslabon).
- El sujeto pasivo del Modelo 450 es el PRODUCTOR LOCAL canario incluido
  en la lista de bienes sometidos a AIEM (Anexo IV TR Decreto Legislativo
  1/2025). Los importadores liquidan AIEM en aduana via DUA, NO en el 450.
- Periodicidad: TRIMESTRAL en regimen general; mensual para grandes
  empresas (> 6.010.121,04 EUR volumen ano anterior).
- Plazos T1: 1-20 abril | T2: 1-20 julio | T3: 1-20 octubre | T4: 1-30 enero
  ano siguiente. Coinciden con los del Modelo 420 (IGIC).

Tipos AIEM vigentes 2025+:
- 5 %  → tipo reducido (bienes de menor proteccion industrial)
- 10 % → tipo intermedio (textiles, calzado parcial, productos quimicos
        ligeros, ciertos manufacturados)
- 15 % → tipo general (mayoria de bienes industriales con produccion local
        relevante: muebles, conservas, papel, hormigon, plastico, etc.)
- 25 % → tipo especial (labores del tabaco)

Nota normativa: la lista exacta y la asignacion epigrafe→tipo del Anexo IV
del TR Decreto Legislativo 1/2025 no esta publicada en formato estructurado
en la sede de la ATC al cierre de esta implementacion. Por eso el calculator
acepta `tipo_aiem` MANUAL por linea de bien y, opcionalmente, hace lookup
contra el dict `AIEM_TIPOS_POR_EPIGRAFE` (subset conservador).

Si se pasa un epigrafe IAE conocido en `AIEM_TIPOS_POR_EPIGRAFE` y no se
indica `tipo_aiem`, se aplica el tipo del lookup. Si no esta en el dict y
no se indica `tipo_aiem`, se devuelve un warning en el output del bien
(no se interrumpe el calculo — la responsabilidad final del tipo es del
contribuyente segun ordenanza fiscal y resolucion ATC vigente).

Estructura del Modelo 450 (resumen):
- DEVENGADO (operaciones interiores producidas):
    cuota_AIEM_total = sum(base_imponible_i * tipo_aiem_i for cada bien i)
- AJUSTES: rectificaciones de bases/cuotas, modificaciones por impagos.
- COMPENSACION: cuotas a compensar de periodos anteriores (cuando un
  trimestre arroja resultado negativo, se arrastra al siguiente).
- RESULTADO: cuota_AIEM_total - compensaciones_anteriores +/- ajustes.

NO existe IVA/IGIC soportado deducible en el Modelo 450 — el AIEM funciona
como impuesto monofasico sobre el productor, no es un impuesto en cadena.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.utils.tax_parameter_repository import TaxParameterRepository


# ---------------------------------------------------------------------------
# Constantes — tipos vigentes 2025+ (TR Decreto Legislativo 1/2025)
# ---------------------------------------------------------------------------
TIPO_AIEM_REDUCIDO = 0.05      # 5 %  — bienes industriales menores
TIPO_AIEM_INTERMEDIO = 0.10    # 10 % — textiles, calzado, quimicos ligeros
TIPO_AIEM_GENERAL = 0.15       # 15 % — tipo general (mayoria de bienes)
TIPO_AIEM_ESPECIAL = 0.25      # 25 % — labores del tabaco

ALLOWED_AIEM_RATES = (
    TIPO_AIEM_REDUCIDO,
    TIPO_AIEM_INTERMEDIO,
    TIPO_AIEM_GENERAL,
    TIPO_AIEM_ESPECIAL,
)


# ---------------------------------------------------------------------------
# Lookup conservador epigrafe IAE → tipo AIEM
# ---------------------------------------------------------------------------
# IMPORTANTE: la lista oficial completa (Anexo IV TR Decreto Legislativo
# 1/2025) no esta publicada en formato estructurado en la sede ATC. Este
# dict cubre las categorias mas habituales basandose en la doctrina previa
# (Ley 4/2014) y se debe ampliar cuando la ATC publique el anexo
# estructurado. Si un epigrafe NO esta aqui, el calculator devuelve warning
# y exige `tipo_aiem` manual.
#
# Formato: clave = primeros 3-4 digitos del epigrafe IAE; valor = tipo AIEM.
AIEM_TIPOS_POR_EPIGRAFE: Dict[str, float] = {
    # Tabaco — tipo especial 25 %
    "1500": TIPO_AIEM_ESPECIAL,  # Industria del tabaco
    "1501": TIPO_AIEM_ESPECIAL,
    "1502": TIPO_AIEM_ESPECIAL,
    # Bebidas alcoholicas / refrescos — tipo general
    "4258": TIPO_AIEM_GENERAL,   # Cerveza
    "4252": TIPO_AIEM_GENERAL,   # Vinos
    "4259": TIPO_AIEM_GENERAL,   # Bebidas no alcoholicas
    # Conservas, alimentacion industrial — tipo general 15 %
    "411": TIPO_AIEM_GENERAL,    # Industrias lacteas
    "413": TIPO_AIEM_GENERAL,    # Sacrificio ganado, conservas carnicas
    "414": TIPO_AIEM_GENERAL,    # Industria lactea (sub)
    "415": TIPO_AIEM_GENERAL,    # Conservas vegetales
    "416": TIPO_AIEM_GENERAL,    # Pescado y conservas pescado
    # Textil, confeccion, calzado — tipo intermedio 10 %
    "433": TIPO_AIEM_INTERMEDIO,
    "439": TIPO_AIEM_INTERMEDIO,
    "451": TIPO_AIEM_INTERMEDIO,
    "453": TIPO_AIEM_INTERMEDIO,
    "454": TIPO_AIEM_INTERMEDIO,
    # Madera, muebles — tipo general
    "461": TIPO_AIEM_GENERAL,
    "468": TIPO_AIEM_GENERAL,
    # Papel, artes graficas — tipo general
    "471": TIPO_AIEM_GENERAL,
    "474": TIPO_AIEM_GENERAL,
    # Quimica industrial — tipo intermedio (varios) / general
    "251": TIPO_AIEM_INTERMEDIO,
    "253": TIPO_AIEM_INTERMEDIO,
    # Plastico, caucho — tipo general
    "481": TIPO_AIEM_GENERAL,
    "482": TIPO_AIEM_GENERAL,
    # Hormigon, cemento, materiales construccion — tipo general
    "243": TIPO_AIEM_GENERAL,
    "244": TIPO_AIEM_GENERAL,
    "245": TIPO_AIEM_GENERAL,
    "247": TIPO_AIEM_GENERAL,
    # Pinturas, barnices — tipo general
    "255": TIPO_AIEM_GENERAL,
    # Minimos / bienes industriales menores — tipo reducido 5 %
    "493": TIPO_AIEM_REDUCIDO,
    "499": TIPO_AIEM_REDUCIDO,
}


# Plazos Modelo 450 — coinciden con Modelo 420 (Orden anual ATC):
PLAZOS_MODELO_450: Dict[int, Dict[str, Any]] = {
    1: {"trimestre": "T1", "mes_fin": 4, "dia_fin": 20, "anio_siguiente": False},
    2: {"trimestre": "T2", "mes_fin": 7, "dia_fin": 20, "anio_siguiente": False},
    3: {"trimestre": "T3", "mes_fin": 10, "dia_fin": 20, "anio_siguiente": False},
    4: {"trimestre": "T4", "mes_fin": 1, "dia_fin": 30, "anio_siguiente": True},
}


# Umbral grandes empresas (mensual en lugar de trimestral)
UMBRAL_MENSUAL_EUR: float = 6_010_121.04


def _resolve_year(year: Optional[int]) -> int:
    """Devuelve el year a aplicar; default = 2025 (esquema vigente)."""
    if year is None:
        return 2025
    return int(year)


def lookup_tipo_aiem(epigrafe_iae: str) -> Optional[float]:
    """
    Devuelve el tipo AIEM aplicable a un epigrafe IAE, o None si no esta
    en el lookup. Hace match por prefijo: epigrafe '4151' matchea '415'.
    """
    if not epigrafe_iae:
        return None
    epi = str(epigrafe_iae).strip()
    # Match exacto primero
    if epi in AIEM_TIPOS_POR_EPIGRAFE:
        return AIEM_TIPOS_POR_EPIGRAFE[epi]
    # Luego match por prefijo (4 digitos, 3 digitos)
    for length in (4, 3):
        prefix = epi[:length]
        if prefix in AIEM_TIPOS_POR_EPIGRAFE:
            return AIEM_TIPOS_POR_EPIGRAFE[prefix]
    return None


class Modelo450Calculator:
    """
    Calculadora autoliquidacion AIEM (Modelo 450) para productores canarios.

    AIEM es un impuesto MONOFASICO sobre el productor (no en cadena como
    IGIC/IVA), por eso NO hay deducciones de cuotas soportadas — solo
    devengado, ajustes y compensaciones de periodos anteriores.
    """

    def __init__(self, repo: Optional[TaxParameterRepository] = None) -> None:
        self._repo = repo  # Reservado para futuras consultas a parametros.

    async def calculate(
        self,
        *,
        bienes_producidos: Optional[List[Dict[str, Any]]] = None,
        cuotas_compensar_anteriores: float = 0.0,
        rectificacion_bases: float = 0.0,
        rectificacion_cuotas: float = 0.0,
        regularizacion_anual: float = 0.0,
        resultado_anterior_complementaria: float = 0.0,
        quarter: int = 1,
        year: Optional[int] = None,
        periodicidad: str = "trimestral",  # 'trimestral' | 'mensual'
        mes: Optional[int] = None,         # solo si periodicidad = 'mensual'
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Calcula la autoliquidacion AIEM (Modelo 450).

        Args:
            bienes_producidos: lista de operaciones, cada una:
                {
                    "epigrafe_iae": "4151" (opcional),
                    "descripcion": "Conservas de pescado" (opcional),
                    "base_imponible": 12000.0 (obligatorio),
                    "tipo_aiem": 0.15 (opcional — si falta y hay epigrafe,
                                         se intenta lookup; si no, warning),
                }
            cuotas_compensar_anteriores: cuotas negativas arrastradas (>= 0).
            rectificacion_bases / rectificacion_cuotas: ajustes de periodos
                anteriores (pueden ser negativos).
            regularizacion_anual: solo aplica en T4.
            resultado_anterior_complementaria: si es complementaria.
            quarter: 1-4. Ignorado si periodicidad = 'mensual'.
            mes: 1-12. Solo si periodicidad = 'mensual'.
            year: ejercicio fiscal (default 2025).
            periodicidad: 'trimestral' (default) o 'mensual' (grandes empresas).

        Returns:
            Dict con desglose por bien, total devengado, resultado liquidacion,
            warnings (epigrafes sin tipo conocido), plazos.
        """
        # -------------------------------------------------------------------
        # 0. Validaciones
        # -------------------------------------------------------------------
        if periodicidad not in ("trimestral", "mensual"):
            raise ValueError(
                f"periodicidad debe ser 'trimestral' o 'mensual', recibido: "
                f"{periodicidad!r}"
            )
        if periodicidad == "trimestral":
            if quarter not in (1, 2, 3, 4):
                raise ValueError(
                    f"quarter debe estar entre 1 y 4, recibido: {quarter}"
                )
        else:
            if mes is None or mes not in range(1, 13):
                raise ValueError(
                    "Para periodicidad mensual, 'mes' debe estar entre 1 y 12. "
                    f"Recibido: {mes}"
                )

        year_resolved = _resolve_year(year)
        if year_resolved < 2010 or year_resolved > 2099:
            raise ValueError(f"year fuera de rango razonable: {year_resolved}")

        if cuotas_compensar_anteriores < 0:
            raise ValueError(
                "cuotas_compensar_anteriores debe ser >= 0 (las cuotas "
                "negativas se compensan en POSITIVO en periodos siguientes)."
            )

        bienes = bienes_producidos or []

        # -------------------------------------------------------------------
        # 1. DEVENGADO — iterar sobre cada bien
        # -------------------------------------------------------------------
        desglose_bienes: List[Dict[str, Any]] = []
        warnings: List[str] = []
        total_base = 0.0
        total_cuota = 0.0

        for idx, bien in enumerate(bienes, start=1):
            if not isinstance(bien, dict):
                raise ValueError(
                    f"bienes_producidos[{idx - 1}] debe ser un dict, recibido: "
                    f"{type(bien).__name__}"
                )
            base = float(bien.get("base_imponible", 0.0))
            if base < 0:
                raise ValueError(
                    f"bienes_producidos[{idx - 1}].base_imponible no puede "
                    f"ser negativa: {base}"
                )

            epigrafe = str(bien.get("epigrafe_iae", "") or "").strip()
            descripcion = str(bien.get("descripcion", "") or "").strip()
            tipo_manual = bien.get("tipo_aiem")

            tipo_aplicado: Optional[float] = None
            origen_tipo = "manual"

            if tipo_manual is not None:
                tipo_aplicado = float(tipo_manual)
                origen_tipo = "manual"
            elif epigrafe:
                tipo_lookup = lookup_tipo_aiem(epigrafe)
                if tipo_lookup is not None:
                    tipo_aplicado = tipo_lookup
                    origen_tipo = "lookup"

            if tipo_aplicado is None:
                # No hay tipo manual ni lookup posible — registramos warning
                # y NO sumamos al total (cuota = 0 para este bien).
                warnings.append(
                    f"Bien #{idx} ({descripcion or epigrafe or 'sin id'}): "
                    "no se ha indicado tipo_aiem y el epigrafe no esta en el "
                    "lookup conservador. Indica tipo_aiem manualmente "
                    "consultando el Anexo IV TR Decreto Legislativo 1/2025."
                )
                desglose_bienes.append({
                    "indice": idx,
                    "epigrafe_iae": epigrafe or None,
                    "descripcion": descripcion or None,
                    "base_imponible": round(base, 2),
                    "tipo_aiem": None,
                    "cuota_aiem": 0.0,
                    "origen_tipo": "desconocido",
                    "warning": True,
                })
                continue

            # Clamp tipo a [0, 1] por defensa (evita inputs maliciosos)
            tipo_clamped = max(0.0, min(tipo_aplicado, 1.0))
            if tipo_clamped not in ALLOWED_AIEM_RATES:
                warnings.append(
                    f"Bien #{idx}: tipo {tipo_clamped:.2%} no esta en la "
                    f"lista oficial AIEM ({', '.join(f'{r:.0%}' for r in ALLOWED_AIEM_RATES)}). "
                    "Verifica el Anexo IV TR Decreto Legislativo 1/2025."
                )

            cuota = round(base * tipo_clamped, 2)
            total_base += base
            total_cuota += cuota

            desglose_bienes.append({
                "indice": idx,
                "epigrafe_iae": epigrafe or None,
                "descripcion": descripcion or None,
                "base_imponible": round(base, 2),
                "tipo_aiem": round(tipo_clamped, 4),
                "cuota_aiem": cuota,
                "origen_tipo": origen_tipo,
                "warning": False,
            })

        total_base = round(total_base, 2)
        total_cuota = round(total_cuota, 2)

        # -------------------------------------------------------------------
        # 2. AJUSTES y RESULTADO
        # -------------------------------------------------------------------
        rectificacion_bases = round(float(rectificacion_bases), 2)
        rectificacion_cuotas = round(float(rectificacion_cuotas), 2)

        cuota_devengada_ajustada = round(
            total_cuota + rectificacion_cuotas, 2
        )

        cuotas_compensar_aplicadas = max(
            0.0, round(float(cuotas_compensar_anteriores), 2)
        )

        # Regularizacion anual exclusiva del 4T (igual que Modelo 420).
        if periodicidad == "trimestral":
            regularizacion_anual_aplicada = (
                round(float(regularizacion_anual), 2) if quarter == 4 else 0.0
            )
        else:
            # En periodicidad mensual la regularizacion anual no aplica
            # (se integra via 425-equivalente o resumen anual).
            regularizacion_anual_aplicada = 0.0

        resultado_liquidacion = round(
            cuota_devengada_ajustada
            - cuotas_compensar_aplicadas
            + regularizacion_anual_aplicada,
            2,
        )

        cuota_diferencial_complementaria = round(
            resultado_liquidacion - float(resultado_anterior_complementaria),
            2,
        )

        # -------------------------------------------------------------------
        # 3. Plazos
        # -------------------------------------------------------------------
        if periodicidad == "trimestral":
            plazo_meta = PLAZOS_MODELO_450[quarter]
            plazo_str = (
                f"del 1 al {plazo_meta['dia_fin']} de "
                f"{['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'][plazo_meta['mes_fin']-1]}"
            )
            if plazo_meta["anio_siguiente"]:
                plazo_str += f" de {year_resolved + 1}"
            periodo_label = plazo_meta["trimestre"]
        else:
            # Mensual: del 1 al 20 del mes siguiente
            mes_siguiente = mes + 1 if mes < 12 else 1
            anio_siguiente = mes == 12
            mes_siguiente_label = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'][mes_siguiente - 1]
            plazo_str = f"del 1 al 20 de {mes_siguiente_label}"
            if anio_siguiente:
                plazo_str += f" de {year_resolved + 1}"
            periodo_label = f"M{mes:02d}"

        return {
            "modelo": "450",
            "territorio": "Canarias",
            "organismo": "ATC",
            "periodicidad": periodicidad,
            "quarter": quarter if periodicidad == "trimestral" else None,
            "mes": mes if periodicidad == "mensual" else None,
            "year": year_resolved,
            "periodo_label": periodo_label,
            "plazo_presentacion": plazo_str,
            "desglose_bienes": desglose_bienes,
            "total_base_imponible": total_base,
            "total_cuota_devengada": total_cuota,
            "rectificacion_bases": rectificacion_bases,
            "rectificacion_cuotas": rectificacion_cuotas,
            "cuota_devengada_ajustada": cuota_devengada_ajustada,
            "cuotas_compensar_anteriores": cuotas_compensar_aplicadas,
            "regularizacion_anual": regularizacion_anual_aplicada,
            "resultado_liquidacion": resultado_liquidacion,
            "resultado_anterior_complementaria": round(
                float(resultado_anterior_complementaria), 2
            ),
            "cuota_diferencial_complementaria": cuota_diferencial_complementaria,
            "warnings": warnings,
            "aiem_rates": {
                "tipo_reducido": TIPO_AIEM_REDUCIDO,
                "tipo_intermedio": TIPO_AIEM_INTERMEDIO,
                "tipo_general": TIPO_AIEM_GENERAL,
                "tipo_especial": TIPO_AIEM_ESPECIAL,
            },
        }
