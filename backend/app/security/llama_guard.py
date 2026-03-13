"""
Content Moderation for TaxIA (via Groq API)

Uses Groq API (free tier: 14,400 requests/day) to moderate content
before sending to OpenAI. Model: openai/gpt-oss-safeguard-20b.
Detects 14 categories of harmful content.

Features:
- Spanish language support
- Graceful degradation (fails open if Groq unavailable)
- Latency ~200-500ms
"""
import os
import logging
import httpx
from typing import Optional, List
from dataclasses import dataclass, field
from datetime import datetime

from app.config import settings  # ← FIX: Import settings at module level

logger = logging.getLogger(__name__)


@dataclass
class ModerationResult:
    """Result of content moderation check."""
    is_safe: bool
    blocked_categories: List[str] = field(default_factory=list)
    risk_level: str = "none"  # none, low, medium, high, critical
    raw_response: Optional[str] = None
    latency_ms: float = 0.0
    error: Optional[str] = None


class LlamaGuard:
    """
    Content moderation using Llama Guard 4 via Groq API.
    
    Llama Guard 4 detects 14 categories of harmful content:
    - S1-S4: Violent/non-violent crimes, sexual offenses
    - S5-S8: Defamation, professional advice, privacy, IP
    - S9-S11: Weapons, hate speech, self-harm
    - S12-S14: Adult content, elections, code abuse
    
    Free tier: 14,400 requests/day (enough for most applications)
    """
    
    RISK_CATEGORIES = {
        "S1": "Crímenes violentos",
        "S2": "Crímenes no violentos",
        "S3": "Delitos sexuales",
        "S4": "Explotación infantil",
        "S5": "Difamación",
        "S6": "Consejos profesionales",
        "S7": "Privacidad",
        "S8": "Propiedad intelectual",
        "S9": "Armas",
        "S10": "Odio",
        "S11": "Autolesiones",
        "S12": "Contenido sexual",
        "S13": "Elecciones",
        "S14": "Abuso de código"
    }
    
    # Fiscal/business terms that may trigger false positives but are legitimate
    # These are common in Spanish tax queries (IAE, agricultural activities, etc.)
    FISCAL_WHITELIST = [
        # Agricultural activities (IAE)
        'ponedoras', 'gallinas', 'huevos', 'avícola', 'ganadería', 'ganado',
        'porcino', 'bovino', 'ovino', 'caprino', 'lechería', 'matadero',
        'sacrificio', 'carne', 'carnicería', 'pescado', 'pesquería',
        # Tax terms that might seem aggressive
        'impuesto', 'tributar', 'gravar', 'retención', 'embargo', 'ejecución',
        'sanción', 'multa', 'recargo', 'apremio', 'providencia',
        # Business activities
        'explotación', 'comercio', 'venta', 'compra', 'negocio', 'actividad',
        # Locations
        'bizkaia', 'vizcaya', 'gipuzkoa', 'guipúzcoa', 'araba', 'álava',
        'navarra', 'país vasco', 'euskadi',
        # Specific tax items
        'iae', 'epígrafe', 'cnae', 'modelo', 'declaración', 'autónomo',
        'ticket bai', 'ticketbai', 'verifactu', 'batuz', 'aeat', 'boe',
        'hacienda', 'agencia tributaria', 'irpf', 'iva', 'sociedades',
    ]
    
    # Spanish error messages for blocked content
    BLOCK_MESSAGES = {
        "S1": "Lo siento, no puedo ayudar con contenido relacionado con violencia o crímenes.",
        "S2": "Lo siento, no puedo ayudar con actividades ilegales.",
        "S3": "Lo siento, no puedo ayudar con contenido sexual inapropiado.",
        "S4": "Lo siento, este contenido no está permitido.",
        "S5": "Lo siento, no puedo ayudar con contenido difamatorio.",
        "S6": "Recuerda que soy un asistente fiscal informativo. Para asesoramiento legal específico, consulta con un profesional.",
        "S7": "Lo siento, no puedo ayudar con contenido que viole la privacidad.",
        "S8": "Lo siento, no puedo ayudar con violaciones de propiedad intelectual.",
        "S9": "Lo siento, no puedo ayudar con contenido relacionado con armas.",
        "S10": "Lo siento, no puedo ayudar con contenido de odio o discriminación.",
        "S11": "Si estás pasando por un momento difícil, te recomiendo hablar con un profesional. Teléfono de la Esperanza: 717 003 717",
        "S12": "Lo siento, no puedo ayudar con contenido sexual.",
        "S13": "Lo siento, no puedo proporcionar contenido electoral sesgado.",
        "S14": "Lo siento, no puedo ayudar con código malicioso."
    }
    
    DEFAULT_BLOCK_MESSAGE = (
        "Lo siento, no puedo procesar esta consulta. "
        "Por favor, reformula tu pregunta sobre temas fiscales."
    )
    
    def __init__(self, api_key: str = None, timeout: float = 10.0, enabled: bool = True):
        """
        Initialize Llama Guard.
        
        Args:
            api_key: Groq API key (or from GROQ_API_KEY env var)
            enabled: Whether moderation is enabled
            timeout: Request timeout in seconds
        """
        # Allow override via init args, otherwise use settings
        self.api_key = api_key or settings.GROQ_API_KEY
        
        # Determine strict enabled state: must be enabled in config AND have an API key
        self.enabled = enabled and settings.ENABLE_CONTENT_MODERATION and bool(self.api_key)
        self.timeout = timeout
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        
        # Use model from settings
        self.model_name = settings.GROQ_MODEL
        
        if self.enabled:
            logger.info(f"🛡️ Llama Guard enabled using model: {self.model_name}")
        else:
            if not self.api_key:
                logger.warning("⚠️ Llama Guard disabled (no GROQ_API_KEY in settings)")
            elif not settings.ENABLE_CONTENT_MODERATION:
                 logger.info("⚠️ Llama Guard disabled (ENABLE_CONTENT_MODERATION=False)")
    
    async def moderate(self, text: str) -> ModerationResult:
        """
        Check content for harmful material.
        
        Args:
            text: Text to moderate
            
        Returns:
            ModerationResult with safety assessment
        """
        if not self.enabled:
            return ModerationResult(is_safe=True, risk_level="none")
        
        if not text or len(text.strip()) < 3:
            return ModerationResult(is_safe=True, risk_level="none")
        
        # Check fiscal whitelist - skip moderation for clearly fiscal queries
        text_lower = text.lower()
        fiscal_terms_found = [term for term in self.FISCAL_WHITELIST if term in text_lower]
        if len(fiscal_terms_found) >= 2:
            # If multiple fiscal terms found, it's clearly a tax question - bypass moderation
            logger.info(f"✅ Fiscal whitelist bypass: found {fiscal_terms_found[:3]}...")
            return ModerationResult(is_safe=True, risk_level="none")
        
        start_time = datetime.now()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model_name,
                        "messages": [
                            {
                                "role": "user",
                                "content": text
                            }
                        ],
                        "temperature": 0,
                        "max_tokens": 100
                    }
                )
                
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status_code != 200:
                    logger.warning(f"⚠️ Llama Guard API error: {response.status_code}")
                    # Fail open - allow content if moderation fails
                    return ModerationResult(
                        is_safe=True,
                        risk_level="none",
                        error=f"API error: {response.status_code}",
                        latency_ms=latency_ms
                    )
                
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                # Parse Llama Guard response
                # Format: "safe" or "unsafe\nS1,S2,..."
                is_safe, blocked_categories = self._parse_response(content, text)
                
                risk_level = self._calculate_risk_level(blocked_categories)
                
                if not is_safe:
                    logger.warning(f"🚫 Content blocked: categories={blocked_categories}")
                
                return ModerationResult(
                    is_safe=is_safe,
                    blocked_categories=blocked_categories,
                    risk_level=risk_level,
                    raw_response=content,
                    latency_ms=latency_ms
                )
                
        except httpx.TimeoutException:
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            logger.warning(f"⚠️ Llama Guard timeout after {latency_ms:.0f}ms")
            # Fail open on timeout
            return ModerationResult(
                is_safe=True,
                risk_level="none",
                error="timeout",
                latency_ms=latency_ms
            )
        except Exception as e:
            logger.error(f"❌ Llama Guard error: {e}")
            # Fail open on any error
            return ModerationResult(
                is_safe=True,
                risk_level="none",
                error=str(e)
            )
    
    def _parse_response(self, content: str, original_text: str = "") -> tuple[bool, List[str]]:
        """Parse Llama Guard response into safety decision."""
        content = content.strip().lower()
        
        if content.startswith("safe"):
            return True, []
        
        if content.startswith("unsafe"):
            # Extract categories from response
            categories = []
            for cat in self.RISK_CATEGORIES.keys():
                if cat.lower() in content:
                    categories.append(cat)
            
            # FILTER S6 (Professional Advice) - Tax advice is Impuestify's core function
            categories = [cat for cat in categories if cat != "S6"]
            
            # FILTER S1/S2/S13 (Crimes/Elections) if fiscal context detected - prevents false positives
            # like "ponedoras de huevos" being flagged as violence, or regional tax questions as elections
            if original_text:
                text_lower = original_text.lower()
                has_fiscal_context = any(term in text_lower for term in self.FISCAL_WHITELIST)
                if has_fiscal_context:
                    # Remove crime and elections categories for fiscal queries
                    filtered_cats = ["S1", "S2", "S13"]
                    removed = [cat for cat in categories if cat in filtered_cats]
                    if removed:
                        logger.info(f"✅ Filtering {removed} due to fiscal context in: {original_text[:50]}...")
                    categories = [cat for cat in categories if cat not in filtered_cats]
            
            # If all categories were filtered, consider it safe
            if not categories:
                return True, []
            
            return False, categories
        
        # Unknown format, assume safe
        logger.warning(f"⚠️ Unknown Llama Guard response format: {content[:50]}")
        return True, []
    
    def _calculate_risk_level(self, categories: List[str]) -> str:
        """Calculate overall risk level from blocked categories."""
        if not categories:
            return "none"
        
        # Critical categories
        critical = {"S1", "S3", "S4", "S11"}
        high = {"S2", "S9", "S10"}
        
        if any(cat in critical for cat in categories):
            return "critical"
        if any(cat in high for cat in categories):
            return "high"
        
        return "medium"
    
    def get_block_message(self, categories: List[str]) -> str:
        """Get user-friendly block message in Spanish."""
        if not categories:
            return self.DEFAULT_BLOCK_MESSAGE
        
        # Return message for first blocked category
        first_cat = categories[0]
        return self.BLOCK_MESSAGES.get(first_cat, self.DEFAULT_BLOCK_MESSAGE)


# Global instance
_llama_guard: Optional[LlamaGuard] = None


def get_llama_guard() -> LlamaGuard:
    """Get global Llama Guard instance."""
    global _llama_guard
    if _llama_guard is None:
        from app.config import settings
        _llama_guard = LlamaGuard(
            api_key=getattr(settings, 'GROQ_API_KEY', None),
            enabled=getattr(settings, 'ENABLE_CONTENT_MODERATION', True)
        )
    return _llama_guard


async def moderate_content(text: str) -> ModerationResult:
    """Convenience function to moderate content."""
    guard = get_llama_guard()
    return await guard.moderate(text)
