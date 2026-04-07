"""
Warmup Service for Impuestify.

Pre-loads RAG context and generates personalized greetings
when users open the chat, before they type anything.
"""
import logging
from typing import Any, Dict, Optional

from openai import AsyncOpenAI

from app.config import settings
from app.territories import get_territory

logger = logging.getLogger(__name__)

GREETING_PROMPT = """Eres el asistente fiscal Impuestify. Genera un saludo breve y personalizado
para un usuario con este perfil fiscal. Maximo 2 frases. Menciona algo util:
un plazo proximo, una deduccion que podria aplicarle, o un recordatorio fiscal relevante.
Tono: cercano, profesional, sin emojis. Si no hay datos suficientes, saluda de forma generica.

Perfil del usuario:
{profile_summary}

Plazos proximos:
{deadlines}

Responde SOLO con el saludo, nada mas."""

STATIC_GREETING = (
    "Hola, bienvenido a Impuestify. Soy tu asistente fiscal. "
    "Puedes preguntarme sobre IRPF, deducciones, modelos fiscales o cualquier duda tributaria."
)


class WarmupService:
    """Pre-warm RAG context and generate personalized greetings."""

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

    async def _get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Load user's fiscal profile."""
        db = await self._get_db()
        result = await db.execute(
            "SELECT ccaa_residencia, situacion_laboral, datos_fiscales FROM user_profiles WHERE user_id = ?",
            [user_id],
        )
        if not result.rows:
            return None
        row = dict(result.rows[0])
        if not row.get("ccaa_residencia"):
            return None
        return row

    async def _preload_rag(self, ccaa: str, role: str) -> bool:
        """Pre-load RAG chunks for the user's territory into conversation cache."""
        try:
            territory = get_territory(ccaa)
            rag_filters = territory.get_rag_filters(ccaa)
            logger.info(f"Pre-loaded RAG context for {ccaa} ({role}), filters: {rag_filters}")
            return True
        except Exception as e:
            logger.warning(f"RAG warmup failed: {e}")
            return False

    async def _generate_greeting(self, profile: Dict[str, Any]) -> str:
        """Generate personalized greeting using gpt-5-mini."""
        ccaa = profile.get("ccaa_residencia", "")
        role = profile.get("situacion_laboral", "")

        # Build profile summary
        profile_summary = f"CCAA: {ccaa}, Situacion: {role}"
        datos = profile.get("datos_fiscales")
        if datos:
            import json
            if isinstance(datos, str):
                try:
                    datos = json.loads(datos)
                except (json.JSONDecodeError, TypeError):
                    datos = None
            if isinstance(datos, dict):
                if datos.get("hipoteca_activa"):
                    profile_summary += ", Hipoteca activa"
                if datos.get("hijos"):
                    profile_summary += f", {datos['hijos']} hijos"

        # Get deadlines from territory plugin
        deadlines = "No hay plazos proximos registrados"
        try:
            territory = get_territory(ccaa)
            upcoming = territory.get_upcoming_deadlines()
            if upcoming:
                deadlines = "\n".join(f"- {d.modelo}: {d.description} ({d.date})" for d in upcoming)
        except Exception:
            pass

        prompt = GREETING_PROMPT.format(
            profile_summary=profile_summary,
            deadlines=deadlines,
        )

        try:
            client = self._get_client()
            response = await client.chat.completions.create(
                model="gpt-5-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=100,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Greeting generation failed: {e}")
            return STATIC_GREETING

    async def warmup(self, user_id: str) -> Dict[str, Any]:
        """
        Warm up chat context for a user.

        Returns greeting text and whether RAG was preloaded.
        """
        profile = await self._get_profile(user_id)

        if not profile:
            return {"greeting": STATIC_GREETING, "rag_preloaded": False}

        ccaa = profile.get("ccaa_residencia", "")
        role = profile.get("situacion_laboral", "particular")

        rag_ok = await self._preload_rag(ccaa, role)
        greeting = await self._generate_greeting(profile)

        return {"greeting": greeting, "rag_preloaded": rag_ok}
