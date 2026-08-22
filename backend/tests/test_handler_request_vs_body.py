"""Ningún handler puede leer un campo del cuerpo sobre el objeto ``request``.

En los endpoints con rate limiting, slowapi **obliga** a que el primer parámetro
se llame ``request`` y sea un ``starlette.Request``, así que el cuerpo Pydantic
tiene que llamarse ``body``. Confundirlos no da error de import ni de tipos:
revienta en runtime con ``AttributeError``, y solo en la petición real.

Precedente (Bug 119): ``chat_stream.py`` hacía ``request.workspace_id`` en vez de
``body.workspace_id``. Entró el 2026-06-28 con Modo Gestoría y estuvo **ocho
semanas** rompiendo TODAS las peticiones de chat sin que nada lo detectara: el
único test del endpoint (``test_stream.py``) es un script de integración que
necesita un servidor vivo.

Este test es estático — no levanta nada — y cubre la clase entera de error, no
solo la línea que fallaba.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parent.parent / "app"

# Atributos legítimos de starlette.Request que los handlers sí usan.
# Si un handler necesita uno nuevo, añadirlo aquí a conciencia.
ATRIBUTOS_REALES_DE_REQUEST = {
    "app",
    "auth",
    "base_url",
    "client",
    "cookies",
    "headers",
    "is_disconnected",
    "json",
    "method",
    "path_params",
    "query_params",
    "scope",
    "session",
    "state",
    "stream",
    "url",
    "user",
}


def _campos_de_modelos_pydantic(arbol: ast.Module) -> set[str]:
    """Nombres de campo declarados en los BaseModel del módulo."""
    campos: set[str] = set()
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.ClassDef):
            continue
        hereda_de_basemodel = any(
            (isinstance(b, ast.Name) and b.id == "BaseModel")
            or (isinstance(b, ast.Attribute) and b.attr == "BaseModel")
            for b in nodo.bases
        )
        if not hereda_de_basemodel:
            continue
        for item in nodo.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                campos.add(item.target.id)
    return campos


def _es_starlette_request(anotacion: ast.expr | None) -> bool:
    """¿La anotación es `Request` / `starlette.Request` (y no un BaseModel)?"""
    if isinstance(anotacion, ast.Name):
        return anotacion.id == "Request"
    if isinstance(anotacion, ast.Attribute):
        return anotacion.attr == "Request"
    return False


def _accesos_sobre_request(arbol: ast.Module) -> list[tuple[int, str]]:
    """``request.<attr>`` SOLO dentro de handlers donde `request` es un Request.

    Hay routers que llaman `request` al cuerpo Pydantic (``request:
    CheckoutRequest``). Ahí `request.plan_type` es correcto, así que mirar solo
    el nombre da falsos positivos: hay que mirar la ANOTACIÓN.
    """
    accesos: list[tuple[int, str]] = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        args = nodo.args
        params = [*args.posonlyargs, *args.args, *args.kwonlyargs]
        if not any(a.arg == "request" and _es_starlette_request(a.annotation) for a in params):
            continue
        accesos.extend(
            (n.lineno, n.attr)
            for n in ast.walk(nodo)
            if isinstance(n, ast.Attribute)
            and isinstance(n.value, ast.Name)
            and n.value.id == "request"
        )
    return accesos


@pytest.mark.parametrize(
    "ruta",
    sorted(p for p in (APP_DIR / "routers").glob("*.py") if p.name != "__init__.py"),
    ids=lambda p: p.name,
)
def test_ningun_handler_lee_un_campo_del_body_sobre_request(ruta: Path):
    arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
    campos_body = _campos_de_modelos_pydantic(arbol)

    ofensores = [
        (linea, attr)
        for linea, attr in _accesos_sobre_request(arbol)
        if attr in campos_body and attr not in ATRIBUTOS_REALES_DE_REQUEST
    ]

    assert not ofensores, (
        f"{ruta.name}: se lee un campo del cuerpo sobre `request`, que es el "
        f"starlette.Request. Usa `body.<campo>`. Ofensores: "
        + ", ".join(f"linea {ln} -> request.{a}" for ln, a in ofensores)
    )


def test_la_guarda_detecta_el_bug_119():
    """El test anterior no vale nada si no cazaría el bug original.

    Se le da el código exacto que estuvo ocho semanas en producción.
    """
    codigo_roto = """
from pydantic import BaseModel

class StreamQuestionRequest(BaseModel):
    question: str
    workspace_id: str | None = None

async def ask_question_stream(request: Request, body: StreamQuestionRequest):
    if await request.is_disconnected():
        return
    return resolve(workspace_id=request.workspace_id)
"""
    arbol = ast.parse(codigo_roto)
    campos = _campos_de_modelos_pydantic(arbol)
    assert "workspace_id" in campos and "question" in campos

    ofensores = [
        (ln, a)
        for ln, a in _accesos_sobre_request(arbol)
        if a in campos and a not in ATRIBUTOS_REALES_DE_REQUEST
    ]

    assert ofensores == [(11, "workspace_id")], ofensores


def test_la_guarda_no_marca_un_body_llamado_request():
    """Contrapunto: varios routers llaman `request` al cuerpo Pydantic.

    ``request: CheckoutRequest`` es legítimo y `request.plan_type` también.
    Sin mirar la anotación, la guarda daba 4 falsos positivos.
    """
    codigo_valido = """
from pydantic import BaseModel

class CheckoutRequest(BaseModel):
    plan_type: str

async def create_checkout(request: CheckoutRequest):
    return stripe.checkout(plan=request.plan_type)
"""
    arbol = ast.parse(codigo_valido)
    campos = _campos_de_modelos_pydantic(arbol)
    assert "plan_type" in campos

    assert _accesos_sobre_request(arbol) == []
