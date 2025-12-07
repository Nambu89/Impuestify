"""
Prompt Injection Filter for TaxIA

Detects and blocks direct and indirect prompt injection attacks.
Based on OWASP LLM Top 10 recommendations.
"""
import re
import logging
from typing import Tuple, List
from dataclasses import dataclass

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
        Initialize the filter.
        
        Args:
            sensitivity: Detection sensitivity (0.0 to 1.0)
                         Higher values = more strict, more false positives
        """
        self.sensitivity = max(0.0, min(1.0, sensitivity))
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile regex patterns for efficiency"""
        self.compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), name)
            for pattern, name in self.INJECTION_PATTERNS
        ]
        self.compiled_suspicious = [
            (re.compile(pattern), name)
            for pattern, name in self.SUSPICIOUS_CHARS
        ]
    
    def check(self, text: str) -> InjectionCheckResult:
        """
        Check text for potential prompt injection.
        
        Args:
            text: User input to validate
            
        Returns:
            InjectionCheckResult with safety status and details
        """
        if not text or not text.strip():
            return InjectionCheckResult(
                is_safe=True,
                risk_score=0.0,
                matched_patterns=[],
                sanitized_input=""
            )
        
        matched_patterns = []
        risk_score = 0.0
        
        # Check injection patterns
        for pattern, name in self.compiled_patterns:
            if pattern.search(text):
                matched_patterns.append(name)
                risk_score += 0.3
        
        # Check suspicious characters
        for pattern, name in self.compiled_suspicious:
            if pattern.search(text):
                matched_patterns.append(name)
                risk_score += 0.2
        
        # Check for excessive special characters
        special_ratio = len(re.findall(r'[{}\[\]<>|\\`]', text)) / max(1, len(text))
        if special_ratio > 0.1:
            matched_patterns.append("excessive_special_chars")
            risk_score += special_ratio
        
        # Normalize risk score
        risk_score = min(1.0, risk_score)
        
        # Determine if safe based on sensitivity threshold
        is_safe = risk_score < self.sensitivity
        
        # Sanitize input (remove dangerous patterns)
        sanitized = self._sanitize(text) if not is_safe else text
        
        if matched_patterns:
            logger.warning(
                f"Prompt injection patterns detected: {matched_patterns}, "
                f"risk_score: {risk_score:.2f}"
            )
        
        return InjectionCheckResult(
            is_safe=is_safe,
            risk_score=risk_score,
            matched_patterns=matched_patterns,
            sanitized_input=sanitized
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
