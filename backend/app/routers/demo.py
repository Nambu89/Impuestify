"""
Demo Chat Router for Impuestify

Public demo endpoint with:
- No authentication required
- Aggressive rate limiting (10 req/min per IP)
- Limited context (stateless)
- Truncated responses
- Watermark for demo version
- FULL SECURITY: SQL injection, guardrails, prompt injection, PII, Llama Guard
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List, Optional
import time
import logging
import asyncio
from collections import defaultdict
from datetime import datetime, timedelta

from app.database.turso_client import TursoClient
from app.config import settings
# Import ALL security modules
from app.security import (
    sql_validator, 
    guardrails_system,
    prompt_injection_filter,
    pii_detector,
    audit_logger,
    AuditEventType
)
from app.security.llama_guard import get_llama_guard
from app.metrics import record_demo_request, record_security_block, record_rag_search, record_llm_latency

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/demo", tags=["demo"])


# === Rate Limiting ===

class RateLimiter:
    """Simple in-memory rate limiter by IP"""
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)  # IP -> [timestamps]
    
    def is_allowed(self, ip: str) -> tuple[bool, int]:
        """
        Check if request is allowed.
        Returns (allowed, seconds_until_reset)
        """
        now = datetime.now()
        window_start = now - timedelta(seconds=self.window_seconds)
        
        # Clean old requests
        self.requests[ip] = [
            ts for ts in self.requests[ip] 
            if ts > window_start
        ]
        
        if len(self.requests[ip]) >= self.max_requests:
            # Calculate time until oldest request expires
            oldest = min(self.requests[ip])
            reset_in = int((oldest + timedelta(seconds=self.window_seconds) - now).total_seconds())
            return False, max(1, reset_in)
        
        # Allow and record
        self.requests[ip].append(now)
        return True, 0
    
    def get_remaining(self, ip: str) -> int:
        """Get remaining requests in current window"""
        now = datetime.now()
        window_start = now - timedelta(seconds=self.window_seconds)
        
        self.requests[ip] = [
            ts for ts in self.requests[ip] 
            if ts > window_start
        ]
        
        return max(0, self.max_requests - len(self.requests[ip]))


# Global rate limiter instance
demo_rate_limiter = RateLimiter(max_requests=10, window_seconds=60)

# Demo usage counter (simple analytics without PII)
demo_stats = {
    "total_requests": 0,
    "total_errors": 0,
    "started_at": datetime.now().isoformat()
}


# === Models ===

class DemoChatRequest(BaseModel):
    """Demo chat request - limited input"""
    question: str = Field(
        ..., 
        min_length=3, 
        max_length=500,
        description="Pregunta fiscal (máx 500 caracteres)"
    )


class DemoSource(BaseModel):
    """Simplified source for demo"""
    title: str
    page: int


class DemoChatResponse(BaseModel):
    """Demo chat response"""
    response: str
    sources: List[DemoSource]
    demo: bool = True
    remaining_requests: int
    processing_time: float


# === Dependencies ===

async def get_db(request: Request) -> TursoClient:
    """Get database client from app state"""
    if hasattr(request.app.state, 'db_client') and request.app.state.db_client:
        return request.app.state.db_client
    raise HTTPException(
        status_code=503,
        detail="Database not available"
    )


def get_client_ip(request: Request) -> str:
    """Extract client IP from request"""
    # Check X-Forwarded-For header (for proxies/Railway)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    # Check X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to direct client
    return request.client.host if request.client else "unknown"


# === Helper Functions ===

async def demo_fts_search(db: TursoClient, query: str, k: int = 3) -> List[dict]:
    """
    Simplified FTS search for demo (limited results).
    """
    try:
        # Clean query
        clean_query = ''.join(c for c in query if c.isalnum() or c.isspace())
        keywords = clean_query.split()[:5]  # Max 5 keywords
        
        if not keywords:
            return []
        
        # Simple OR query
        fts_query = ' OR '.join([f'"{kw}"' for kw in keywords])
        
        # Exclude foral regions for simplicity in demo
        sql = """
        SELECT 
            c.id,
            c.content,
            c.page_number,
            d.filename,
            d.title
        FROM document_chunks_fts fts
        JOIN document_chunks c ON c.id = fts.chunk_id
        JOIN documents d ON d.id = c.document_id
        WHERE document_chunks_fts MATCH ? 
        AND LOWER(d.filename) NOT LIKE '%navarra%'
        AND LOWER(d.filename) NOT LIKE '%bizkaia%'
        ORDER BY fts.rank 
        LIMIT ?
        """
        
        result = await db.execute(sql, [fts_query, k])
        
        chunks = []
        for row in result.rows:
            chunks.append({
                "id": row['id'],
                "text": row['content'][:1500],  # Limit text size
                "page": row['page_number'],
                "source": row['filename'],
                "title": row['title'] or row['filename']
            })
        
        return chunks
        
    except Exception as e:
        logger.error(f"Demo FTS search error: {e}")
        return []


async def generate_demo_response(
    question: str, 
    context: str, 
    timeout: float = 30.0
) -> str:
    """
    Generate response using GPT-4o-mini (cheaper model for demo).
    """
    import httpx
    
    system_prompt = """Eres Impuestify, un asistente fiscal español especializado.

REGLAS PARA DEMO:
- Respuestas CONCISAS (máximo 2-3 párrafos)
- Usa SOLO la información del contexto proporcionado
- Si no encuentras información relevante, indícalo claramente
- Responde SIEMPRE en español
- No inventes datos fiscales
- Menciona siempre que esto es orientativo y se debe consultar con un profesional"""

    user_prompt = f"""CONTEXTO DOCUMENTAL:
{context}

PREGUNTA DEL USUARIO:
{question}

Responde de forma concisa y profesional:"""

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-mini",  # Cheaper model for demo
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "max_tokens": 400,  # Limit output tokens
                    "temperature": 0.3
                }
            )
            
            if response.status_code != 200:
                logger.error(f"OpenAI error: {response.text}")
                raise HTTPException(status_code=502, detail="Error generating response")
            
            data = response.json()
            return data["choices"][0]["message"]["content"]
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Response timeout - try a simpler question")
    except Exception as e:
        logger.error(f"Demo generation error: {e}")
        raise HTTPException(status_code=500, detail="Error processing question")


def truncate_response(text: str, max_chars: int = 800) -> str:
    """Truncate response to max characters, ending at sentence boundary."""
    if len(text) <= max_chars:
        return text
    
    # Find last sentence boundary before limit
    truncated = text[:max_chars]
    
    # Try to end at a sentence
    for end_char in ['. ', '.\n', '? ', '?\n', '! ', '!\n']:
        last_pos = truncated.rfind(end_char)
        if last_pos > max_chars // 2:
            return truncated[:last_pos + 1] + "..."
    
    # Fallback: end at word boundary
    last_space = truncated.rfind(' ')
    if last_space > max_chars // 2:
        return truncated[:last_space] + "..."
    
    return truncated + "..."


def add_demo_watermark(text: str) -> str:
    """Add demo watermark to response."""
    watermark = "\n\n---\n💡 *Demo limitado - Accede a la versión completa en [impuestify.com](https://impuestify.com)*"
    return text + watermark


# === Routes ===

@router.post("/chat", response_model=DemoChatResponse)
async def demo_chat(
    request: Request,
    body: DemoChatRequest
):
    """
    Demo chat endpoint - No authentication required.
    
    **Limitaciones:**
    - 10 requests/minuto por IP
    - Respuestas máximo 800 caracteres
    - Sin memoria de conversación
    - Máximo 3 fuentes
    
    **Uso:**
    ```
    POST /api/demo/chat
    {
        "question": "¿Cuándo se presenta el IVA trimestral?"
    }
    ```
    """
    start_time = time.time()
    demo_stats["total_requests"] += 1
    
    # === Rate Limiting ===
    client_ip = get_client_ip(request)
    allowed, reset_in = demo_rate_limiter.is_allowed(client_ip)
    
    if not allowed:
        logger.warning(f"Demo rate limit exceeded for IP: {client_ip[:10]}...")
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Demo limit alcanzado",
                "message": f"Espera {reset_in} segundos o contacta para acceso completo",
                "retry_after": reset_in
            },
            headers={"Retry-After": str(reset_in)}
        )
    
    remaining = demo_rate_limiter.get_remaining(client_ip)
    
    # === SECURITY LAYER 1: SQL Injection Detection ===
    sql_check = sql_validator.validate_user_input(body.question)
    if not sql_check.is_safe:
        logger.warning(f"🚨 Demo SQL injection attempt blocked: {sql_check.violations}")
        demo_stats["total_errors"] += 1
        audit_logger.log_security_event(
            event_type=AuditEventType.SECURITY_VIOLATION,
            details={"type": "sql_injection", "ip": client_ip[:10]},
            user_id="demo"
        )
        raise HTTPException(status_code=400, detail="Invalid input detected")
    
    # === SECURITY LAYER 2: Prompt Injection Detection ===
    injection_check = prompt_injection_filter.check(body.question)
    if not injection_check.is_safe:
        logger.warning(f"🚨 Demo prompt injection attempt blocked: {injection_check.detected_patterns}")
        demo_stats["total_errors"] += 1
        audit_logger.log_security_event(
            event_type=AuditEventType.SECURITY_VIOLATION,
            details={"type": "prompt_injection", "ip": client_ip[:10]},
            user_id="demo"
        )
        raise HTTPException(status_code=400, detail="Invalid input detected")
    
    # === SECURITY LAYER 3: Guardrails Validation ===
    guardrails_check = guardrails_system.validate_input(body.question)
    if not guardrails_check.is_safe and guardrails_check.risk_level == "critical":
        logger.warning(f"⚠️ Demo guardrails violation: {guardrails_check.violations}")
        demo_stats["total_errors"] += 1
        raise HTTPException(status_code=400, detail="Question violates guidelines")
    
    # === SECURITY LAYER 4: PII Detection (redact but don't block) ===
    pii_result = pii_detector.detect(body.question)
    sanitized_question = body.question
    if pii_result.has_pii:
        logger.info(f"🔒 Demo PII detected and redacted: {pii_result.pii_types}")
        sanitized_question = pii_result.redacted_text
    
    # === SECURITY LAYER 5: Llama Guard Content Moderation ===
    try:
        llama_guard = get_llama_guard()
        if llama_guard:
            moderation = await llama_guard.moderate(body.question)
            if not moderation.is_safe:
                logger.warning(f"🛡️ Demo Llama Guard blocked: {moderation.categories}")
                demo_stats["total_errors"] += 1
                audit_logger.log_security_event(
                    event_type=AuditEventType.SECURITY_VIOLATION,
                    details={"type": "llama_guard", "categories": moderation.categories, "ip": client_ip[:10]},
                    user_id="demo"
                )
                raise HTTPException(status_code=400, detail="Content violates safety guidelines")
    except Exception as e:
        # Don't block if Llama Guard fails, just log
        logger.warning(f"Llama Guard check failed (non-blocking): {e}")
    
    # === Greeting Detection ===
    if guardrails_system.is_greeting(body.question.strip()):
        greeting = (
            "¡Hola! 👋 Soy Impuestify, tu asistente fiscal. "
            "Pregúntame sobre IRPF, IVA, deducciones o cualquier tema fiscal español."
        )
        return DemoChatResponse(
            response=add_demo_watermark(greeting),
            sources=[],
            demo=True,
            remaining_requests=remaining,
            processing_time=time.time() - start_time
        )
    
    # === Get Database ===
    db = await get_db(request)
    
    # === Search Documents (limited) ===
    chunks = await demo_fts_search(db, body.question, k=3)
    
    if not chunks:
        no_info = (
            "No encontré información específica sobre tu pregunta en la documentación fiscal. "
            "Intenta reformular tu consulta o pregunta sobre temas como IRPF, IVA, "
            "deducciones, modelos tributarios o autónomos."
        )
        return DemoChatResponse(
            response=add_demo_watermark(no_info),
            sources=[],
            demo=True,
            remaining_requests=remaining,
            processing_time=time.time() - start_time
        )
    
    # === Prepare Context ===
    context = "\n\n".join([
        f"[{chunk['title']} - Página {chunk['page']}]\n{chunk['text']}"
        for chunk in chunks
    ])
    
    # === Generate Response (with timeout) ===
    try:
        raw_response = await asyncio.wait_for(
            generate_demo_response(body.question, context),
            timeout=30.0
        )
    except asyncio.TimeoutError:
        demo_stats["total_errors"] += 1
        raise HTTPException(
            status_code=504,
            detail="Tiempo de respuesta agotado. Intenta con una pregunta más simple."
        )
    
    # === Post-process Response ===
    # Truncate to max length
    truncated = truncate_response(raw_response, max_chars=800)
    
    # === SECURITY LAYER 6: Output Validation ===
    output_check = guardrails_system.validate_output(
        llm_response=truncated,
        user_question=sanitized_question,
        sources=[]  # Simplified for demo
    )
    if not output_check.is_safe:
        logger.warning(f"⚠️ Demo output guardrail violation: {output_check.violations}")
        truncated = guardrails_system.apply_safety_wrapper(
            truncated,
            risk_level=output_check.risk_level
        )
    
    # Add watermark
    final_response = add_demo_watermark(truncated)
    
    # === Format Sources (max 3) ===
    sources = [
        DemoSource(title=chunk['title'], page=chunk['page'])
        for chunk in chunks[:3]
    ]
    
    processing_time = time.time() - start_time
    logger.info(f"Demo request processed in {processing_time:.2f}s")
    
    return DemoChatResponse(
        response=final_response,
        sources=sources,
        demo=True,
        remaining_requests=remaining,
        processing_time=processing_time
    )


@router.get("/stats")
async def demo_stats_endpoint():
    """
    Get demo usage statistics (no PII).
    """
    return {
        "total_requests": demo_stats["total_requests"],
        "total_errors": demo_stats["total_errors"],
        "uptime_since": demo_stats["started_at"],
        "rate_limit": {
            "max_requests": demo_rate_limiter.max_requests,
            "window_seconds": demo_rate_limiter.window_seconds
        }
    }


@router.get("/health")
async def demo_health():
    """Demo endpoint health check."""
    return {"status": "ok", "demo": True}
