"""
Prompt Injection Filter for TaxIA

Detects and blocks direct and indirect prompt injection attacks.
Based on OWASP LLM Top 10 recommendations.
"""
import re
import logging
from typing import Tuple, List
from dataclasses import dataclass

from app.config import settings  # ← FIX: Import settings at module level

logger = logging.getLogger(__name__)


@dataclass
class InjectionCheckResult:
    """Result of prompt injection check"""
    is_safe: bool
    risk_score: float  # 0.0 to 1.0
    matched_patterns: List[str]
    sanitized_input: str


class PromptInjectionFilter:
    """
    Filter to detect and prevent prompt injection attacks.
    
    Implements multiple detection strategies:
    1. Pattern-based detection (direct injection)
    2. Delimiter manipulation detection
    3. Role hijacking detection
    """
    
    # Direct injection patterns
    INJECTION_PATTERNS = [
        # Ignore instructions - expanded patterns
        (r"ignore\s+(all\s+)?(previous|prior|above|earlier|your|the|my)?\s*(instructions?|prompts?|rules?)", "ignore_instructions"),
        (r"disregard\s+(all\s+)?(previous|prior|above|your)?\s*(instructions?)?", "disregard_instructions"),
        (r"forget\s+(everything|all|your\s+instructions?)", "forget_instructions"),
        
        # New instructions injection
        (r"new\s+(instructions?|rules?|prompt)\s*[:=]", "new_instructions"),
        (r"your\s+new\s+(task|role|instructions?)\s+is", "role_change"),
        (r"from\s+now\s+on\s+(you\s+are|act\s+as|pretend)", "role_hijack"),
        
        # System prompt extraction - expanded patterns
        (r"(show|reveal|display|print|output)\s+(me\s+)?(your\s+)?(system\s+)?prompt", "prompt_extraction"),
        (r"what\s+(are|is)\s+your\s+(system\s+)?(prompt|instructions?)", "prompt_extraction"),
        (r"repeat\s+(your\s+)?(initial|first|original|system)?\s*(prompt|instructions?)", "prompt_extraction"),
        
        # Role manipulation
        (r"you\s+are\s+(now|actually)\s+(a|an)\s+", "role_manipulation"),
        (r"pretend\s+(to\s+be|you\s+are)", "role_manipulation"),
        (r"act\s+as\s+(if|though)\s+you", "role_manipulation"),
        (r"roleplay\s+as", "role_manipulation"),
        
        # Delimiter attacks
        (r"\]\s*\}\s*\{", "json_injection"),
        (r"```\s*(system|assistant|user)", "markdown_injection"),
        (r"<\s*/?system\s*>", "xml_injection"),
        
        # Jailbreak attempts
        (r"(DAN|dan)\s*mode", "jailbreak"),
        (r"developer\s+mode", "jailbreak"),
        (r"(bypass|disable|ignore)\s+(safety|security|filter|restriction)", "jailbreak"),
        
        # Indirect injection markers
        (r"\[hidden\]|\[invisible\]|\[secret\]", "hidden_content"),
    ]
    
    # Suspicious character patterns
    SUSPICIOUS_CHARS = [
        (r"[\u200b-\u200f\u2028-\u202e\u2060-\u206f]", "invisible_chars"),  # Zero-width and special Unicode
        (r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "control_chars"),  # Control characters
    ]
    
    def __init__(self, sensitivity: float = 0.5):
        """
        Initialize the filter with Groq client.
        """
        from groq import Groq
        from app.config import settings
        
        self.sensitivity = sensitivity
        self.client = None
        
        if settings.GROQ_API_KEY:
            try:
                self.client = Groq(api_key=settings.GROQ_API_KEY)
                logger.info(f"✅ Prompt Injection Filter initialized with Groq model: {settings.GROQ_MODEL_PROMPT_GUARD}")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Groq client for Prompt Guard: {e}")
        else:
            logger.warning("⚠️ GROQ_API_KEY not found. Prompt Injection Logic will fail.")

    def check(self, text: str) -> InjectionCheckResult:
        """
        Check text for potential prompt injection using Llama Prompt Guard.
        """
        if not text or not text.strip():
            return InjectionCheckResult(is_safe=True, risk_score=0.0, matched_patterns=[], sanitized_input="")

        if not self.client:
             # Fallback or Fail Safe
             return InjectionCheckResult(
                 is_safe=True, 
                 risk_score=0.0, 
                 matched_patterns=["GROQ_CLIENT_MISSING"], 
                 sanitized_input=text
             )

        try:
            from app.config import settings
            
            # Llama Prompt Guard is a classifier. It outputs "Safe" or "Unsafe" (and sometimes probabilities).
            # We treat the text as the user prompt to be analyzed.
            
            completion = self.client.chat.completions.create(
                model=settings.GROQ_MODEL_PROMPT_GUARD,
                messages=[{"role": "user", "content": text}],
                temperature=0.0,
            )
            
            response = completion.choices[0].message.content.strip().lower()
            
            is_unsafe = "unsafe" in response or "injection" in response
            
            risk_score = 0.9 if is_unsafe else 0.0
            matched_patterns = ["Prompt Guard: Unsafe"] if is_unsafe else []
            
            if is_unsafe:
                logger.warning(f"🚨 Prompt Injection detected by API: {response}")

            return InjectionCheckResult(
                is_safe=not is_unsafe,
                risk_score=risk_score,
                matched_patterns=matched_patterns,
                sanitized_input=text # We don't sanitize with LLM, we just block
            )

        except Exception as e:
            logger.error(f"❌ Prompt Injection API Error: {e}")
            # Fail safe or fail closed? 
            # For security, better to Fail Open if API down? Or Fail Closed?
            # User wants robust. Let's return safe but log heavily.
            return InjectionCheckResult(
                 is_safe=True, 
                 risk_score=0.0, 
                 matched_patterns=[f"API_ERROR: {str(e)}"], 
                 sanitized_input=text
            )
    
    def _sanitize(self, text: str) -> str:
        """
        Sanitize text by removing dangerous patterns.
        """
        sanitized = text
        
        # Remove invisible characters
        for pattern, _ in self.compiled_suspicious:
            sanitized = pattern.sub("", sanitized)
        
        # Escape potential delimiters
        sanitized = sanitized.replace("```", "` ` `")
        sanitized = re.sub(r'\[hidden\]|\[invisible\]|\[secret\]', '', sanitized, flags=re.IGNORECASE)
        
        return sanitized.strip()
    
    def validate(self, text: str) -> Tuple[bool, str]:
        """
        Simple validation interface.
        
        Args:
            text: User input to validate
            
        Returns:
            Tuple of (is_safe, message)
        """
        result = self.check(text)
        
        if result.is_safe:
            return True, text
        else:
            return False, "Tu consulta contiene patrones no permitidos. Por favor, reformula tu pregunta."


# Global instance
prompt_injection_filter = PromptInjectionFilter(sensitivity=0.5)
