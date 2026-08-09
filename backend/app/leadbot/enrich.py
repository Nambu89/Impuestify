"""Enriquecimiento del lead — genera un brief accionable para el equipo.

Cuando un lead se cualifica/agenda/escala, antes de avisar a Joaquín la IA
sintetiza toda la conversación en un resumen claro: quién es el negocio, qué
necesita, qué servicio encaja y cuál es el siguiente paso. Pensado para el
cliente típico de Melilla: autónomos y PYMES pequeñas, poca o ninguna
herramienta digital (nada de Azure/cloud/ERP).

Resiliente: si OpenAI falla o no está configurado, cae a un brief básico armado
con los campos del lead — nunca rompe el flujo del bot.
"""

from __future__ import annotations

import asyncio
import logging

from app.leadbot.config import LeadbotConfig, get_leadbot_config

logger = logging.getLogger(__name__)

ENRICH_TIMEOUT_S = 30.0


def _system_prompt(cfg: LeadbotConfig) -> str:
    return f"""Preparas un RESUMEN INTERNO para el equipo de {cfg.brand_name} a partir \
de la conversación entre nuestro chatbot y un posible cliente.

Perfil típico: autónomo o PYME pequeña de Melilla (comercio, hostelería, \
peluquería/estética, taller, clínica/fisio, asesoría, academia, inmobiliaria, \
restauración…). Negocios pequeños, con poca o ninguna herramienta digital. NO \
asumas infraestructura técnica (nada de Azure, cloud, ERP ni jerga enterprise).

Redacta un brief breve y accionable en español (markdown sencillo) con estas \
secciones, en este orden:

**Negocio:** qué es y a qué se dedica (nombre del negocio si lo dio).
**Tamaño:** autónomo en solitario / equipo pequeño, si se deduce.
**Qué necesita:** el problema o deseo concreto, en sus palabras.
**Qué usa hoy:** herramientas actuales si las mencionó (probablemente pocas).
**Servicio recomendado:** qué de {cfg.brand_name} encaja (presencia web, \
automatización de WhatsApp/citas, facturación, redes sociales, captación de \
clientes, asistente de IA sencillo…).
**Interés y plazo:** nivel de interés y cuándo querría empezar.
**Presupuesto:** sólo si lo mencionó.
**Contacto:** nombre, email, teléfono.
**Siguiente paso:** recomendación concreta para el equipo.

REGLAS: no inventes datos que no estén en la conversación (escribe "no \
especificado"). Sé concreto y breve. Si la conversación es muy corta, dilo."""


class LeadEnricher:
    def __init__(self, cfg: LeadbotConfig | None = None, client=None):
        self.cfg = cfg or get_leadbot_config()
        self._client = client

    def _ensure_client(self):
        if self._client is None:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(api_key=self.cfg.openai_api_key)
        return self._client

    async def build_brief(self, lead: dict, messages: list[dict]) -> str:
        """Devuelve un brief en texto. Cae al brief básico ante cualquier fallo."""
        basic = self._basic_brief(lead, messages)
        if not self.cfg.openai_configured:
            return basic
        try:
            client = self._ensure_client()
            convo = "\n".join(f"{m.get('role')}: {m.get('content')}" for m in (messages or []))
            fields = ", ".join(
                f"{k}={lead.get(k)}"
                for k in (
                    "name",
                    "email",
                    "phone",
                    "company",
                    "sector",
                    "need",
                    "timeline",
                    "budget_range",
                )
                if lead.get(k)
            )
            resp = await asyncio.wait_for(
                client.chat.completions.create(
                    model=self.cfg.model,
                    messages=[
                        {"role": "system", "content": _system_prompt(self.cfg)},
                        {
                            "role": "user",
                            "content": f"Datos recogidos: {fields or 'pocos'}\n\nConversación:\n{convo or '(vacía)'}",
                        },
                    ],
                    temperature=1,
                    max_completion_tokens=700,
                    reasoning_effort=self.cfg.reasoning_effort,
                ),
                timeout=ENRICH_TIMEOUT_S,
            )
            text = (resp.choices[0].message.content or "").strip()
            return text or basic
        except Exception as exc:  # noqa: BLE001 — nunca romper el aviso al dueño
            logger.warning("Lead enrichment falló, uso brief básico: %s", exc)
            return basic

    def _basic_brief(self, lead: dict, messages: list[dict]) -> str:
        def v(key: str) -> str:
            return str(lead.get(key) or "no especificado")

        return (
            f"**Negocio:** {v('company')} ({v('sector')})\n"
            f"**Qué necesita:** {v('need')}\n"
            f"**Interés y plazo:** {v('timeline')}\n"
            f"**Presupuesto:** {v('budget_range')}\n"
            f"**Contacto:** {v('name')} · {v('email')} · {v('phone')}\n"
            f"**Mensajes intercambiados:** {len(messages or [])}\n"
            f"**Siguiente paso:** revisar y contactar al cliente."
        )
