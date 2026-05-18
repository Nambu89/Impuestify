"""
Security Module for TaxIA

Comprehensive security suite including:
- PII Detection and Redaction
- Prompt Injection Prevention
- Rate Limiting & DDoS Protection
- SQL Injection Prevention (Direct & Indirect)
- AI Guardrails and Safety
- File Upload Validation
- Content Moderation (Llama Guard)
- Semantic Cache
- Complexity Router
- Audit Logging
"""

from app.security.audit_logger import AuditEventType, AuditLogger, audit_logger
from app.security.complexity_router import (
    ComplexityClassifier,
    ComplexityLevel,
    ComplexityResult,
    ReasoningEffort,
    classify_complexity,
    complexity_classifier,
    get_reasoning_effort,
)
from app.security.file_validator import FileValidationResult, FileValidator, file_validator
from app.security.guardrails import GuardrailsResult, TaxIAGuardrails, guardrails_system

# New security modules (v2.7)
from app.security.llama_guard import LlamaGuard, ModerationResult, get_llama_guard, moderate_content
from app.security.pii_detector import PIIDetectionResult, pii_detector
from app.security.prompt_injection import (
    InjectionCheckResult,
    PromptInjectionFilter,
    prompt_injection_filter,
)
from app.security.rate_limiter import (
    check_ip_blocked,
    ip_blocker,
    limiter,
    rate_limit_ask,
    rate_limit_auth,
    rate_limit_exceeded_handler,
    rate_limit_notification,
    rate_limit_read,
)
from app.security.semantic_cache import CacheResult, SemanticCache, get_semantic_cache
from app.security.sql_injection import SQLInjectionResult, SQLInjectionValidator, sql_validator

__all__ = [
    # Existing
    "pii_detector",
    "PIIDetectionResult",
    "prompt_injection_filter",
    "PromptInjectionFilter",
    "InjectionCheckResult",
    "limiter",
    "check_ip_blocked",
    "ip_blocker",
    "rate_limit_ask",
    "rate_limit_notification",
    "rate_limit_auth",
    "rate_limit_read",
    "rate_limit_exceeded_handler",
    "sql_validator",
    "SQLInjectionResult",
    "SQLInjectionValidator",
    "guardrails_system",
    "GuardrailsResult",
    "TaxIAGuardrails",
    "file_validator",
    "FileValidationResult",
    "FileValidator",
    # New (v2.7)
    "get_llama_guard",
    "moderate_content",
    "LlamaGuard",
    "ModerationResult",
    "get_semantic_cache",
    "SemanticCache",
    "CacheResult",
    "complexity_classifier",
    "get_reasoning_effort",
    "classify_complexity",
    "ComplexityClassifier",
    "ComplexityResult",
    "ComplexityLevel",
    "ReasoningEffort",
    "audit_logger",
    "AuditLogger",
    "AuditEventType",
]
