"""El texto de una excepción no puede llegar al usuario.

El frontend pinta el `data` de un evento ``error`` tal cual
(``useStreamingChat.ts``, ``case 'error'``), así que emitir ``str(e)`` enseña la
traza interna a quien pregunta — y a cualquiera que sondee el endpoint desde
fuera.

Precedente (Bug 119): ``chat_stream.py`` emitía ``str(e)`` y durante ocho semanas
la respuesta del chat fue ``'Request' object has no attribute 'workspace_id'``.
El red-team lo leyó desde fuera sin autenticarse como admin.

Es la misma clase de fuga que emitir ``pipeline_result.reason`` en vez de
``rejection_message`` (regla del Bug 104): el motivo interno se queda en el log.

Test estático — no levanta nada.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROUTERS_DIR = Path(__file__).resolve().parent.parent / "app" / "routers"


def _nombres_de_excepcion(arbol: ast.Module) -> set[str]:
    """Variables ligadas en un ``except ... as <nombre>``."""
    return {
        nodo.name for nodo in ast.walk(arbol) if isinstance(nodo, ast.ExceptHandler) and nodo.name
    }


def _es_str_de_excepcion(nodo: ast.expr, excepciones: set[str]) -> bool:
    """¿La expresión es ``str(exc)`` / ``f"{exc}"`` sobre una excepción?"""
    if isinstance(nodo, ast.Call):
        if isinstance(nodo.func, ast.Name) and nodo.func.id == "str" and nodo.args:
            arg = nodo.args[0]
            return isinstance(arg, ast.Name) and arg.id in excepciones
    if isinstance(nodo, ast.JoinedStr):  # f-string
        return any(
            isinstance(v, ast.FormattedValue)
            and isinstance(v.value, ast.Name)
            and v.value.id in excepciones
            for v in nodo.values
        )
    if isinstance(nodo, ast.Name):
        return nodo.id in excepciones
    return False


def _emisiones_con_excepcion(arbol: ast.Module) -> list[tuple[int, str]]:
    """``yield {"event": "error", "data": <algo derivado de la excepción>}``."""
    excepciones = _nombres_de_excepcion(arbol)
    if not excepciones:
        return []

    ofensores: list[tuple[int, str]] = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Dict):
            continue
        claves = {
            k.value: v
            for k, v in zip(nodo.keys, nodo.values, strict=False)
            if isinstance(k, ast.Constant)
        }
        evento = claves.get("event")
        data = claves.get("data")
        es_error = isinstance(evento, ast.Constant) and evento.value == "error"
        if es_error and data is not None and _es_str_de_excepcion(data, excepciones):
            ofensores.append((nodo.lineno, ast.dump(data)[:60]))
    return ofensores


@pytest.mark.parametrize(
    "ruta",
    sorted(p for p in ROUTERS_DIR.glob("*.py") if p.name != "__init__.py"),
    ids=lambda p: p.name,
)
def test_ningun_router_emite_la_excepcion_al_cliente(ruta: Path):
    arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))

    ofensores = _emisiones_con_excepcion(arbol)

    assert not ofensores, (
        f"{ruta.name}: se emite el texto de la excepción en un evento `error`, "
        f"y el frontend se lo enseña al usuario. Manda un mensaje genérico y deja "
        f"el detalle en `logger.error(..., exc_info=True)`. Líneas: "
        + ", ".join(str(ln) for ln, _ in ofensores)
    )


def test_la_guarda_detecta_el_bug_119():
    """Sin esto, el test de arriba podría estar comprobando nada."""
    codigo_roto = """
async def event_stream():
    try:
        pass
    except Exception as e:
        logger.error(f"Stream error: {e}", exc_info=True)
        yield {"event": "error", "data": str(e)}
"""
    ofensores = _emisiones_con_excepcion(ast.parse(codigo_roto))
    assert len(ofensores) == 1, ofensores


def test_la_guarda_acepta_un_mensaje_generico():
    """Contrapunto: el patrón correcto no debe marcarse.

    Es el que ya usaba `defensia.py` — genérico al cliente, detalle al log.
    """
    codigo_valido = """
async def event_stream():
    try:
        pass
    except Exception as e:
        logger.error("DefensIA chat error: %s", e, exc_info=True)
        yield {"event": "error", "data": "Error en el chat DefensIA"}
"""
    assert _emisiones_con_excepcion(ast.parse(codigo_valido)) == []
