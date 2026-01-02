"""
SSE Streaming Chat Router

Implements Server-Sent Events streaming for real-time AI responses.
Best practices from research applied:
- sse-starlette for robust SSE handling
- Railway-compatible heartbeats
- Client disconnection detection
- Graceful error handling
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel, Field
from typing import Optional
import logging
import asyncio

from app.database.turso_client import TursoClient
from app.agents.tax_agent import TaxAgent
from app.services.conversation_service import ConversationService
from app.services.conversation_cache import ConversationCache  
from app.auth.jwt_handler import get_current_user, TokenData
from app.security import sql_validator, guardrails_system
from app.utils.streaming import ProgressCallback, sse_generator, filter_json_from_content

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat-streaming"])


# === Models ===

class StreamQuestionRequest(BaseModel):
    """Request for streaming chat"""
    question: str = Field(..., min_length=3, max_length=1000)
    conversation_id: Optional[str] = None
    k: Optional[int] = Field(default=5, ge=1, le=10)


# === Dependencies ===

async def get_db(request: Request) -> TursoClient:
    """Get database client"""
    if hasattr(request.app.state, 'db_client') and request.app.state.db_client:
        return request.app.state.db_client
    raise HTTPException(status_code=503, detail="Database not connected")


# === Routes ===

@router.post("/ask/stream")
async def ask_question_stream(
    req: Request,
    request: StreamQuestionRequest,
    db: TursoClient = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Stream AI responses with chain-of-thought display.
    
    Returns Server-Sent Events with:
    - thinking: AI reasoning steps
    - tool_call: Tool execution events
    - tool_result: Tool completion
    - content: Final response text
    - done: Stream complete
    - error: Error occurred
    
    Compatible with Railway's timeout limits via heartbeats.
    """
    
    # === SECURITY: Input validation ===
    sql_check = sql_validator.validate_user_input(request.question)
    if not sql_check.is_safe:
        raise HTTPException(
            status_code=400,
            detail={"error": "Security violation", "type": "sql_injection"}
        )
    
    guardrails_check = guardrails_system.validate_input(request.question)
    if not guardrails_check.is_safe and guardrails_check.risk_level == "critical":
        raise HTTPException(
            status_code=400,
            detail={"error": "Question violates safety guidelines"}
        )
    
    # === Conversation setup ===
    conv_service = ConversationService(db)
    conversation_id = request.conversation_id
    
    if not conversation_id:
        conversation = await conv_service.create_conversation(
            user_id=current_user.user_id,
            title=request.question[:50] + "..." if len(request.question) > 50 else request.question
        )
        conversation_id = conversation["id"]
    else:
        conversation = await conv_service.get_conversation(conversation_id, current_user.user_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    
    # === Greeting detection (fast path) ===
    if guardrails_system.is_greeting(request.question.strip()):
        async def greeting_stream():
            greeting = (
                "¡Hola! 👋 Soy Impuestify, tu asistente fiscal.\\n\\n"
                "¿En qué puedo ayudarte hoy?"
            )
            yield {"event": "content", "data": greeting}
            yield {"event": "done", "data": ""}
        
        return EventSourceResponse(greeting_stream())
    
    # === Main streaming logic ===
    async def event_stream():
        callback = ProgressCallback()
        
        try:
            # Check if client is still connected (Railway best practice)
            if await req.is_disconnected():
                logger.info("Client disconnected before processing")
                callback.close()
                return
            
            # Load conversation history (cache-first)
            upstash_client = getattr(req.app.state, 'upstash_client', None)
            cache = ConversationCache(upstash_client)
            cached_context = await cache.get_context(conversation_id)
            
            conversation_history = []
            notification_context = ""
            
            if cached_context:
                conversation_history = cached_context.get("recent_messages", [])
                notification_context = cached_context.get("notification_content", "")
                await cache.refresh_ttl(conversation_id)
            else:
                conversation_history = await conv_service.get_recent_messages(conversation_id, limit=20)
            
            # Search relevant documents
            from app.routers.chat import fts_search  # Import helper
            relevant_chunks = await fts_search(db, request.question, k=request.k or 5)
            
            if not relevant_chunks:
                await callback.error("No encontré información relevante en la documentación")
                await callback.done()
                return
            
            # Prepare context
            rag_context = "\\n\\n".join([
                f"Fuente: {chunk['title']} (Página {chunk['page']})\\n{chunk['text']}"
                for chunk in relevant_chunks
            ])
            combined_context = notification_context + rag_context if notification_context else rag_context
            
            # Prepare sources
            sources_data = [
                {
                    "id": chunk['id'],
                    "source": chunk['source'],
                    "page": chunk['page'],
                    "title": chunk['title'],
                    "score": chunk['similarity']
                }
                for chunk in relevant_chunks
            ]
            
            # Format conversation history
            formatted_history = [
                {"role": msg.get("role"), "content": msg.get("content")}
                for msg in conversation_history[-10:]
            ]
            
            # Run TaxAgent with streaming callback
            tax_agent = TaxAgent()
            
            # Create async task for agent execution
            async def run_agent():
                try:
                    response = await tax_agent.run(
                        query=request.question,
                        context=combined_context,
                        sources=sources_data,
                        conversation_history=formatted_history,
                        use_tools=True,
                        user_id=current_user.user_id,
                        progress_callback=callback  # ← Enable streaming
                    )
                    
                    # Filter JSON from final content
                    clean_content = filter_json_from_content(response.content)
                    
                    # Stream final content
                    await callback.content(clean_content)
                    
                    # Save messages to database
                    await conv_service.add_message(conversation_id, "user", request.question)
                    assistant_msg = await conv_service.add_message(
                        conversation_id, 
                        "assistant", 
                        clean_content,
                        metadata={"sources": sources_data}
                    )
                    await conv_service.add_message_sources(assistant_msg["id"], sources_data)
                    
                    # Update cache
                    updated_history = await conv_service.get_recent_messages(conversation_id, limit=20)
                    await cache.set_context(conversation_id, {
                        "notification_content": notification_context,
                        "recent_messages": updated_history
                    })
                    
                    await callback.done()
                    
                except Exception as e:
                    logger.error(f"Agent error: {e}", exc_info=True)
                    await callback.error(f"Error procesando la consulta: {str(e)}")
                    await callback.done()
            
            # Start agent task
            agent_task = asyncio.create_task(run_agent())
            
            # Stream events from callback with heartbeats (Railway best practice)
            async for event_str in sse_generator(callback):
                # Check if client disconnected (save resources)
                if await req.is_disconnected():
                    logger.info("Client disconnected mid-stream")
                    agent_task.cancel()
                    callback.close()
                    break
                
                yield event_str
            
            # Wait for agent to finish
            await agent_task
            
        except asyncio.CancelledError:
            logger.info("Stream cancelled by client")
            callback.close()
        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            yield f"event: error\\ndata: {str(e)}\\n\\n"
            yield "event: done\\ndata: \\n\\n"
        finally:
            callback.close()
    
    # Return SSE response (sse-starlette handles formatting)
    return EventSourceResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
