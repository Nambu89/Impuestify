"""
Reasoning trail recorder — provides AI-Act Art. 86 right-to-explanation
data and AESIA Guide 14 compliance evidence.

Stores per-assistant-message:
  - which RAG chunks were retrieved (id + source + trust_level)
  - which tools were called and with what inputs
  - which security pipeline layer outcome
  - fiscal profile snapshot at time of response
  - model used

Retention: 24 months. Run scripts/purge_old_reasoning_trails.py monthly.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


class ReasoningTrailRecorder:
    """Append-only audit log of LLM decisions for compliance."""

    def __init__(self, db=None):
        self._db = db

    async def _get_db(self):
        if self._db:
            return self._db
        from app.database.turso_client import get_db_client

        self._db = await get_db_client()
        return self._db

    @staticmethod
    def _summarize_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Compact chunk metadata to keep DB rows small (no full text)."""
        out = []
        for c in chunks or []:
            out.append(
                {
                    "id": c.get("id"),
                    "source": c.get("title") or c.get("source"),
                    "page": c.get("page"),
                    "trust_level": c.get("trust_level"),
                    "similarity": round(c.get("similarity", 0) or 0, 4),
                }
            )
        return out

    @staticmethod
    def _summarize_tools(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = []
        for t in tool_calls or []:
            out.append(
                {
                    "name": t.get("name") or t.get("tool"),
                    "args_keys": sorted(list((t.get("arguments") or t.get("args") or {}).keys())),
                    "ok": t.get("ok", True),
                }
            )
        return out

    async def record(
        self,
        message_id: str,
        user_id: str,
        conversation_id: str | None,
        rag_chunks: list[dict[str, Any]] | None = None,
        tools_called: list[dict[str, Any]] | None = None,
        security_layer: str | None = None,
        fiscal_profile: dict[str, Any] | None = None,
        model: str | None = None,
    ) -> str | None:
        """Insert a reasoning trail row. Returns the row id, or None on failure."""
        try:
            db = await self._get_db()
            trail_id = str(uuid.uuid4())

            # Defensive: anything we don't recognize gets serialized as best-effort
            chunks_json = json.dumps(
                self._summarize_chunks(rag_chunks or []), default=str, ensure_ascii=False
            )
            tools_json = json.dumps(
                self._summarize_tools(tools_called or []), default=str, ensure_ascii=False
            )
            sec_json = json.dumps({"layer": security_layer or "all_clear"}, ensure_ascii=False)

            # Fiscal profile snapshot — only safe keys, no full object dump
            safe_profile = {}
            if fiscal_profile:
                safe_keys = (
                    "ccaa_residencia",
                    "situacion_laboral",
                    "tipo_actividad",
                    "regimen_estimacion",
                    "edad_contribuyente",
                    "tributacion_conjunta",
                    "roles_adicionales",
                )
                for k in safe_keys:
                    if k in fiscal_profile and fiscal_profile[k] is not None:
                        safe_profile[k] = fiscal_profile[k]
            profile_json = json.dumps(safe_profile, default=str, ensure_ascii=False)

            await db.execute(
                """
                INSERT INTO reasoning_trails
                    (id, message_id, user_id, conversation_id,
                     rag_chunks, tools_called, security_layers,
                     fiscal_profile_snapshot, model, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    trail_id,
                    message_id,
                    user_id,
                    conversation_id,
                    chunks_json,
                    tools_json,
                    sec_json,
                    profile_json,
                    model or "gpt-5-mini",
                    datetime.now(UTC).isoformat(),
                ],
            )
            return trail_id
        except Exception as e:
            logger.warning(f"reasoning_trail.record failed (non-blocking): {e}")
            return None

    async def get_for_message(self, message_id: str) -> dict[str, Any] | None:
        """Fetch the trail row for a given message (for /api/admin or right-to-explain)."""
        db = await self._get_db()
        result = await db.execute(
            "SELECT * FROM reasoning_trails WHERE message_id = ? LIMIT 1",
            [message_id],
        )
        if not result.rows:
            return None
        row = dict(result.rows[0])
        for key in ("rag_chunks", "tools_called", "security_layers", "fiscal_profile_snapshot"):
            try:
                row[key] = json.loads(row.get(key) or "null")
            except Exception:
                pass
        return row


reasoning_trail_recorder = ReasoningTrailRecorder()
