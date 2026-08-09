"""LeadAgent — chatbot captador de leads (BANT-NATB).

Espeja el patrón de ``DefensiaAgent``/``TaxAgent`` (gpt-5 family + temperature=1
+ reasoning_effort=minimal) pero con un loop de function-calling para cualificar
y agendar. NO streamea (el loop de tools es más robusto sin streaming); el router
envía la respuesta final como evento SSE ``content``.

El agente sólo conoce ``dispatcher.dispatch(name, args)`` — los efectos viven en
``LeadToolContext`` (``tools.py``), lo que permite testear con un mock.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field

from openai import AsyncOpenAI

from app.leadbot.config import LeadbotConfig, get_leadbot_config

logger = logging.getLogger(__name__)

OPENAI_TIMEOUT_S = 45.0
MAX_TOOL_ROUNDS = 5


def _system_prompt(cfg: LeadbotConfig) -> str:
    return f"""Eres el asistente virtual de {cfg.brand_name}. Ayudamos a NEGOCIOS \
PEQUEÑOS de Melilla —autónomos y PYMES— a usar la tecnología y la inteligencia \
artificial para vender más y ahorrar tiempo: presencia web sencilla, automatizar \
WhatsApp y la reserva de citas, facturación y gestión, redes sociales, captación \
de clientes y asistentes de IA a su medida.

PERFIL DE QUIEN TE ESCRIBE: comercios, hostelería, peluquerías y estética, \
talleres, clínicas y fisios, asesorías, academias, inmobiliarias, restaurantes… \
Gente con poco tiempo y, normalmente, pocas herramientas digitales (WhatsApp, \
Excel, papel). NO uses jerga técnica (nada de Azure, "cloud", ERP, CRM…); habla \
en cristiano, como a un vecino que lleva su negocio.

TU OBJETIVO ES DOBLE:
1. Sacar TODA la información posible de su caso, con curiosidad y cercanía, para \
que el equipo entienda bien qué necesita ANTES de hablar con él.
2. Si encaja, agendar una llamada con el equipo.

QUÉ AVERIGUAR (poco a poco, de forma natural — NO un interrogatorio):
- Qué negocio tiene y a qué se dedica exactamente (y su nombre comercial).
- Tamaño: ¿está solo o tiene un equipo pequeño?
- Qué le gustaría conseguir o qué problema le quita tiempo o dinero hoy.
- Qué hace ahora para resolverlo y qué herramientas usa (si usa alguna).
- Cuándo le gustaría ponerlo en marcha.
- Presupuesto orientativo, sin presionar (si no lo dice, no pasa nada).
- Su nombre, email y teléfono para que el equipo le contacte.

PROFUNDIZA: cuando te cuente algo, pregunta un poco más para entenderlo de verdad \
(ejemplos, números, cómo lo hace hoy). No te quedes en la superficie. Pero una o \
dos preguntas por mensaje, no más.

IDENTIDAD: eres una IA; si te preguntan, dilo con naturalidad. No finjas ser humano.

ESTILO: español de España, tildes correctas, cercano y sencillo. Mensajes breves \
(2-4 frases). No inventes precios ni promesas; si insisten en precio, di que \
depende de lo que necesite y que el equipo se lo concreta.

HERRAMIENTAS (úsalas; no las menciones por su nombre):
- save_lead_info: guarda CADA dato útil EN CUANTO lo sepas (nombre, email, \
teléfono, negocio/empresa, sector, necesidad —cuanto más detalle mejor—, plazo, \
presupuesto). Llámala varias veces a lo largo de la charla.
- get_available_slots: cuando muestre interés en hablar con el equipo, consulta \
huecos. Si devuelve available=false, pídele el email y dile que el equipo le \
contactará; luego llama a book_meeting con ese email.
- book_meeting: para reservar un hueco concreto (slot_iso de los ofrecidos) con su \
email. Si no hay calendario, sirve igual para registrar el lead.
- escalate_to_human: si pide hablar con una persona ya.

REGLAS DE AGENDA:
- Antes de proponer cita, ten al menos: necesidad clara + email.
- Ofrece los huecos de get_available_slots tal cual; no inventes huecos.
- Pide SIEMPRE el email antes de cerrar una cita.

Si el primer mensaje es un saludo, preséntate en una frase y pregunta a qué se \
dedica su negocio y en qué le podemos ayudar."""


# Esquemas de function-calling (OpenAI tools)
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "save_lead_info",
            "description": "Guarda datos del lead conforme se conocen. Llamar varias veces.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                    "company": {"type": "string"},
                    "sector": {"type": "string"},
                    "need": {"type": "string", "description": "Qué necesita el lead (texto breve)"},
                    "decision_maker": {"type": "boolean"},
                    "timeline": {"type": "string", "enum": ["now", "1-3m", "3-6m", "6m+"]},
                    "budget_range": {
                        "type": "string",
                        "enum": ["<500", "500-1500", "1500-3000", "3000+"],
                        "description": "Presupuesto orientativo en EUR (negocios pequeños)",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_available_slots",
            "description": "Consulta huecos libres para una llamada. Devuelve lista de slots.",
            "parameters": {
                "type": "object",
                "properties": {
                    "preferred_period": {
                        "type": "string",
                        "description": "Preferencia opcional (ej. 'mañanas', 'esta semana')",
                    }
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_meeting",
            "description": "Reserva un hueco para una llamada con el equipo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "slot_iso": {"type": "string", "description": "ISO8601 de un hueco ofrecido"},
                    "attendee_email": {"type": "string"},
                    "attendee_name": {"type": "string"},
                },
                "required": ["attendee_email"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": "Marca que el lead quiere/necesita atención humana.",
            "parameters": {
                "type": "object",
                "properties": {"reason": {"type": "string"}},
                "additionalProperties": False,
            },
        },
    },
]

FALLBACK_MESSAGE = (
    "Disculpa, he tenido un problema técnico. ¿Puedes repetirme en qué te gustaría "
    "que te ayudemos? Si lo prefieres, dime tu email y te contactamos."
)


@dataclass
class LeadAgentResult:
    reply_text: str
    tokens_in: int = 0
    tokens_out: int = 0
    tool_calls: list[str] = field(default_factory=list)


class LeadAgent:
    def __init__(self, cfg: LeadbotConfig | None = None, client: AsyncOpenAI | None = None):
        self.cfg = cfg or get_leadbot_config()
        self._client = client or AsyncOpenAI(api_key=self.cfg.openai_api_key)

    async def run(
        self,
        message: str,
        history: list[dict[str, str]],
        dispatcher,
    ) -> LeadAgentResult:
        """Procesa un turno: loop de tools y devuelve el texto final.

        Args:
            message: mensaje del usuario (ya sanitizado por el pipeline de seguridad).
            history: turnos previos ``[{"role","content"}]`` (user/assistant).
            dispatcher: objeto con ``async dispatch(name, args) -> dict``.
        """
        messages: list[dict] = [{"role": "system", "content": _system_prompt(self.cfg)}]
        messages.extend(history[-20:])
        messages.append({"role": "user", "content": message})

        result = LeadAgentResult(reply_text="")

        try:
            for _round in range(MAX_TOOL_ROUNDS):
                completion = await asyncio.wait_for(
                    self._client.chat.completions.create(
                        model=self.cfg.model,
                        messages=messages,
                        tools=TOOLS,
                        tool_choice="auto",
                        temperature=1,
                        max_completion_tokens=self.cfg.max_completion_tokens,
                        reasoning_effort=self.cfg.reasoning_effort,
                    ),
                    timeout=OPENAI_TIMEOUT_S,
                )
                usage = getattr(completion, "usage", None)
                if usage:
                    result.tokens_in += getattr(usage, "prompt_tokens", 0) or 0
                    result.tokens_out += getattr(usage, "completion_tokens", 0) or 0

                choice = completion.choices[0]
                msg = choice.message
                tool_calls = getattr(msg, "tool_calls", None)

                if not tool_calls:
                    result.reply_text = (msg.content or "").strip()
                    break

                # Re-inyecta el mensaje del asistente con sus tool_calls
                messages.append(
                    {
                        "role": "assistant",
                        "content": msg.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in tool_calls
                        ],
                    }
                )
                for tc in tool_calls:
                    name = tc.function.name
                    result.tool_calls.append(name)
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    tool_result = await dispatcher.dispatch(name, args)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(tool_result, ensure_ascii=False),
                        }
                    )
            else:
                # Agotó las rondas sin texto final: forzar un cierre.
                logger.warning("LeadAgent agotó MAX_TOOL_ROUNDS sin respuesta final")

            if not result.reply_text:
                result.reply_text = (
                    "He registrado tus datos. ¿Hay algo más que quieras contarme o "
                    "prefieres que te contactemos por email?"
                )
        except TimeoutError:
            logger.error("LeadAgent OpenAI timeout tras %ss", OPENAI_TIMEOUT_S)
            result.reply_text = FALLBACK_MESSAGE
        except Exception as exc:  # noqa: BLE001 — degradación graceful
            logger.error("LeadAgent error: %s", exc, exc_info=True)
            result.reply_text = FALLBACK_MESSAGE

        return result
