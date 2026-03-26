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
import json

from app.database.turso_client import TursoClient
from app.agents.tax_agent import TaxAgent
from app.services.conversation_service import ConversationService
from app.services.conversation_cache import ConversationCache
from app.auth.jwt_handler import get_current_user, TokenData
from app.auth.subscription_guard import require_active_subscription
from app.security import sql_validator, guardrails_system
from app.security.content_restriction import detect_autonomo_query, get_autonomo_block_response
from app.services.subscription_service import SubscriptionAccess
from app.utils.streaming import ProgressCallback, sse_generator, filter_json_from_content


def _filter_permission_asking(content: str) -> str:
    """Filter LLM responses that ask permission instead of answering."""
    if not content or len(content.strip()) < 20:
        return content
    content_lower = content.lower()
    permission_patterns = [
        "te digo lo que encuentre",
        "¿de acuerdo?",
        "¿quieres que busque",
        "¿te parece",
        "si el catálogo oficial no carga",
        "¿deseas que",
        "¿procedo a",
        "voy a intentar",
        "déjame ver si",
    ]
    if any(p in content_lower for p in permission_patterns):
        return (
            "No he encontrado datos específicos en mis fuentes para tu consulta exacta, "
            "pero puedo orientarte con mi conocimiento de la normativa fiscal española.\n\n"
            "Para consultas sobre epígrafes IAE, modelos tributarios o normativa específica, "
            "te recomiendo consultar directamente:\n"
            "- **AEAT**: sede.agenciatributaria.gob.es\n"
            "- **Hacienda Foral de Bizkaia**: web.bizkaia.eus/es/hacienda\n"
            "- **Hacienda Foral de Gipuzkoa**: www.gipuzkoa.eus/es/hacienda\n"
            "- **Hacienda Foral de Araba**: web.araba.eus/es/hacienda\n"
            "- **Hacienda Foral de Navarra**: hacienda.navarra.es\n\n"
            "Si me das más contexto sobre tu actividad, puedo ayudarte a identificar el epígrafe más probable."
        )
    return content
from app.utils.followup_detector import classify_followup
from app.utils.query_contextualizer import contextualize_query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat-streaming"])


# === Models ===

class StreamQuestionRequest(BaseModel):
    """Request for streaming chat"""
    question: str = Field(..., min_length=1, max_length=1000)
    conversation_id: Optional[str] = None
    workspace_id: Optional[str] = Field(default=None, description="Active workspace ID for context")
    session_doc_ids: Optional[list] = Field(default=None, description="Session document IDs for ephemeral context")
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
    current_user: TokenData = Depends(get_current_user),
    access: SubscriptionAccess = Depends(require_active_subscription)
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
    
    # === CONTENT RESTRICTION: Autonomo detection (only block "particular" plan) ===
    if not access.is_owner and access.plan_type not in ("autonomo", "creator") and detect_autonomo_query(request.question):
        async def autonomo_block_stream():
            yield {"event": "content", "data": get_autonomo_block_response()}
            yield {"event": "done", "data": ""}
        return EventSourceResponse(autonomo_block_stream())

    # === Conversation setup ===
    conv_service = ConversationService(db)
    conversation_id = request.conversation_id
    
    if not conversation_id:
        logger.info("Creating new conversation (no ID provided)")
        conversation = await conv_service.create_conversation(
            user_id=current_user.user_id,
            title=request.question[:50] + "..." if len(request.question) > 50 else request.question
        )
        conversation_id = conversation["id"]
    else:
        logger.info(f"Checking for existing conversation: {conversation_id}")
        conversation = await conv_service.get_conversation(conversation_id, current_user.user_id)
        if not conversation:
            logger.warning(f"Conversation {conversation_id} not found, creating new one")
            # Create a new conversation (can't use specific ID)
            conversation = await conv_service.create_conversation(
                user_id=current_user.user_id,
                title=request.question[:50] + "..." if len(request.question) > 50 else request.question
            )
            # Update the conversation_id to the newly created one
            conversation_id = conversation["id"]
            logger.info(f"Created new conversation with ID: {conversation_id}")
    
    # === Greeting detection (fast path) ===
    if guardrails_system.is_greeting(request.question.strip()):
        async def greeting_stream():
            greeting = (
                "¡Hola! 👋 Soy Impuestify, tu asistente fiscal.\n\n"
                "¿En qué puedo ayudarte hoy?"
            )
            yield {"event": "content", "data": greeting}
            yield {"event": "done", "data": json.dumps({"conversation_id": conversation_id})}

        return EventSourceResponse(greeting_stream())
    
    # === Main streaming logic ===
    async def event_stream():
        print("🎬 event_stream() STARTED", flush=True)
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

            # === Load workspace context if workspace_id provided ===
            workspace_context = ""
            workspace_files_info = []
            if request.workspace_id:
                logger.info(f"Loading workspace context for: {request.workspace_id}")
                try:
                    # Verify workspace ownership
                    ws_result = await db.execute(
                        "SELECT id, name FROM workspaces WHERE id = ? AND user_id = ?",
                        [request.workspace_id, current_user.user_id]
                    )
                    if ws_result.rows:
                        # Load workspace files with extracted text
                        files_result = await db.execute(
                            """
                            SELECT filename, file_type, extracted_text
                            FROM workspace_files
                            WHERE workspace_id = ? AND processing_status = 'completed'
                            """,
                            [request.workspace_id]
                        )

                        if files_result.rows:
                            from app.services.payslip_extractor import PayslipExtractor
                            docs_context = []
                            for f in files_result.rows:
                                if f.get("extracted_text"):
                                    raw_text = f['extracted_text'][:5000]
                                    # SECURITY: Anonymize PII before passing to LLM
                                    if f.get('file_type') in ('nomina', 'payslip', 'factura', 'declaracion'):
                                        raw_text = PayslipExtractor.anonymize_text(raw_text)
                                    doc_info = f"--- {f['filename']} ({f['file_type']}) ---\n{raw_text}"
                                    docs_context.append(doc_info)
                                    workspace_files_info.append({
                                        "filename": f["filename"],
                                        "file_type": f["file_type"]
                                    })

                            if docs_context:
                                workspace_context = "\n\n".join(docs_context)
                                logger.info(f"Loaded {len(docs_context)} documents from workspace (PII anonymized)")
                except Exception as e:
                    logger.error(f"Error loading workspace context: {e}")

            # === Load session documents context (ephemeral, Redis-cached) ===
            session_docs_context = ""
            if request.session_doc_ids:
                try:
                    for doc_id in request.session_doc_ids[:5]:
                        cache_key = f"session_doc:{current_user.user_id}:{doc_id}"
                        raw = await upstash_client.get(cache_key) if upstash_client else None
                        if raw:
                            doc_data = json.loads(raw)
                            fname = doc_data.get("filename", "documento")
                            ftype = doc_data.get("file_type", "otro")
                            structured = doc_data.get("extracted_data", {})

                            session_docs_context += f"\n--- {fname} ({ftype}) ---\n"

                            # Prefer structured data (PayslipExtractor/InvoiceExtractor output)
                            if structured:
                                session_docs_context += "DATOS EXTRAIDOS:\n"
                                for key, val in structured.items():
                                    if key in ("full_text", "file_hash", "extraction_status"):
                                        continue
                                    label = key.replace("_", " ").capitalize()
                                    session_docs_context += f"  {label}: {val}\n"

                            # Also include raw text (truncated) for context the extractor may have missed
                            text = doc_data.get("extracted_text", "")[:3000]
                            if text:
                                session_docs_context += f"\nTEXTO DEL DOCUMENTO:\n{text}\n"

                    if session_docs_context:
                        logger.info(f"Loaded {len(request.session_doc_ids)} session docs for context")
                except Exception as e:
                    logger.warning(f"Error loading session docs: {e}")

            # === Follow-up detection & RAG optimization ===
            followup_type = classify_followup(request.question, conversation_history)
            cached_rag_chunks = cached_context.get("last_rag_chunks", []) if cached_context else []
            cached_rag_query = cached_context.get("last_rag_query", "") if cached_context else ""

            relevant_chunks = []
            rag_query_used = request.question  # Track which query was sent to RAG

            if followup_type == "clarification" and cached_rag_chunks:
                # SKIP RAG — reuse cached chunks from previous turn
                relevant_chunks = cached_rag_chunks
                rag_query_used = cached_rag_query
                print(f"⚡ RAG SKIP (clarification) — reusing {len(relevant_chunks)} cached chunks", flush=True)
                logger.info(f"⚡ RAG SKIP (clarification) — reusing {len(relevant_chunks)} cached chunks")
            else:
                # Run RAG (normal or with expanded query)
                if followup_type == "modification":
                    rag_query_used = contextualize_query(
                        request.question, conversation_history, cached_rag_query
                    )
                    print(f"🔀 RAG CONTEXTUALIZED: '{request.question}' → '{rag_query_used}'", flush=True)
                    logger.info(f"🔀 RAG CONTEXTUALIZED: '{request.question}' → '{rag_query_used}'")

                from app.utils.hybrid_retriever import HybridRetriever, get_query_embedding
                retriever = HybridRetriever(db_client=db)
                query_embedding = await get_query_embedding(rag_query_used)

                # Territory filter: prioritize docs matching user's CCAA
                ccaa_for_rag = None
                try:
                    fp_rag_result = await db.execute(
                        "SELECT ccaa_residencia FROM user_profiles WHERE user_id = ?",
                        [current_user.user_id]
                    )
                    if fp_rag_result.rows and fp_rag_result.rows[0].get("ccaa_residencia"):
                        ccaa_for_rag = fp_rag_result.rows[0]["ccaa_residencia"]
                except Exception as _rag_ccaa_err:
                    logger.debug(f"Could not pre-fetch CCAA for RAG filter: {_rag_ccaa_err}")

                relevant_chunks = await retriever.search(
                    query=rag_query_used,
                    query_embedding=query_embedding,
                    k=request.k or 5,
                    territory_filter=ccaa_for_rag,
                )

            # Prepare context - ALLOW empty RAG if we have conversation history or user memory
            if relevant_chunks:
                # Filter out chunks with missing metadata (page=0, empty title)
                # These produce broken "(pág. 0)" sources in the response
                valid_chunks = [
                    c for c in relevant_chunks
                    if c.get('title') and c.get('page', 0) > 0
                ]
                rag_context = "\n\n".join([
                    f"Fuente: {chunk['title']} (Página {chunk['page']})\n{chunk['text']}"
                    for chunk in valid_chunks
                ])
                sources_data = [
                    {
                        "id": chunk['id'],
                        "source": chunk['source'],
                        "page": chunk['page'],
                        "title": chunk['title'],
                        "score": chunk['similarity']
                    }
                    for chunk in valid_chunks
                ]
                logger.info(f"Using {len(relevant_chunks)} RAG chunks for context")
            else:
                has_internal_context = bool(conversation_history)
                if not has_internal_context:
                    logger.info("No RAG chunks and no conversation history - will attempt general answer")
                else:
                    logger.info(f"No RAG chunks but have {len(conversation_history)} conversation messages - will use memory")
                rag_context = ""
                sources_data = []

            combined_context = notification_context + rag_context if notification_context else rag_context
            if session_docs_context:
                combined_context = session_docs_context + "\n\n" + combined_context

            # Format conversation history
            formatted_history = [
                {"role": msg.get("role"), "content": msg.get("content")}
                for msg in conversation_history[-10:]
            ]

            # === Choose agent based on context ===
            use_workspace_agent = bool(workspace_context or session_docs_context)

            # === Load fiscal profile for personalized agent responses ===
            fiscal_profile = {}
            try:
                fp_result = await db.execute(
                    "SELECT datos_fiscales, ccaa_residencia, situacion_laboral "
                    "FROM user_profiles WHERE user_id = ?",
                    [current_user.user_id]
                )
                if fp_result.rows:
                    row = fp_result.rows[0]
                    raw = row.get("datos_fiscales")
                    if raw:
                        datos = json.loads(raw) if isinstance(raw, str) else raw
                        # Extract plain values from {value, _source, _updated} wrappers
                        for k, v in datos.items():
                            if k.startswith("_"):
                                continue
                            fiscal_profile[k] = v["value"] if isinstance(v, dict) and "value" in v else v
                    if row.get("ccaa_residencia"):
                        fiscal_profile["ccaa_residencia"] = row["ccaa_residencia"]
                    if row.get("situacion_laboral"):
                        fiscal_profile["situacion_laboral"] = row["situacion_laboral"]
            except Exception as e:
                logger.warning(f"Error loading fiscal profile: {e}")

            # Create async task for agent execution
            async def run_agent():
                done_emitted = False
                try:
                    restricted_mode = not access.is_owner and access.plan_type not in ("autonomo", "creator")

                    if use_workspace_agent:
                        # Use WorkspaceAgent for workspace/session-doc queries
                        from app.agents.workspace_agent import get_workspace_agent
                        agent = get_workspace_agent()
                        # Combine workspace + session docs context
                        agent_doc_context = workspace_context or ""
                        if session_docs_context:
                            agent_doc_context = (agent_doc_context + "\n\n" + session_docs_context).strip()
                        response = await agent.run(
                            query=request.question,
                            context=agent_doc_context,
                            rag_context=rag_context,
                            sources=sources_data,
                            conversation_history=formatted_history,
                            user_id=current_user.user_id,
                            workspace_id=request.workspace_id,
                            progress_callback=callback,
                            restricted_mode=restricted_mode,
                            fiscal_profile=fiscal_profile
                        )
                    else:
                        # Use TaxAgent for general tax queries
                        tax_agent = TaxAgent()
                        response = await tax_agent.run(
                            query=request.question,
                            context=combined_context,
                            sources=sources_data,
                            conversation_history=formatted_history,
                            use_tools=True,
                            user_id=current_user.user_id,
                            progress_callback=callback,
                            db_client=db,  # Pass database client for user memory
                            restricted_mode=restricted_mode,
                            fiscal_profile=fiscal_profile
                        )
                    
                    # Filter JSON from final content
                    clean_content = filter_json_from_content(response.content)

                    # Filter permission-asking / internal reasoning from LLM
                    clean_content = _filter_permission_asking(clean_content)

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
                    
                    # Update cache (include RAG chunks for follow-up optimization)
                    updated_history = await conv_service.get_recent_messages(conversation_id, limit=20)
                    await cache.set_context(conversation_id, {
                        "notification_content": notification_context,
                        "recent_messages": updated_history,
                        "last_rag_chunks": relevant_chunks[:5],
                        "last_rag_query": rag_query_used,
                    })
                    
                    await callback.done(conversation_id=conversation_id)
                    done_emitted = True
                    
                except Exception as e:
                    logger.error(f"Agent error: {e}", exc_info=True)
                    await callback.error(f"Error procesando la consulta: {str(e)}")
                    await callback.done(conversation_id=conversation_id)
                    done_emitted = True
                finally:
                    # CRITICAL: Ensure done is ALWAYS emitted, even if something went wrong above
                    if not done_emitted:
                        logger.warning("Emitting done event in finally block (safety net)")
                        try:
                            await callback.done(conversation_id=conversation_id)
                        except Exception as e:
                            logger.error(f"Failed to emit done in finally: {e}")
            
            # Start agent task
            agent_task = asyncio.create_task(run_agent())
            
            # Stream events from callback with heartbeats (Railway best practice)
            async for event_dict in sse_generator(callback):
                # Check if client disconnected (save resources)
                if await req.is_disconnected():
                    logger.info("Client disconnected mid-stream")
                    agent_task.cancel()
                    callback.close()
                    break
                
                yield event_dict
            
            # Wait for agent to finish
            await agent_task
            
        except asyncio.CancelledError:
            logger.info("Stream cancelled by client")
            callback.close()
        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            yield {"event": "error", "data": str(e)}
            yield {"event": "done", "data": ""}
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
