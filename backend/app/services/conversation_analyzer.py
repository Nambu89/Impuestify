"""
Post-conversation LLM analyzer for Impuestify.

Analyzes completed conversations to extract structured fiscal facts
and merge them into the user's profile. Runs as a background task.

Priority: manual > llm > regex (check _source field)
Skips conversations with < 3 messages.
"""
import json
import logging
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """Analiza esta conversacion fiscal y extrae datos estructurados del usuario.
Devuelve SOLO un JSON valido con los campos que se mencionan EXPLICITAMENTE.
Si un dato NO se menciona, NO lo incluyas.

Campos posibles:
- ccaa (str): comunidad autonoma de residencia
- situacion_laboral (str): asalariado/autonomo/pensionista/desempleado/farmaceutico
- hijos (int): numero de hijos
- edad_hijos (list[int]): edades de los hijos
- custodia_compartida (bool)
- hipoteca_activa (bool)
- importe_hipoteca (float): cuota mensual
- plan_pensiones (bool)
- aportacion_plan_pensiones (float): aportacion anual
- alquiler_vivienda (bool)
- importe_alquiler (float): cuota mensual alquiler
- autonomo_actividad (str): tipo de actividad
- cnae (str): codigo CNAE
- cripto_activo (bool)
- discapacidad_grado (int): porcentaje
- familia_numerosa (bool)
- donaciones (bool)
- ingresos_brutos (float): ingresos anuales brutos

Responde SOLO con el JSON, sin texto adicional."""


class ConversationAnalyzer:
    """Extracts fiscal facts from conversations using LLM."""

    def __init__(self, db=None):
        self._db = db
        self._client = None

    async def _get_db(self):
        if self._db:
            return self._db
        from app.database.turso_client import get_db_client
        self._db = await get_db_client()
        return self._db

    def _get_client(self) -> AsyncOpenAI:
        if not self._client:
            self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    async def _get_messages(self, conversation_id: str) -> List[Dict[str, str]]:
        """Load messages from database."""
        db = await self._get_db()
        result = await db.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY created_at",
            [conversation_id],
        )
        return [dict(row) for row in result.rows or []]

    async def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        """Call gpt-5-mini with the extraction prompt."""
        client = self._get_client()
        conversation_text = "\n".join(
            f"{m['role']}: {m['content']}" for m in messages
        )
        response = await client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": EXTRACTION_PROMPT},
                {"role": "user", "content": conversation_text},
            ],
            temperature=1,
            max_completion_tokens=500,
        )
        return response.choices[0].message.content.strip()

    async def _merge_facts(self, user_id: str, extracted: Dict[str, Any]) -> None:
        """
        Merge extracted facts into user profile with source='llm'.

        Priority: manual > llm > regex
        Fields with _source="manual" are never overwritten.
        Fields with _source="llm" overwrite _source="regex" but not "manual".
        """
        db = await self._get_db()

        # Load existing profile
        result = await db.execute(
            "SELECT datos_fiscales FROM user_profiles WHERE user_id = ?",
            [user_id],
        )
        existing = {}
        if result.rows:
            raw = result.rows[0]["datos_fiscales"] if isinstance(result.rows[0], dict) else None
            if raw:
                existing = json.loads(raw) if isinstance(raw, str) else raw

        # Merge: manual > llm > regex (check _source field)
        for key, value in extracted.items():
            existing_entry = existing.get(key)

            # New format: {"value": ..., "_source": ...}
            if isinstance(existing_entry, dict) and "_source" in existing_entry:
                if existing_entry["_source"] == "manual":
                    continue  # manual data takes priority over llm
                # llm overwrites regex and conversation
            # Legacy format or no entry: safe to write

            existing[key] = {
                "value": value,
                "_source": "llm",
            }

        datos_json = json.dumps(existing)

        # Check if profile exists
        if result.rows:
            await db.execute(
                "UPDATE user_profiles SET datos_fiscales = ?, updated_at = datetime('now') WHERE user_id = ?",
                [datos_json, user_id],
            )
        else:
            # No profile yet - create one (unlikely but safe)
            import uuid
            profile_id = str(uuid.uuid4())
            await db.execute(
                """INSERT INTO user_profiles (id, user_id, datos_fiscales, created_at, updated_at)
                   VALUES (?, ?, ?, datetime('now'), datetime('now'))""",
                [profile_id, user_id, datos_json],
            )

    async def analyze(self, conversation_id: str, user_id: str) -> Dict[str, Any]:
        """
        Analyze a conversation and extract fiscal facts.

        Skips conversations with < 3 messages.
        Returns extracted facts dict (empty if nothing found).
        """
        messages = await self._get_messages(conversation_id)

        if len(messages) < 3:
            return {}

        try:
            raw_response = await self._call_llm(messages)
            # Parse JSON response (strip markdown code fences if present)
            clean = raw_response.strip()
            if clean.startswith("```"):
                # Remove ```json ... ``` wrapper
                lines = clean.split("\n")
                clean = "\n".join(lines[1:-1]) if len(lines) > 2 else clean

            extracted = json.loads(clean)
            if not isinstance(extracted, dict):
                return {}

            await self._merge_facts(user_id, extracted)

            logger.info(
                "Extracted %d fiscal facts from conversation %s for user %s",
                len(extracted), conversation_id, user_id,
            )
            return extracted

        except (json.JSONDecodeError, Exception) as e:
            logger.warning("Failed to analyze conversation %s: %s", conversation_id, e)
            return {}
