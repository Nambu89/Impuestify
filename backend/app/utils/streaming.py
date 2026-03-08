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
    "simulate_irpf": ("Simulando tu IRPF", "Simulación de IRPF completada"),
    "calculate_irpf": ("Calculando tramos IRPF", "Cálculo de tramos completado"),
    "calculate_autonomous_quota": ("Calculando cuota de autónomo", "Cuota de autónomo calculada"),
    "calculate_modelo_303": ("Calculando Modelo 303 (IVA)", "Modelo 303 calculado"),
    "calculate_modelo_130": ("Calculando Modelo 130 (IRPF)", "Modelo 130 calculado"),
    "discover_deductions": ("Buscando deducciones aplicables", "Deducciones encontradas"),
    "search_tax_regulations": ("Consultando normativa fiscal", "Normativa consultada"),
    "analyze_payslip": ("Analizando tu nómina", "Nómina analizada"),
    "web_scraper": ("Consultando fuentes oficiales", "Fuentes consultadas"),
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
        await self.emit("content_chunk", text)

    async def content(self, text: str):
        """Stream final response content (full replacement)"""
        await self.emit("content", text)

    async def error(self, message: str):
        """An error occurred"""
        await self.emit("error", message)

    async def done(self):
        """Processing complete"""
        await self.emit("done", "")
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
    
    # Remove standalone JSON objects (common in tool responses)
    # Matches: {"key": "value", ...}
    content = re.sub(r'\{["\'](?:base_imponible|formatted_response|query|tool)["\']:[^}]+\}', '', content)

    # Remove JSON in code blocks
    content = re.sub(r'```json\s*\{[^`]+\}\s*```', '', content)

    # Remove technical key-value lines leaked from tool calls
    # e.g. "invoke_calculate_irpf_used: true", "tool_name: calculate_irpf"
    content = re.sub(r'^(?:invoke_\w+|tool_name|function_call|calling)\s*[:=]\s*\S+.*$', '', content, flags=re.MULTILINE | re.IGNORECASE)

    # Remove lines starting with "Calling " followed by a function name
    content = re.sub(r'^Calling\s+\w+\s+with.*$', '', content, flags=re.MULTILINE)

    # Clean up multiple newlines
    content = re.sub(r'\n{3,}', '\n\n', content)

    return content.strip()
