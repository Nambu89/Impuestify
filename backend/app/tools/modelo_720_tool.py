"""
Tool para evaluar la obligacion de presentar el Modelo 720 (Declaracion Informativa
de Bienes y Derechos en el Extranjero).

Normativa aplicable:
- Ley 7/2012, de 29 de octubre (introduccion del Modelo 720)
- Real Decreto 1065/2007, Arts. 42 bis, 42 ter y 54 bis
- Sentencia TJUE C-788/19 de 27/01/2022 (anulacion sanciones desproporcionadas)
- Ley 5/2022 de 9 de marzo (reforma regimen sancionador — regimen general LGT)

Umbrales:
- Obligacion si a 31/dic se supera 50.000 EUR en CUALQUIERA de las 3 categorias:
  1. Cuentas bancarias en entidades financieras del extranjero
  2. Valores, derechos, seguros y rentas en entidades del extranjero
  3. Bienes inmuebles y derechos sobre inmuebles en el extranjero
- Incremento >20.000 EUR respecto la ultima declaracion presentada obliga a
  presentar de nuevo (aunque no se supere el umbral de 50K si ya se presento antes).

Plazo: 1 de enero a 31 de marzo del ejercicio siguiente.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

UMBRAL_OBLIGACION_EUR = 50_000
UMBRAL_INCREMENTO_EUR = 20_000

CATEGORIAS = {
    "cuentas": "Cuentas bancarias en el extranjero",
    "valores": "Valores, derechos, seguros y rentas en el extranjero",
    "inmuebles": "Bienes inmuebles en el extranjero",
}

# ---------------------------------------------------------------------------
# Subtipos por categoria (claves DR720 AEAT)
# ---------------------------------------------------------------------------
#
# Diseno de Registro Modelo 720 — claves declarativas por categoria. Estas
# claves no afectan al calculo del umbral (50K agregados por categoria) pero
# son obligatorias en el fichero AEAT para identificar el subtipo del bien.
#
# Referencias normativas:
#   - Cuentas:   RD 1065/2007 Art. 42 bis.1
#   - Valores:   RD 1065/2007 Art. 42 ter.1
#   - Inmuebles: RD 1065/2007 Art. 54 bis.1, .5

SUBTIPOS_CUENTAS = {
    "A": "Cuenta corriente",
    "B": "Cuenta de ahorro",
    "C": "Imposiciones a plazo",
    "D": "Cuenta de credito",
    "E": "Otras cuentas",
}

SUBTIPOS_VALORES = {
    "A": "Valores representativos del capital social o fondos propios (acciones, participaciones)",
    "B": "Valores representativos de la cesion a terceros de capitales propios (bonos, obligaciones)",
    "C": "Valores aportados a instrumentos juridicos (trusts, fideicomisos, masas patrimoniales)",
    "D": "Acciones y participaciones en Instituciones de Inversion Colectiva (fondos)",
    "E": "Seguros de vida o invalidez con tomador residente",
    "F": "Rentas vitalicias o temporales con beneficiario residente",
}

SUBTIPOS_INMUEBLES = {
    "A": "Titularidad plena del inmueble",
    "B": "Nuda propiedad",
    "C": "Usufructo (vitalicio o temporal)",
    "D": "Multipropiedad, aprovechamiento por turnos u otros derechos reales",
}

SUBTIPOS_POR_CATEGORIA = {
    "cuentas": SUBTIPOS_CUENTAS,
    "valores": SUBTIPOS_VALORES,
    "inmuebles": SUBTIPOS_INMUEBLES,
}

# ---------------------------------------------------------------------------
# Tool definition (OpenAI function calling)
# ---------------------------------------------------------------------------

MODELO_720_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "check_modelo_720",
        "description": (
            "Evalua si el usuario esta obligado a presentar el Modelo 720 "
            "(Declaracion Informativa de Bienes y Derechos en el Extranjero). "
            "Usa esta funcion cuando el usuario pregunte sobre el Modelo 720, "
            "bienes en el extranjero, cuentas bancarias fuera de Espana, "
            "inmuebles en otro pais, valores o seguros en entidades extranjeras, "
            "o si debe declarar activos en el exterior. "
            "Evalua por cada categoria (cuentas, valores, inmuebles) si se supera "
            "el umbral de 50.000 EUR y si hay incremento >20.000 EUR respecto "
            "a la ultima declaracion presentada. "
            "Tambien evalua la obligacion de declarar el cese de titularidad "
            "(cierre de cuenta, transmision de valores, venta de inmueble) cuando "
            "esos bienes fueron declarados en un 720 anterior (RD 1065/2007 "
            "Arts. 42 bis.5, 42 ter.5 y 54 bis.7). "
            "El parametro opcional 'subtipos' permite desglosar el valor por "
            "clave declarativa AEAT (A-F) dentro de cada categoria. "
            "IMPORTANTE: este tool evalua SOLO la obligacion de presentar el "
            "modelo. Para preparar el fichero AEAT (identificacion bien a bien "
            "con BIC/IBAN, ISIN, direccion catastral y % titularidad) se "
            "requiere flujo guiado adicional en Sede Electronica."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "cuentas_extranjero": {
                    "type": "number",
                    "description": (
                        "Saldo total en cuentas bancarias en el extranjero a 31 de "
                        "diciembre del ejercicio, en euros."
                    ),
                },
                "valores_extranjero": {
                    "type": "number",
                    "description": (
                        "Valor de mercado de valores, derechos, seguros y rentas "
                        "depositados en entidades extranjeras a 31 de diciembre, en euros."
                    ),
                },
                "inmuebles_extranjero": {
                    "type": "number",
                    "description": (
                        "Valor de adquisicion de bienes inmuebles situados en el "
                        "extranjero, en euros."
                    ),
                },
                "ultimo_720_presentado": {
                    "type": "integer",
                    "description": (
                        "Ano del ultimo Modelo 720 presentado (ej: 2023). "
                        "Null si nunca se ha presentado."
                    ),
                },
                "saldos_ultimo_720_cuentas": {
                    "type": "number",
                    "description": (
                        "Saldo de cuentas declarado en el ultimo 720 presentado, en euros. "
                        "Solo relevante si se presento un 720 anterior."
                    ),
                },
                "saldos_ultimo_720_valores": {
                    "type": "number",
                    "description": (
                        "Valor de valores/seguros declarado en el ultimo 720 presentado, en euros."
                    ),
                },
                "saldos_ultimo_720_inmuebles": {
                    "type": "number",
                    "description": (
                        "Valor de inmuebles declarado en el ultimo 720 presentado, en euros."
                    ),
                },
                "ceses_titularidad": {
                    "type": "array",
                    "description": (
                        "Lista de ceses de titularidad sobre bienes declarados en 720 "
                        "anteriores. Cada elemento describe un bien que ha dejado de "
                        "cumplir las condiciones que motivaron su inclusion en un 720 "
                        "previo (cierre de cuenta, transmision de valores, venta de "
                        "inmueble, perdida de titularidad). Si el bien NO fue "
                        "declarado en un 720 anterior, el cese NO genera obligacion. "
                        "RD 1065/2007 Arts. 42 bis.5, 42 ter.5, 54 bis.7."
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "categoria": {
                                "type": "string",
                                "enum": ["cuentas", "valores", "inmuebles"],
                                "description": "Categoria del bien cesado.",
                            },
                            "subtipo": {
                                "type": "string",
                                "description": (
                                    "Clave DR720 del subtipo (A, B, C, D, E, F). "
                                    "Cuentas: A-E. Valores: A-F. Inmuebles: A-D."
                                ),
                            },
                            "descripcion": {
                                "type": "string",
                                "description": (
                                    "Texto libre identificando el bien (ej: 'Cuenta "
                                    "corriente Andorra ES12...', 'Acciones Apple', "
                                    "'Inmueble Lisboa')."
                                ),
                            },
                            "valor_ultima_declaracion": {
                                "type": "number",
                                "description": (
                                    "Valor con que se declaro el bien en el ultimo "
                                    "720 presentado, en euros."
                                ),
                            },
                            "fecha_cese": {
                                "type": "string",
                                "description": (
                                    "Fecha del cese (cierre, venta, transmision) en "
                                    "formato YYYY-MM-DD."
                                ),
                            },
                            "motivo": {
                                "type": "string",
                                "description": (
                                    "Motivo del cese: 'cierre_cuenta', 'venta_valores', "
                                    "'venta_inmueble', 'transmision', 'cancelacion', 'otro'."
                                ),
                            },
                        },
                        "required": ["categoria"],
                    },
                },
                "subtipos": {
                    "type": "object",
                    "description": (
                        "Desglose opcional del valor de cada categoria por clave "
                        "DR720 (A-F). Estructura: {categoria: {clave: importe}}. "
                        "Ejemplo: {'cuentas': {'A': 30000, 'B': 25000}, 'valores': "
                        "{'A': 40000, 'D': 15000}}. La suma por categoria debe "
                        "coincidir con el valor agregado de esa categoria. Las "
                        "claves declarativas no modifican el calculo del umbral "
                        "(que se evalua sobre el agregado), pero se devuelven en "
                        "la respuesta para que el preparador del modelo pueda "
                        "identificar el subtipo de cada bien."
                    ),
                    "properties": {
                        "cuentas": {
                            "type": "object",
                            "description": "Subtipos cuentas (A-E). Ej: {'A': 30000, 'B': 25000}",
                            "additionalProperties": {"type": "number"},
                        },
                        "valores": {
                            "type": "object",
                            "description": "Subtipos valores (A-F). Ej: {'A': 40000, 'D': 15000}",
                            "additionalProperties": {"type": "number"},
                        },
                        "inmuebles": {
                            "type": "object",
                            "description": "Subtipos inmuebles (A-D). Ej: {'A': 200000}",
                            "additionalProperties": {"type": "number"},
                        },
                    },
                },
            },
            "required": [],
        },
    },
}


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------


async def check_modelo_720_tool(
    cuentas_extranjero: float = 0,
    valores_extranjero: float = 0,
    inmuebles_extranjero: float = 0,
    ultimo_720_presentado: Optional[int] = None,
    saldos_ultimo_720_cuentas: Optional[float] = None,
    saldos_ultimo_720_valores: Optional[float] = None,
    saldos_ultimo_720_inmuebles: Optional[float] = None,
    ceses_titularidad: Optional[List[Dict[str, Any]]] = None,
    subtipos: Optional[Dict[str, Dict[str, float]]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Evalua la obligacion de presentar el Modelo 720.

    Analiza tres categorias independientes:
    1. Cuentas bancarias en el extranjero (umbral 50.000 EUR)
    2. Valores, derechos, seguros y rentas en entidades extranjeras (umbral 50.000 EUR)
    3. Bienes inmuebles en el extranjero (umbral 50.000 EUR)

    Si ya se presento un 720 anterior, se evalua ademas si hay incremento >20.000 EUR
    en alguna categoria respecto a los saldos declarados.

    Cese de titularidad (RD 1065/2007 Arts. 42 bis.5, 42 ter.5, 54 bis.7): si un
    bien declarado en un 720 anterior deja de cumplir las condiciones que motivaron
    su inclusion (cierre de cuenta, venta de valores, transmision de inmueble),
    existe obligacion de declarar el cese en el ejercicio en que ocurre, aunque la
    posicion a 31/dic sea 0. Si no se presento 720 previo por esa categoria, no
    hay obligacion derivada del cese.

    Subtipos opcionales: el desglose por clave DR720 (A-F) no afecta al calculo
    del umbral pero se devuelve en la respuesta para identificar el subtipo de
    cada bien (clave declarativa AEAT).

    Post-reforma 2022 (Ley 5/2022): las sanciones se rigen por el regimen general
    de la LGT (no las sanciones desproporcionadas que anulo el TJUE en C-788/19).

    Returns:
        Dict con obligado_720 (bool), categorias_obligadas, plazo, recomendaciones,
        ceses_obligan_declarar, subtipos_validados y formatted_response para el usuario.
    """
    try:
        current_year = datetime.now().year
        ejercicio = current_year - 1  # Se declara el ejercicio anterior

        saldos_actuales = {
            "cuentas": float(cuentas_extranjero or 0),
            "valores": float(valores_extranjero or 0),
            "inmuebles": float(inmuebles_extranjero or 0),
        }

        saldos_previos: Optional[Dict[str, float]] = None
        if ultimo_720_presentado is not None:
            saldos_previos = {
                "cuentas": float(saldos_ultimo_720_cuentas or 0),
                "valores": float(saldos_ultimo_720_valores or 0),
                "inmuebles": float(saldos_ultimo_720_inmuebles or 0),
            }

        categorias_obligadas: List[str] = []
        categorias_por_incremento: List[str] = []
        detalles: List[Dict[str, Any]] = []

        for cat_key, cat_label in CATEGORIAS.items():
            valor = saldos_actuales[cat_key]
            obligado_umbral = valor > UMBRAL_OBLIGACION_EUR
            obligado_incremento = False
            incremento = 0.0

            if saldos_previos is not None and not obligado_umbral:
                incremento = valor - saldos_previos[cat_key]
                if incremento > UMBRAL_INCREMENTO_EUR:
                    obligado_incremento = True

            if obligado_umbral:
                categorias_obligadas.append(cat_key)
            elif obligado_incremento:
                categorias_por_incremento.append(cat_key)

            detalles.append({
                "categoria": cat_key,
                "descripcion": cat_label,
                "valor_actual": valor,
                "supera_umbral_50k": obligado_umbral,
                "incremento_vs_ultimo_720": round(incremento, 2) if saldos_previos else None,
                "supera_incremento_20k": obligado_incremento,
                "obligado": obligado_umbral or obligado_incremento,
            })

        # Cese de titularidad (Art. 42 bis.5, 42 ter.5, 54 bis.7 RGAT).
        # Solo genera obligacion si existe 720 previo Y (mejor esfuerzo) si la
        # categoria del bien cesado tenia saldo previo declarado.
        ceses_validados, ceses_que_obligan, categorias_por_cese = _evaluar_ceses_titularidad(
            ceses_titularidad, ultimo_720_presentado, saldos_previos
        )

        # Anadir categorias por cese a la lista de obligadas si no estaban ya.
        for cat in categorias_por_cese:
            if cat not in categorias_obligadas and cat not in categorias_por_incremento:
                categorias_por_incremento.append(cat)  # cese se reporta como obligacion no por umbral

        # Validar subtipos opcionales contra agregados por categoria.
        subtipos_validados, subtipos_warnings = _validar_subtipos(subtipos, saldos_actuales)

        todas_obligadas = list(dict.fromkeys(
            categorias_obligadas + categorias_por_incremento
        ))
        obligado = len(todas_obligadas) > 0 or len(ceses_que_obligan) > 0

        plazo = f"Del 1 de enero al 31 de marzo de {ejercicio + 1}"

        recomendaciones = _generar_recomendaciones_720(
            obligado, categorias_obligadas, categorias_por_incremento,
            saldos_actuales, ejercicio,
            ceses_que_obligan=ceses_que_obligan,
            subtipos_warnings=subtipos_warnings,
        )

        formatted = _format_720_response(
            obligado, detalles, plazo, recomendaciones, ejercicio,
            ultimo_720_presentado,
            ceses_que_obligan=ceses_que_obligan,
            subtipos_validados=subtipos_validados,
        )

        return {
            "success": True,
            "modelo": "720",
            "ejercicio": ejercicio,
            "obligado_720": obligado,
            "categorias_obligadas": todas_obligadas,
            "categorias_por_umbral": categorias_obligadas,
            "categorias_por_incremento": categorias_por_incremento,
            "plazo": plazo,
            "detalles": detalles,
            "ceses_titularidad": ceses_validados,
            "ceses_obligan_declarar": ceses_que_obligan,
            "categorias_por_cese": categorias_por_cese,
            "subtipos": subtipos_validados,
            "subtipos_warnings": subtipos_warnings,
            "recomendaciones": recomendaciones,
            "formatted_response": formatted,
        }

    except Exception as exc:
        logger.error("check_modelo_720 error: %s", exc, exc_info=True)
        return {
            "success": False,
            "error": str(exc),
            "formatted_response": (
                f"Error al evaluar la obligacion del Modelo 720: {exc}. "
                "Por favor, revisa los datos introducidos."
            ),
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _evaluar_ceses_titularidad(
    ceses: Optional[List[Dict[str, Any]]],
    ultimo_720_presentado: Optional[int],
    saldos_previos: Optional[Dict[str, float]],
) -> tuple:
    """
    Evalua los ceses de titularidad declarados por el usuario.

    RD 1065/2007 Arts. 42 bis.5, 42 ter.5 y 54 bis.7: la obligacion de declarar
    el cese (cierre de cuenta, transmision de valores, venta de inmueble)
    aplica unicamente cuando el bien fue declarado en un Modelo 720 anterior.
    Si no hubo 720 previo por esa categoria, el cese no genera obligacion.

    Returns:
        Tuple (ceses_validados, ceses_que_obligan, categorias_por_cese):
        - ceses_validados: lista normalizada de los ceses recibidos.
        - ceses_que_obligan: subconjunto que efectivamente obliga a declarar.
        - categorias_por_cese: lista de categorias afectadas por cese obligatorio.
    """
    ceses_validados: List[Dict[str, Any]] = []
    ceses_que_obligan: List[Dict[str, Any]] = []
    categorias_por_cese: List[str] = []

    if not ceses:
        return ceses_validados, ceses_que_obligan, categorias_por_cese

    for raw in ceses:
        if not isinstance(raw, dict):
            continue

        categoria = (raw.get("categoria") or "").strip().lower()
        if categoria not in CATEGORIAS:
            continue

        subtipo_raw = raw.get("subtipo")
        subtipo = subtipo_raw.strip().upper() if isinstance(subtipo_raw, str) else None
        subtipo_valido = (
            subtipo is not None
            and subtipo in SUBTIPOS_POR_CATEGORIA[categoria]
        )

        valor_previo = raw.get("valor_ultima_declaracion")
        try:
            valor_previo_float = float(valor_previo) if valor_previo is not None else None
        except (TypeError, ValueError):
            valor_previo_float = None

        cese_norm: Dict[str, Any] = {
            "categoria": categoria,
            "categoria_descripcion": CATEGORIAS[categoria],
            "subtipo": subtipo if subtipo_valido else None,
            "subtipo_descripcion": (
                SUBTIPOS_POR_CATEGORIA[categoria][subtipo] if subtipo_valido else None
            ),
            "descripcion": (raw.get("descripcion") or "").strip() or None,
            "valor_ultima_declaracion": valor_previo_float,
            "fecha_cese": (raw.get("fecha_cese") or "").strip() or None,
            "motivo": (raw.get("motivo") or "").strip().lower() or None,
        }

        # Decidir si el cese obliga a declarar.
        # Mejor esfuerzo: requiere 720 previo Y (valor_ultima_declaracion>0
        # o saldo_previo>0 en esa categoria).
        obliga = False
        razon_no_obliga: Optional[str] = None
        if ultimo_720_presentado is None:
            razon_no_obliga = (
                "No se presento Modelo 720 anterior, por lo que el cese no "
                "genera obligacion de declarar (RD 1065/2007)."
            )
        else:
            previo_categoria = (
                saldos_previos.get(categoria, 0.0) if saldos_previos else 0.0
            )
            if (
                (valor_previo_float is not None and valor_previo_float > 0)
                or previo_categoria > 0
            ):
                obliga = True
            else:
                razon_no_obliga = (
                    "El bien cesado no figura con valor en el ultimo 720 "
                    "presentado para esta categoria."
                )

        cese_norm["obliga_declarar"] = obliga
        if razon_no_obliga:
            cese_norm["motivo_no_obliga"] = razon_no_obliga

        ceses_validados.append(cese_norm)

        if obliga:
            ceses_que_obligan.append(cese_norm)
            if categoria not in categorias_por_cese:
                categorias_por_cese.append(categoria)

    return ceses_validados, ceses_que_obligan, categorias_por_cese


def _validar_subtipos(
    subtipos: Optional[Dict[str, Dict[str, float]]],
    saldos_actuales: Dict[str, float],
) -> tuple:
    """
    Valida el desglose por subtipo (clave DR720) frente al agregado de la categoria.

    Devuelve la estructura normalizada y warnings cuando la suma por categoria
    no coincide con el valor agregado o cuando se usa una clave fuera del
    diseno de registro (DR720) de esa categoria.
    """
    validados: Dict[str, Dict[str, Dict[str, Any]]] = {}
    warnings: List[str] = []

    if not subtipos or not isinstance(subtipos, dict):
        return validados, warnings

    for categoria_raw, claves in subtipos.items():
        categoria = (categoria_raw or "").strip().lower()
        if categoria not in CATEGORIAS:
            warnings.append(f"Categoria '{categoria_raw}' desconocida en subtipos.")
            continue
        if not isinstance(claves, dict):
            warnings.append(
                f"Desglose de subtipos para '{categoria}' debe ser un diccionario."
            )
            continue

        catalogo = SUBTIPOS_POR_CATEGORIA[categoria]
        cat_validada: Dict[str, Dict[str, Any]] = {}
        suma = 0.0
        for clave_raw, importe_raw in claves.items():
            clave = (clave_raw or "").strip().upper()
            try:
                importe = float(importe_raw)
            except (TypeError, ValueError):
                warnings.append(
                    f"Importe invalido en subtipo {categoria}/{clave_raw}."
                )
                continue
            if clave not in catalogo:
                warnings.append(
                    f"Clave '{clave_raw}' fuera de DR720 para {categoria}. "
                    f"Validas: {sorted(catalogo.keys())}."
                )
                continue
            cat_validada[clave] = {
                "clave": clave,
                "descripcion": catalogo[clave],
                "valor": round(importe, 2),
            }
            suma += importe

        validados[categoria] = cat_validada

        agregado = saldos_actuales.get(categoria, 0.0)
        if cat_validada and abs(suma - agregado) > 0.5:
            warnings.append(
                f"La suma de subtipos en {categoria} ({suma:,.2f} EUR) no "
                f"coincide con el valor agregado ({agregado:,.2f} EUR). "
                "Revisa el desglose."
            )

    return validados, warnings


def _generar_recomendaciones_720(
    obligado: bool,
    por_umbral: List[str],
    por_incremento: List[str],
    saldos: Dict[str, float],
    ejercicio: int,
    ceses_que_obligan: Optional[List[Dict[str, Any]]] = None,
    subtipos_warnings: Optional[List[str]] = None,
) -> List[str]:
    """Genera recomendaciones personalizadas."""
    recs: List[str] = []
    ceses_que_obligan = ceses_que_obligan or []
    subtipos_warnings = subtipos_warnings or []

    if not obligado:
        recs.append(
            f"No estas obligado a presentar el Modelo 720 del ejercicio {ejercicio} "
            "con los datos facilitados."
        )
        # Avisar si esta cerca del umbral
        for cat_key, cat_label in CATEGORIAS.items():
            if saldos[cat_key] > UMBRAL_OBLIGACION_EUR * 0.8:
                recs.append(
                    f"Tu saldo en {cat_label.lower()} ({saldos[cat_key]:,.2f} EUR) "
                    f"esta cerca del umbral de {UMBRAL_OBLIGACION_EUR:,.0f} EUR. "
                    "Vigila la evolucion a cierre del ejercicio."
                )
        for w in subtipos_warnings:
            recs.append(f"Aviso subtipos: {w}")
        return recs

    recs.append(
        f"Estas obligado a presentar el Modelo 720 del ejercicio {ejercicio}."
    )

    if por_umbral:
        nombres = [CATEGORIAS[c] for c in por_umbral]
        recs.append(
            f"Superas el umbral de {UMBRAL_OBLIGACION_EUR:,.0f} EUR en: "
            + ", ".join(nombres) + "."
        )

    if por_incremento:
        nombres = [CATEGORIAS[c] for c in por_incremento]
        recs.append(
            f"Hay incremento superior a {UMBRAL_INCREMENTO_EUR:,.0f} EUR respecto "
            f"al ultimo Modelo 720 presentado en: " + ", ".join(nombres) + "."
        )

    if ceses_que_obligan:
        descripciones: List[str] = []
        for c in ceses_que_obligan:
            base = c["categoria_descripcion"]
            if c.get("descripcion"):
                base += f" — {c['descripcion']}"
            if c.get("subtipo"):
                base += f" (clave {c['subtipo']})"
            descripciones.append(base)
        recs.append(
            "Debes declarar el cese de titularidad de los siguientes bienes "
            "incluidos en un Modelo 720 anterior (RD 1065/2007 Arts. 42 bis.5, "
            "42 ter.5 y 54 bis.7), aunque su valor a 31/dic sea cero: "
            + "; ".join(descripciones) + "."
        )

    recs.append(
        f"Plazo de presentacion: del 1 de enero al 31 de marzo de {ejercicio + 1}."
    )
    recs.append(
        "Tras la sentencia TJUE C-788/19 (27/01/2022) y la Ley 5/2022, ya NO se "
        "aplican: (a) la sancion fija de 5.000 EUR por dato omitido (minimo "
        "10.000 EUR), (b) la multa proporcional del 150% sobre la cuota IRPF/IS "
        "asociada a ganancia patrimonial no justificada, ni (c) la "
        "imprescriptibilidad de dichas ganancias. Aplican las sanciones "
        "generales del Art. 198 LGT."
    )
    recs.append(
        "TaxIA evalua la obligacion; la presentacion telematica del Modelo 720 "
        "(con identificacion bien a bien — BIC/IBAN, ISIN, direccion catastral, "
        "% titularidad y clave declarativa A-F) debe completarse en Sede "
        "Electronica AEAT con certificado digital o Cl@ve PIN."
    )
    for w in subtipos_warnings:
        recs.append(f"Aviso subtipos: {w}")

    return recs


def _format_720_response(
    obligado: bool,
    detalles: List[Dict],
    plazo: str,
    recomendaciones: List[str],
    ejercicio: int,
    ultimo_presentado: Optional[int],
    ceses_que_obligan: Optional[List[Dict[str, Any]]] = None,
    subtipos_validados: Optional[Dict[str, Dict[str, Dict[str, Any]]]] = None,
) -> str:
    """Formatea la respuesta del Modelo 720 para el usuario."""
    ceses_que_obligan = ceses_que_obligan or []
    subtipos_validados = subtipos_validados or {}

    lines: List[str] = []
    lines.append(f"Modelo 720 — Bienes y Derechos en el Extranjero (Ejercicio {ejercicio})")
    lines.append("")

    if obligado:
        lines.append("RESULTADO: Obligado a presentar el Modelo 720.")
    else:
        lines.append("RESULTADO: No obligado a presentar el Modelo 720.")
    lines.append("")

    lines.append("Detalle por categorias:")
    for d in detalles:
        estado = "OBLIGADO" if d["obligado"] else "No obligado"
        lines.append(f"  {d['descripcion']}: {d['valor_actual']:,.2f} EUR — {estado}")
        if d["supera_umbral_50k"]:
            lines.append(f"    Supera umbral de 50.000 EUR")
        if d["supera_incremento_20k"]:
            lines.append(f"    Incremento >{UMBRAL_INCREMENTO_EUR:,.0f} EUR vs ultimo 720")

        cat = d["categoria"]
        if cat in subtipos_validados and subtipos_validados[cat]:
            for clave, info in sorted(subtipos_validados[cat].items()):
                lines.append(
                    f"    Clave {clave} ({info['descripcion']}): "
                    f"{info['valor']:,.2f} EUR"
                )

    if ceses_que_obligan:
        lines.append("")
        lines.append("Ceses de titularidad que obligan a declarar:")
        for c in ceses_que_obligan:
            etiqueta = c["categoria_descripcion"]
            if c.get("subtipo"):
                etiqueta += f" — clave {c['subtipo']} ({c['subtipo_descripcion']})"
            if c.get("descripcion"):
                etiqueta += f" — {c['descripcion']}"
            extras: List[str] = []
            if c.get("motivo"):
                extras.append(f"motivo: {c['motivo']}")
            if c.get("fecha_cese"):
                extras.append(f"fecha: {c['fecha_cese']}")
            if c.get("valor_ultima_declaracion") is not None:
                extras.append(
                    f"valor declarado anterior: {c['valor_ultima_declaracion']:,.2f} EUR"
                )
            sufijo = f" ({'; '.join(extras)})" if extras else ""
            lines.append(f"  - {etiqueta}{sufijo}")

    if ultimo_presentado:
        lines.append(f"\nUltimo Modelo 720 presentado: ejercicio {ultimo_presentado}")

    lines.append(f"\nPlazo: {plazo}")
    lines.append("")

    for rec in recomendaciones:
        lines.append(f"- {rec}")

    return "\n".join(lines)
