"""DefensIA DI factories para FastAPI endpoints.

Proporciona get_defensia_storage, get_defensia_rag_verifier, etc. Las
instancias pesadas (storage, writer, export, agent) se cachean a nivel de
modulo (singleton per-worker) para evitar reinstanciar en cada request. Los
servicios que dependen del TursoClient (quota_service, rag_verifier,
defensia_service) se construyen por request porque la conexion a Turso vive
en el app.state y puede variar entre requests.

Uso tipico desde un endpoint::

    from app.services.defensia_dependencies import get_defensia_service

    @router.post("/expedientes/{exp_id}/analyze")
    async def analyze(
        exp_id: str,
        service: DefensiaService = Depends(get_defensia_service),
    ):
        ...
"""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Request

from app.agents.defensia_agent import DefensiaAgent
from app.database.turso_client import TursoClient
from app.services.defensia_export_service import DefensiaExportService
from app.services.defensia_quota_service import DefensiaQuotaService
from app.services.defensia_rag_verifier import DefensiaRagVerifier
from app.services.defensia_service import DefensiaService
from app.services.defensia_storage import DefensiaStorage
from app.services.defensia_writer_service import DefensiaWriterService
from app.utils.hybrid_retriever import HybridRetriever


# ---------------------------------------------------------------------------
# Singletons per-worker (lazy). El lock no hace falta: cada worker del uvicorn
# importa este modulo una vez y FastAPI ejecuta las dependencias en el mismo
# event loop, por lo que no hay condiciones de carrera reales en la
# inicializacion (solo asignaciones simples).
# ---------------------------------------------------------------------------

_storage_singleton: Optional[DefensiaStorage] = None
_writer_singleton: Optional[DefensiaWriterService] = None
_export_singleton: Optional[DefensiaExportService] = None
_agent_singleton: Optional[DefensiaAgent] = None


# ---------------------------------------------------------------------------
# DB dependency — reutiliza el patron de chat_stream.py: el TursoClient vive
# en app.state.db_client. Si no esta disponible devolvemos 503.
# ---------------------------------------------------------------------------


async def get_db(request: Request) -> TursoClient:
    """Devuelve el cliente Turso inyectado en ``app.state.db_client``.

    Raises:
        HTTPException 503 si la conexion a Turso no esta lista.
    """
    if hasattr(request.app.state, "db_client") and request.app.state.db_client:
        return request.app.state.db_client
    raise HTTPException(status_code=503, detail="Base de datos no disponible")


# ---------------------------------------------------------------------------
# Servicios sin estado (singletons)
# ---------------------------------------------------------------------------


def get_defensia_storage() -> DefensiaStorage:
    """Devuelve el servicio de cifrado de documentos (singleton).

    Si ``DEFENSIA_STORAGE_KEY`` no esta configurada el singleton se crea de
    todas formas pero con ``is_enabled=False``. El router traduce los usos
    en ese estado a HTTP 503 capturando ``DefensiaStorageUnavailable``.
    """
    global _storage_singleton
    if _storage_singleton is None:
        _storage_singleton = DefensiaStorage()
    return _storage_singleton


def get_defensia_writer() -> DefensiaWriterService:
    """Servicio de renderizado Jinja de dictamenes y escritos (singleton)."""
    global _writer_singleton
    if _writer_singleton is None:
        _writer_singleton = DefensiaWriterService()
    return _writer_singleton


def get_defensia_export() -> DefensiaExportService:
    """Servicio de export DOCX/PDF (singleton)."""
    global _export_singleton
    if _export_singleton is None:
        _export_singleton = DefensiaExportService()
    return _export_singleton


def get_defensia_agent() -> DefensiaAgent:
    """Chat agent conversacional de DefensIA (singleton)."""
    global _agent_singleton
    if _agent_singleton is None:
        _agent_singleton = DefensiaAgent()
    return _agent_singleton


# ---------------------------------------------------------------------------
# Servicios con estado (por request, atados al TursoClient del app.state)
# ---------------------------------------------------------------------------


def get_defensia_rag_verifier(
    db: TursoClient = Depends(get_db),
) -> DefensiaRagVerifier:
    """Instancia del verificador RAG con su HybridRetriever acoplado al db.

    Se construye por request porque tanto ``HybridRetriever`` como el
    verificador mantienen referencias al ``TursoClient`` inyectado.
    """
    retriever = HybridRetriever(db_client=db)
    return DefensiaRagVerifier(retriever=retriever, db_client=db)


def get_defensia_quota_service(
    db: TursoClient = Depends(get_db),
) -> DefensiaQuotaService:
    """Servicio de cuota mensual — vinculado al TursoClient del request."""
    return DefensiaQuotaService(db_client=db)


def get_defensia_service(
    db: TursoClient = Depends(get_db),
    rag_verifier: DefensiaRagVerifier = Depends(get_defensia_rag_verifier),
    quota_service: DefensiaQuotaService = Depends(get_defensia_quota_service),
    writer: DefensiaWriterService = Depends(get_defensia_writer),
    export: DefensiaExportService = Depends(get_defensia_export),
    storage: DefensiaStorage = Depends(get_defensia_storage),
) -> DefensiaService:
    """Facade que orquesta el pipeline completo — una instancia por request."""
    return DefensiaService(
        db_client=db,
        rag_verifier=rag_verifier,
        quota_service=quota_service,
        writer_service=writer,
        export_service=export,
        storage=storage,
    )


__all__ = [
    "get_db",
    "get_defensia_storage",
    "get_defensia_writer",
    "get_defensia_export",
    "get_defensia_agent",
    "get_defensia_rag_verifier",
    "get_defensia_quota_service",
    "get_defensia_service",
]
