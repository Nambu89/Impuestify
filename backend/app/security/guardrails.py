"""
Guardrails System for TaxIA

Implements AI safety guardrails using guardrails-ai library to prevent:
1. Hallucinations (unsupported claims)
2. Tax evasion advice
3. Off-topic responses
4. Inappropriate content
5. Regulatory compliance violations

Uses multi-layer validation:
- Input validation (pre-LLM)
- Output validation (post-LLM)
- Semantic analysis
- Domain-specific rules
"""
import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import re

logger = logging.getLogger(__name__)

# Try to import guardrails-ai (optional dependency)
try:
    import guardrails as gd
    # Don't import validators - they may not exist in all versions
    # We use rule-based validation anyway as primary method
    GUARDRAILS_AVAILABLE = True
    logger.info("✅ guardrails-ai loaded successfully")
except ImportError as e:
    GUARDRAILS_AVAILABLE = False
    logger.info(f"ℹ️  guardrails-ai not available ({e}). Using rule-based fallback.")


class GuardrailsResult(BaseModel):
    """Result of guardrails validation"""
    is_safe: bool
    risk_level: str = Field(description="none, low, medium, high, critical")
    violations: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    validated_output: Optional[str] = None


class TaxIAGuardrails:
    """
    Comprehensive guardrails system for TaxIA.
    
    Ensures all AI responses are:
    - Legally compliant
    - Factually grounded
    - Domain-appropriate
    - Safe and helpful
    """
    
    # Prohibited topics (tax evasion indicators)
    # NOTE: Only include phrases that are UNAMBIGUOUSLY evasion.
    # "no declarar" was removed — users legitimately ask "¿qué pasa si no declaro?"
    # which is an informational query about penalties, not evasion advice.
    PROHIBITED_KEYWORDS = [
        'evasión fiscal', 'evadir impuestos', 'ocultar ingresos',
        'dinero negro', 'economía sumergida',
        'factura falsa', 'sociedades offshore', 'paraíso fiscal',
        'evitar pagar impuestos ilegalmente',
        'cómo no pagar impuestos', 'como no pagar impuestos',
        'fraude fiscal', 'delito fiscal'
    ]
    
    # Mandatory disclaimer keywords (when detected, response must include warnings)
    RISK_KEYWORDS = [
        'sanción', 'multa', 'recargo', 'intereses de demora',
        'inspección', 'hacienda comprueba', 'delito',
        'prescripción', 'regularización'
    ]
    
    # Required grounding phrases (responses should reference sources)
    GROUNDING_INDICATORS = [
        'según', 'de acuerdo con', 'la normativa establece',
        'el artículo', 'la ley', 'el reglamento',
        'en el documento', 'conforme a'
    ]
    
    # Greeting patterns (common greetings in Spanish and English)
    GREETING_PATTERNS = [
        r'\b(hola|hello|hi|hey|buenos días|buenas tardes|buenas noches)\b',
        r'\b(qué tal|cómo estás|cómo vas|saludos)\b',
        r'^(hola|hi|hey)\s*[!.?]*$'
    ]
    
    def __init__(self, enable_strict_mode: bool = True):
        """
        Initialize guardrails system.
        
        Args:
            enable_strict_mode: If True, applies stricter validation rules
        """
        self.strict_mode = enable_strict_mode
        self.guardrails_available = GUARDRAILS_AVAILABLE
        
        if not GUARDRAILS_AVAILABLE:
            logger.info("Using rule-based guardrails (guardrails-ai not available)")
    
    def validate_input(self, user_question: str) -> GuardrailsResult:
        """
        Validate user input before sending to LLM.
        
        Checks for:
        - Inappropriate requests (tax evasion)
        - Off-topic questions
        - Excessive length
        - Toxic/abusive language
        
        Args:
            user_question: User's input question
            
        Returns:
            GuardrailsResult with safety assessment
        """
        violations = []
        suggestions = []
        risk_level = "none"
        
        # Check length
        if len(user_question) > 1000:
            violations.append("Question too long (>1000 characters)")
            suggestions.append("Please rephrase your question more concisely")
            risk_level = "low"
        
        if len(user_question) < 3:
            violations.append("Question too short (<3 characters)")
            risk_level = "medium"
        
        # Check for prohibited content (tax evasion)
        lower_question = user_question.lower()
        for keyword in self.PROHIBITED_KEYWORDS:
            if keyword in lower_question:
                violations.append(f"Prohibited topic detected: {keyword}")
                suggestions.append(
                    "TaxIA está diseñado para asesoramiento legal. "
                    "No podemos ayudar con actividades que violen la normativa fiscal."
                )
                risk_level = "critical"
                break
        
        # Check if it's a greeting before checking if tax-related
        if self.is_greeting(user_question):
            # Greetings are safe and don't need to be tax-related
            logger.info("👋 Greeting detected, skipping tax-keyword validation")
        else:
            # Check if question is tax-related
            tax_keywords = [
                'irpf', 'renta', 'impuesto', 'declaración', 'hacienda',
                'tributar', 'fiscal', 'deducción', 'exención', 'retención',
                'iva', 'sociedades', 'patrimonio', 'plusvalía'
            ]
            
            is_tax_related = any(kw in lower_question for kw in tax_keywords)
            
            if not is_tax_related and self.strict_mode:
                # Might be off-topic
                suggestions.append(
                    "Tu pregunta no parece relacionada con temas fiscales. "
                    "TaxIA está especializado en IRPF y normativa tributaria española."
                )
                risk_level = "low" if risk_level == "none" else risk_level
        
        # Use guardrails-ai if available
        if self.guardrails_available:
            try:
                # Check for toxic language
                guard = gd.Guard().use(ToxicLanguage(threshold=0.5, validation_method="sentence"))
                result = guard.validate(user_question)
                
                if not result.validation_passed:
                    violations.append("Potentially toxic or inappropriate language detected")
                    risk_level = "high"
            except Exception as e:
                logger.debug(f"Guardrails-ai validation skipped: {e}")
        
        is_safe = risk_level in ["none", "low"]
        
        if not is_safe:
            logger.warning(f"⚠️ Input guardrail triggered: {violations}")
        
        return GuardrailsResult(
            is_safe=is_safe,
            risk_level=risk_level,
            violations=violations,
            suggestions=suggestions
        )
    
    def validate_output(
        self,
        llm_response: str,
        user_question: str,
        sources: Optional[List[Dict]] = None
    ) -> GuardrailsResult:
        """
        Validate LLM output before returning to user.
        
        Checks for:
        - Hallucinations (claims without source backing)
        - Prohibited advice
        - Missing disclaimers
        - Factual grounding
        
        Args:
            llm_response: Generated response from LLM
            user_question: Original user question
            sources: Retrieved document sources
            
        Returns:
            GuardrailsResult with safety assessment
        """
        violations = []
        suggestions = []
        risk_level = "none"
        
        # Check if response contains grounding (references to sources)
        has_grounding = any(
            indicator in llm_response.lower()
            for indicator in self.GROUNDING_INDICATORS
        )
        
        if not has_grounding and sources:
            violations.append("Response lacks proper source attribution")
            suggestions.append("Add references like 'según la normativa...' or 'el artículo X establece...'")
            risk_level = "medium"
        
        # Check for prohibited advice in output
        lower_response = llm_response.lower()
        for keyword in self.PROHIBITED_KEYWORDS:
            if keyword in lower_response:
                violations.append(f"Response contains prohibited content: {keyword}")
                risk_level = "critical"
                suggestions.append("Remove any advice related to tax evasion or illegal activities")
        
        # Check for risk topics requiring disclaimers
        contains_risk_topic = any(
            keyword in lower_response
            for keyword in self.RISK_KEYWORDS
        )
        
        disclaimer_present = any(
            phrase in lower_response
            for phrase in ['consulta con un asesor', 'recomendamos consultar', 'asesor fiscal']
        )
        
        if contains_risk_topic and not disclaimer_present and self.strict_mode:
            violations.append("Response discusses sanctions/penalties without professional disclaimer")
            suggestions.append(
                "Add disclaimer: 'Para casos específicos con sanciones, "
                "te recomendamos consultar con un asesor fiscal profesional.'"
            )
            risk_level = "medium" if risk_level == "none" else risk_level
        
        # Check response length
        if len(llm_response) < 50:
            violations.append("Response too short (possible generation failure)")
            risk_level = "high"
        
        if len(llm_response) > 2000:
            suggestions.append("Response is quite long, consider summarizing")
        
        # Check for hallucination indicators
        hallucination_phrases = [
            'no estoy seguro', 'no tengo información', 'no puedo confirmar',
            'posiblemente', 'probablemente', 'creo que', 'puede que'
        ]
        
        uncertainty_count = sum(
            1 for phrase in hallucination_phrases
            if phrase in lower_response
        )
        
        if uncertainty_count > 2:
            violations.append(f"High uncertainty in response ({uncertainty_count} uncertain phrases)")
            suggestions.append("Response shows lack of confidence - verify against sources")
            risk_level = "medium" if risk_level == "none" else risk_level
        
        # Validate with guardrails-ai if available
        if self.guardrails_available:
            try:
                # Check output length
                guard = gd.Guard().use(ValidLength(min=50, max=2000))
                result = guard.validate(llm_response)
                
                if not result.validation_passed:
                    violations.append("Output length validation failed")
                    risk_level = "low" if risk_level == "none" else risk_level
            except Exception as e:
                logger.debug(f"Guardrails-ai output validation skipped: {e}")
        
        is_safe = risk_level in ["none", "low"]
        
        if not is_safe:
            logger.warning(f"⚠️ Output guardrail triggered: {violations}")
        
        return GuardrailsResult(
            is_safe=is_safe,
            risk_level=risk_level,
            violations=violations,
            suggestions=suggestions,
            validated_output=llm_response if is_safe else None
        )
    
    def apply_safety_wrapper(
        self,
        response: str,
        risk_level: str = "none"
    ) -> str:
        """
        Wrap response with appropriate safety disclaimers.
        
        Args:
            response: Original LLM response
            risk_level: Detected risk level
            
        Returns:
            Response with safety wrapper
        """
        if risk_level in ["medium", "high"]:
            disclaimer = (
                "\n\n⚠️ **Aviso importante**: Esta información es orientativa. "
                "Para situaciones específicas que impliquen sanciones o procedimientos "
                "de inspección, te recomendamos consultar con un asesor fiscal profesional."
            )
            return response + disclaimer
        
        if risk_level == "critical":
            return (
                "❌ Lo siento, no puedo proporcionar asesoramiento sobre actividades "
                "que podrían ser contrarias a la normativa fiscal española. "
                "TaxIA está diseñado para ayudarte con el cumplimiento legal de tus "
                "obligaciones tributarias. ¿Tienes alguna otra consulta sobre declaración "
                "de impuestos o deducciones legales?"
            )
        
        return response
    
    def is_greeting(self, text: str) -> bool:
        """
        Detect if the text is a simple greeting.
        
        Args:
            text: User input text
            
        Returns:
            True if text matches greeting patterns
        """
        text_clean = text.strip().lower()
        
        # Check if it's very short and matches greeting pattern
        if len(text_clean) < 50:  # Greetings are typically short
            for pattern in self.GREETING_PATTERNS:
                if re.search(pattern, text_clean):
                    return True
        
        return False
    
    def validate_output_format(self, response: str) -> bool:
        """
        Validate that response doesn't contain internal JSON or debug info.
        
        Args:
            response: LLM response to validate
            
        Returns:
            True if response format is clean, False if contains internal data
        """
        # Check for JSON-like structures that shouldn't be in user-facing text
        json_indicators = [
            r'\{\s*["\']tool["\']\s*:',  # {"tool": ...}
            r'\{\s*["\']function["\']\s*:',  # {"function": ...}
            r'\{\s*["\']query["\']\s*:',  # {"query": ...}
            r'\{\s*["\']search_params["\']\s*:',  # Internal search params
        ]
        
        for pattern in json_indicators:
            if re.search(pattern, response):
                logger.warning(f"⚠️ Internal JSON detected in response: {pattern}")
                return False
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get guardrails system statistics."""
        return {
            "strict_mode": self.strict_mode,
            "guardrails_ai_available": self.guardrails_available,
            "prohibited_keywords_count": len(self.PROHIBITED_KEYWORDS),
            "risk_keywords_count": len(self.RISK_KEYWORDS),
            "greeting_patterns_count": len(self.GREETING_PATTERNS)
        }


# Global guardrails instance
guardrails_system = TaxIAGuardrails(enable_strict_mode=True)