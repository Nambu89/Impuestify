"""
SSE Streaming Utilities for Chain-of-Thought UI

Provides Server-Sent Events streaming infrastructure for displaying
AI reasoning progress in real-time, ChatGPT/Claude style.

Uses sse-starlette format: yields dict with 'event' and 'data' keys
"""
import json
import time
import asyncio
import logging
from typing import AsyncGenerator, Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Railway SSE best practices
HEARTBEAT_INTERVAL = 15  # seconds - prevents 2min timeout on Railway
MAX_STREAM_DURATION = 240  # 4 minutes - well under Railway's 5min limit


# Friendly tool name mapping for UI display: (active_label, done_label)
TOOL_DISPLAY_NAMES: Dict[str, tuple] = {
    "simulate_irpf": ("Simulando tu IRPF", "Simulacion de IRPF completada"),
    "calculate_irpf": ("Calculando tramos IRPF", "Calculo de tramos completado"),
    "calculate_autonomous_quota": ("Calculando cuota de autonomo", "Cuota de autonomo calculada"),
    "calculate_modelo_303": ("Calculando Modelo 303 (IVA)", "Modelo 303 calculado"),
    "calculate_modelo_130": ("Calculando Modelo 130 (IRPF)", "Modelo 130 calculado"),
    "calculate_modelo_ipsi": ("Calculando IPSI trimestral", "IPSI calculado"),
    "discover_deductions": ("Buscando deducciones aplicables", "Deducciones encontradas"),
    "search_tax_regulations": ("Consultando normativa fiscal", "Normativa consultada"),
    "analyze_payslip": ("Analizando tu nomina", "Nomina analizada"),
    "web_scraper": ("Consultando fuentes oficiales", "Fuentes consultadas"),
    "update_fiscal_profile": ("Actualizando tu perfil fiscal", "Perfil fiscal actualizado"),
    "calculate_isd": ("Calculando Impuesto Sucesiones/Donaciones", "ISD calculado"),
    "lookup_casilla": ("Consultando casillas IRPF", "Casilla encontrada"),
    "calculate_crypto_gains": ("Calculando ganancias cripto", "Ganancias cripto calculadas"),
    "parse_crypto_csv": ("Procesando CSV de exchange", "CSV procesado"),
    "get_workspace_summary": ("Analizando workspace", "Workspace analizado"),
    "calculate_vat_balance": ("Calculando balance IVA", "Balance IVA calculado"),
    "project_annual_irpf": ("Proyectando IRPF anual", "Proyeccion completada"),
    "get_quarterly_deadlines": ("Consultando plazos fiscales", "Plazos consultados"),
}


class ProgressCallback:
    """
    Callback interface for streaming progress updates from AI processing.

    Used by TaxAgent to emit events during query processing.
    Events are stored in a queue and yielded by sse_generator().
    """

    def __init__(self):
        self.events: asyncio.Queue = asyncio.Queue()
        self._closed = False

    async def emit(self, event: str, data: Any):
        """Emit an event to the stream as dict for sse-starlette"""
        if not self._closed:
            # sse-starlette expects dict with 'event' and 'data' keys
            data_str = json.dumps(data) if not isinstance(data, str) else data
            event_dict = {"event": event, "data": data_str}
            await self.events.put(event_dict)
            # Use print for Railway visibility (logger may not flush in async context)
            print(f"📤 SSE Event queued: {event}", flush=True)
            logger.info(f"📤 SSE Event queued: {event}")

    async def thinking(self, message: str):
        """AI is thinking/reasoning"""
        await self.emit("thinking", message)

    async def tool_call(self, tool_name: str, args: Dict[str, Any]):
        """AI is calling a tool — emits friendly name for UI"""
        names = TOOL_DISPLAY_NAMES.get(tool_name, (tool_name, tool_name))
        await self.emit("tool_call", {"tool": tool_name, "display_name": names[0], "done_name": names[1], "args": args})

    async def tool_result(self, tool_name: str, success: bool):
        """Tool execution completed"""
        names = TOOL_DISPLAY_NAMES.get(tool_name, (tool_name, tool_name))
        await self.emit("tool_result", {"tool": tool_name, "display_name": names[0], "done_name": names[1], "success": success})

    async def content_chunk(self, text: str):
        """Stream a single chunk/token of the response (for real-time typing effect)"""
        # Skip chunks that are purely technical artifacts
        if text and _is_technical_chunk(text):
            return
        await self.emit("content_chunk", text)

    async def content(self, text: str):
        """Stream final response content (full replacement)"""
        await self.emit("content", text)

    async def error(self, message: str):
        """An error occurred"""
        await self.emit("error", message)

    async def done(self, conversation_id: Optional[str] = None):
        """Processing complete"""
        data = {"conversation_id": conversation_id} if conversation_id else ""
        await self.emit("done", data)
        self._closed = True

    def close(self):
        """Mark callback as closed"""
        self._closed = True


async def sse_generator(
    callback: ProgressCallback,
    timeout: float = MAX_STREAM_DURATION
) -> AsyncGenerator[Dict[str, str], None]:
    """
    Generate SSE events from a ProgressCallback.
    
    Implements Railway-compatible streaming with:
    - Heartbeat comments every 15s
    - Timeout protection
    - Graceful error handling
    
    IMPORTANT: Yields dict format for sse-starlette:
    {"event": "event_name", "data": "data_string"}
    
    Args:
        callback: Progress callback with event queue
        timeout: Maximum stream duration in seconds
        
    Yields:
        Dict with 'event' and 'data' keys (sse-starlette format)
    """
    start_time = time.time()
    last_heartbeat = time.time()
    
    print("🚀 SSE generator started", flush=True)
    logger.info("🚀 SSE generator started")
    
    try:
        while True:
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > timeout:
                print(f"⏱️ Stream timeout after {elapsed:.1f}s", flush=True)
                logger.warning(f"Stream timeout after {elapsed:.1f}s")
                yield {"event": "error", "data": "Stream timeout - processing took too long"}
                yield {"event": "done", "data": ""}
                break
            
            # Send heartbeat if needed (Railway requirement)
            current_time = time.time()
            if current_time - last_heartbeat > HEARTBEAT_INTERVAL:
                # sse-starlette uses 'comment' key for SSE comments
                yield {"comment": "heartbeat"}
                last_heartbeat = current_time
                print("💓 Sent heartbeat", flush=True)
            
            # Get next event (with timeout)
            try:
                event_dict = await asyncio.wait_for(
                    callback.events.get(),
                    timeout=1.0  # Check heartbeat every second
                )
                
                print(f"📤 SSE yielding: {event_dict.get('event', 'unknown')}", flush=True)
                logger.info(f"📤 SSE yielding: {event_dict.get('event', 'unknown')}")
                
                # Yield event dict (sse-starlette handles formatting)
                yield event_dict
                
                # Check if done
                if event_dict.get("event") == "done":
                    # Drain any remaining events that were queued before done
                    while not callback.events.empty():
                        try:
                            remaining = callback.events.get_nowait()
                            if remaining.get("event") != "done":
                                yield remaining
                        except asyncio.QueueEmpty:
                            break
                    print(f"✅ Stream completed in {elapsed:.1f}s", flush=True)
                    logger.info(f"✅ Stream completed in {elapsed:.1f}s")
                    break
                    
            except asyncio.TimeoutError:
                # No event available, continue to check heartbeat
                continue
                
    except asyncio.CancelledError:
        # Client disconnected
        logger.info("🔌 Client disconnected from stream")
        callback.close()
        raise
    except Exception as e:
        logger.error(f"❌ Stream error: {e}", exc_info=True)
        yield {"event": "error", "data": str(e)}
        yield {"event": "done", "data": ""}
    finally:
        callback.close()
        logger.info("🏁 SSE generator finished")


import re

# Patterns that indicate a chunk is technical/internal and should not be shown
_TECHNICAL_PATTERNS = re.compile(
    r'(?:invoke_\w+\s*[:=]|tool_name\s*[:=]|function_call\s*[:=]|'
    r'Calling\s+\w+\s+with|'
    r'LLAMADA\s+A\s+HERRAMIENTA|'
    r'\{["\'](?:base_imponible|formatted_response|query|tool)["\'])',
    re.IGNORECASE
)


def _is_technical_chunk(text: str) -> bool:
    """Check if a streaming chunk contains technical text that should be hidden."""
    return bool(_TECHNICAL_PATTERNS.search(text))


def filter_json_from_content(content: str) -> str:
    """
    Remove technical JSON artifacts from LLM responses.
    
    Filters out:
    - Tool call JSON like {"base_imponible":...}
    - formatted_response JSON objects
    - Internal reasoning JSON
    
    Args:
        content: Raw LLM response
        
    Returns:
        Cleaned content suitable for user display
    """
    import re

    # Remove ANY standalone JSON objects (handles 1-level nested braces):
    # {"call":"project_annual_irpf","args":{}} or {"base_imponible": 30000}
    content = re.sub(r'\{["\'][a-z_]+["\']:(?:[^{}]|\{[^{}]*\})*\}', '', content)

    # Remove JSON in code blocks
    content = re.sub(r'```json\s*\{[^`]+\}\s*```', '', content)

    # Remove technical key-value lines leaked from tool calls
    content = re.sub(r'^(?:invoke_\w+|tool_name|function_call|calling)\s*[:=]\s*\S+.*$', '', content, flags=re.MULTILINE | re.IGNORECASE)

    # Remove lines starting with "Calling " followed by a function name
    content = re.sub(r'^Calling\s+\w+\s+with.*$', '', content, flags=re.MULTILINE)

    # Remove Spanish internal reasoning / planning phrases (thinking leaked into content)
    # "Llamo a la herramienta de...", "Voy a usar/llamar/ejecutar...", "Utilizo la herramienta..."
    content = re.sub(
        r'(?:Llamo|Voy a (?:usar|llamar|ejecutar|utilizar|consultar)|Utilizo|Uso|Ejecuto|Consulto)'
        r'\s+(?:la |el |a la |al )?(?:herramienta|tool|función|cálculo|simulador|motor)\b[^.!?\n]*[.!?]?\s*',
        '', content, flags=re.IGNORECASE
    )
    # "Calcularé estimación para...", "Primero voy a analizar..."
    content = re.sub(
        r'(?:Calcular[eé]|Primero voy a|Ahora (?:hago|realizo|ejecuto|calculo|analizo))\b[^.!?\n]*[.!?]?\s*',
        '', content, flags=re.IGNORECASE
    )

    # Remove Spanish technical phrases about tool calls
    content = re.sub(r'\(?\s*(?:LLAMADA|llamada)\s+A\s+(?:HERRAMIENTA|herramienta)\s+\w+\s*\)?', '', content, flags=re.IGNORECASE)

    # Remove broken source lines: empty titles with just "(pág. N)"
    content = re.sub(r'^,?\s*\(p[aá]g\.\s*\d+\)\s*$', '', content, flags=re.MULTILINE)
    # Remove "Fuentes:" section if all sources are empty
    content = re.sub(r'^Fuentes:\s*\n(?:\s*,?\s*\(p[aá]g\.\s*\d+\)\s*\n?)+', '', content, flags=re.MULTILINE)

    # Clean up multiple newlines
    content = re.sub(r'\n{3,}', '\n\n', content)

    return content.strip()
