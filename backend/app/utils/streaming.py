"""
SSE Streaming Utilities for Chain-of-Thought UI

Provides Server-Sent Events streaming infrastructure for displaying
AI reasoning progress in real-time, ChatGPT/Claude style.
"""
import json
import time
import asyncio
import logging
from typing import AsyncGenerator, Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Railway SSE best practices
HEARTBEAT_INTERVAL = 30  # seconds - prevents 2min timeout on Railway
MAX_STREAM_DURATION = 240  # 4 minutes - well under Railway's 5min limit


@dataclass
class StreamEvent:
    """SSE event to send to client"""
    event: str
    data: Any
    
    def format(self) -> str:
        """Format as SSE message"""
        data_str = json.dumps(self.data) if not isinstance(self.data, str) else self.data
        return f"event: {self.event}\ndata: {data_str}\n\n"


class ProgressCallback:
    """
    Callback interface for streaming progress updates from AI processing.
    
    Used by TaxAgent to emit events during query processing.
    """
    
    def __init__(self):
        self.events: asyncio.Queue = asyncio.Queue()
        self._closed = False
    
    async def emit(self, event: str, data: Any):
        """Emit an event to the stream"""
        if not self._closed:
            await self.events.put(StreamEvent(event, data))
            logger.info(f"📤 Emitted event: {event}")
    
    async def thinking(self, message: str):
        """AI is thinking/reasoning"""
        await self.emit("thinking", message)
    
    async def tool_call(self, tool_name: str, args: Dict[str, Any]):
        """AI is calling a tool"""
        await self.emit("tool_call", {"tool": tool_name, "args": args})
    
    async def tool_result(self, tool_name: str, success: bool):
        """Tool execution completed"""
        await self.emit("tool_result", {"tool": tool_name, "success": success})
    
    async def content(self, text: str):
        """Stream final response content"""
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
) -> AsyncGenerator[str, None]:
    """
    Generate SSE events from a ProgressCallback.
    
    Implements Railway-compatible streaming with:
    - Heartbeat comments every 30s
    - Timeout protection
    - Graceful error handling
    
    Args:
        callback: Progress callback with event queue
        timeout: Maximum stream duration in seconds
        
    Yields:
        SSE-formatted strings
    """
    start_time = time.time()
    last_heartbeat = time.time()
    
    try:
        while True:
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > timeout:
                logger.warning(f"Stream timeout after {elapsed:.1f}s")
                yield StreamEvent("error", "Stream timeout").format()
                break
            
            # Send heartbeat if needed (Railway requirement)
            if time.time() - last_heartbeat > HEARTBEAT_INTERVAL:
                yield ": heartbeat\n\n"  # SSE comment (ignored by client)
                last_heartbeat = time.time()
                logger.debug("Sent heartbeat")
            
            # Get next event (with timeout)
            try:
                event = await asyncio.wait_for(
                    callback.events.get(),
                    timeout=1.0  # Check heartbeat every second
                )
                
                # Yield event
                yield event.format()
                
                # Check if done
                if event.event == "done":
                    logger.info(f"Stream completed in {elapsed:.1f}s")
                    break
                    
            except asyncio.TimeoutError:
                # No event available, continue to check heartbeat
                continue
                
    except asyncio.CancelledError:
        # Client disconnected
        logger.info("Client disconnected from stream")
        callback.close()
        raise
    except Exception as e:
        logger.error(f"Stream error: {e}", exc_info=True)
        yield StreamEvent("error", str(e)).format()
    finally:
        callback.close()


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
    
    # Clean up multiple newlines
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    return content.strip()
