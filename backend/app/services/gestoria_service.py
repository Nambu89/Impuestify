"""Modo Gestoría: una cuenta gestiona hasta 3 clientes; cada cliente = workspace
con identidad fiscal propia (workspace_profiles)."""

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.database.turso_client import get_db_client
from app.services.workspace_service import WorkspaceCreate, WorkspaceService

logger = logging.getLogger(__name__)

GESTORIA_MAX_CLIENTS = 3
ClientTipo = Literal["particular", "autonomo", "sociedad"]


class ClientLimitError(Exception):
    """Se alcanzó el máximo de clientes permitidos para la cuenta gestoría."""


class GestoriaClientCreate(BaseModel):
    nombre_cliente: str
    tipo: ClientTipo
    nif: str | None = None
    ccaa: str | None = None
    situacion_laboral: str | None = None
    epigrafe_iae: str | None = None
    regimen_iva: str | None = None
    fecha_alta: str | None = None
    datos_fiscales: dict[str, Any] = Field(default_factory=dict)


class GestoriaClientUpdate(BaseModel):
    nombre_cliente: str | None = None
    tipo: ClientTipo | None = None
    nif: str | None = None
    ccaa: str | None = None
    situacion_laboral: str | None = None
    epigrafe_iae: str | None = None
    regimen_iva: str | None = None
    fecha_alta: str | None = None
    datos_fiscales: dict[str, Any] | None = None


class GestoriaClient(BaseModel):
    id: str  # = workspace_id
    nombre_cliente: str
    tipo: str
    nif: str | None = None
    ccaa: str | None = None
    situacion_laboral: str | None = None
    epigrafe_iae: str | None = None
    regimen_iva: str | None = None
    fecha_alta: str | None = None
    datos_fiscales: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None
    file_count: int = 0
    declaration_count: int = 0
    ingresos_total: float = 0.0
    iva_balance: float = 0.0


def _icon_for_tipo(tipo: str) -> str:
    return {"particular": "👤", "autonomo": "🧑‍💼", "sociedad": "🏢"}.get(tipo, "📁")


class GestoriaClientService:
    def __init__(self) -> None:
        self.workspaces = WorkspaceService()

    async def _get_db(self):
        return await get_db_client()

    async def _count_clients(self, db, user_id: str) -> int:
        res = await db.execute(
            """SELECT COUNT(*) AS n FROM workspace_profiles wp
               JOIN workspaces w ON w.id = wp.workspace_id
               WHERE w.user_id = ?""",
            [user_id],
        )
        return int(res.rows[0]["n"]) if res.rows else 0

    async def create_client(self, user_id: str, data: GestoriaClientCreate) -> GestoriaClient:
        db = await self._get_db()
        if await self._count_clients(db, user_id) >= GESTORIA_MAX_CLIENTS:
            raise ClientLimitError(f"Máximo {GESTORIA_MAX_CLIENTS} clientes por cuenta gestoría.")

        workspace = await self.workspaces.create_workspace(
            user_id,
            WorkspaceCreate(name=data.nombre_cliente, icon=_icon_for_tipo(data.tipo)),
        )

        now = datetime.now(UTC).isoformat()
        await db.execute(
            """INSERT INTO workspace_profiles
               (id, workspace_id, nombre_cliente, nif, tipo, ccaa, situacion_laboral,
                epigrafe_iae, regimen_iva, fecha_alta, datos_fiscales, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                str(uuid.uuid4()),
                workspace.id,
                data.nombre_cliente,
                data.nif,
                data.tipo,
                data.ccaa,
                data.situacion_laboral,
                data.epigrafe_iae,
                data.regimen_iva,
                data.fecha_alta,
                json.dumps(data.datos_fiscales),
                now,
                now,
            ],
        )
        logger.info("Gestoria %s created client %s (%s)", user_id, workspace.id, data.tipo)
        return GestoriaClient(
            id=workspace.id,
            nombre_cliente=data.nombre_cliente,
            tipo=data.tipo,
            nif=data.nif,
            ccaa=data.ccaa,
            situacion_laboral=data.situacion_laboral,
            epigrafe_iae=data.epigrafe_iae,
            regimen_iva=data.regimen_iva,
            fecha_alta=data.fecha_alta,
            datos_fiscales=data.datos_fiscales,
            created_at=now,
            updated_at=now,
        )

    def _row_to_client(self, row) -> GestoriaClient:
        raw = row.get("datos_fiscales") or "{}"
        datos = json.loads(raw) if isinstance(raw, str) and raw else (raw or {})
        return GestoriaClient(
            id=row.get("workspace_id"),
            nombre_cliente=row.get("nombre_cliente"),
            tipo=row.get("tipo"),
            nif=row.get("nif"),
            ccaa=row.get("ccaa"),
            situacion_laboral=row.get("situacion_laboral"),
            epigrafe_iae=row.get("epigrafe_iae"),
            regimen_iva=row.get("regimen_iva"),
            fecha_alta=row.get("fecha_alta"),
            datos_fiscales=datos,
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    async def list_clients(self, user_id: str) -> list[GestoriaClient]:
        db = await self._get_db()
        res = await db.execute(
            """SELECT wp.* FROM workspace_profiles wp
               JOIN workspaces w ON w.id = wp.workspace_id
               WHERE w.user_id = ?
               ORDER BY wp.created_at DESC""",
            [user_id],
        )
        clients = [self._row_to_client(r) for r in (res.rows or [])]
        for c in clients:
            kpi = await db.execute(
                "SELECT COUNT(wf.id) AS file_count FROM workspace_files wf WHERE wf.workspace_id = ?",
                [c.id],
            )
            c.file_count = int(kpi.rows[0]["file_count"]) if kpi.rows else 0
            decl = await db.execute(
                "SELECT COUNT(*) AS declaration_count FROM quarterly_declarations WHERE workspace_id = ?",
                [c.id],
            )
            c.declaration_count = int(decl.rows[0]["declaration_count"]) if decl.rows else 0
        return clients

    async def get_client(self, user_id: str, workspace_id: str) -> GestoriaClient | None:
        db = await self._get_db()
        res = await db.execute(
            """SELECT wp.* FROM workspace_profiles wp
               JOIN workspaces w ON w.id = wp.workspace_id
               WHERE w.user_id = ? AND wp.workspace_id = ?""",
            [user_id, workspace_id],
        )
        return self._row_to_client(res.rows[0]) if res.rows else None

    async def update_client(
        self, user_id: str, workspace_id: str, data: GestoriaClientUpdate
    ) -> GestoriaClient | None:
        existing = await self.get_client(user_id, workspace_id)
        if not existing:
            return None
        merged = existing.model_copy(update=data.model_dump(exclude_unset=True))
        db = await self._get_db()
        now = datetime.now(UTC).isoformat()
        await db.execute(
            """UPDATE workspace_profiles SET
               nombre_cliente = ?, nif = ?, tipo = ?, ccaa = ?, situacion_laboral = ?,
               epigrafe_iae = ?, regimen_iva = ?, fecha_alta = ?, datos_fiscales = ?, updated_at = ?
               WHERE workspace_id = ?""",
            [
                merged.nombre_cliente,
                merged.nif,
                merged.tipo,
                merged.ccaa,
                merged.situacion_laboral,
                merged.epigrafe_iae,
                merged.regimen_iva,
                merged.fecha_alta,
                json.dumps(merged.datos_fiscales),
                now,
                workspace_id,
            ],
        )
        # Mantener el nombre del workspace sincronizado con el del cliente
        await db.execute(
            "UPDATE workspaces SET name = ?, updated_at = ? WHERE id = ? AND user_id = ?",
            [merged.nombre_cliente, now, workspace_id, user_id],
        )
        merged.updated_at = now
        return merged

    async def delete_client(self, user_id: str, workspace_id: str) -> bool:
        # delete_workspace verifica ownership y CASCADE borra workspace_profiles + files
        return await self.workspaces.delete_workspace(workspace_id, user_id)

    async def get_workspace_fiscal_profile(self, user_id: str, workspace_id: str) -> dict | None:
        """Devuelve el perfil fiscal del cliente con el mismo shape que el loader
        global de chat_stream (ccaa_residencia, situacion_laboral, tipo_cliente +
        datos_fiscales aplanados), para inyectarlo en el agente."""
        client = await self.get_client(user_id, workspace_id)
        if not client:
            return None
        profile: dict[str, Any] = dict(client.datos_fiscales or {})
        if client.ccaa:
            profile["ccaa_residencia"] = client.ccaa
        # situacion_laboral: explícita o derivada del tipo
        profile["situacion_laboral"] = client.situacion_laboral or (
            "autónomo"
            if client.tipo == "autonomo"
            else "sociedad"
            if client.tipo == "sociedad"
            else "particular"
        )
        profile["tipo_cliente"] = client.tipo
        if client.epigrafe_iae:
            profile["epigrafe_iae"] = client.epigrafe_iae
        if client.regimen_iva:
            profile["regimen_iva"] = client.regimen_iva
        return profile
