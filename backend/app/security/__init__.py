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
from app.security.pii_detector import pii_detector, PIIDetectionResult
from app.security.prompt_injection import prompt_injection_filter, InjectionCheckResult, PromptInjectionFilter
from app.security.rate_limiter import (
    limiter, check_ip_blocked, ip_blocker,
    rate_limit_ask, rate_limit_notification, rate_limit_auth, rate_limit_read,
    rate_limit_exceeded_handler
)
from app.security.sql_injection import sql_validator, SQLInjectionResult, SQLInjectionValidator
from app.security.guardrails import guardrails_system, GuardrailsResult, TaxIAGuardrails
from app.security.file_validator import file_validator, FileValidationResult, FileValidator

# New security modules (v2.7)
from app.security.llama_guard import get_llama_guard, moderate_content, LlamaGuard, ModerationResult
from app.security.semantic_cache import get_semantic_cache, SemanticCache, CacheResult
from app.security.complexity_router import (
    complexity_classifier, get_reasoning_effort, classify_complexity,
    ComplexityClassifier, ComplexityResult, ComplexityLevel, ReasoningEffort
)
from app.security.audit_logger import audit_logger, AuditLogger, AuditEventType


__all__ = [
    # Existing
    'pii_detector',
    'PIIDetectionResult',
    'prompt_injection_filter',
    'PromptInjectionFilter',
    'InjectionCheckResult',
    'limiter',
    'check_ip_blocked',
    'ip_blocker',
    'rate_limit_ask',
    'rate_limit_notification',
    'rate_limit_auth',
    'rate_limit_read',
    'rate_limit_exceeded_handler',
    'sql_validator',
    'SQLInjectionResult',
    'SQLInjectionValidator',
    'guardrails_system',
    'GuardrailsResult',
    'TaxIAGuardrails',
    'file_validator',
    'FileValidationResult',
    'FileValidator',
    # New (v2.7)
    'get_llama_guard',
    'moderate_content',
    'LlamaGuard',
    'ModerationResult',
    'get_semantic_cache',
    'SemanticCache',
    'CacheResult',
    'complexity_classifier',
    'get_reasoning_effort',
    'classify_complexity',
    'ComplexityClassifier',
    'ComplexityResult',
    'ComplexityLevel',
    'ReasoningEffort',
    'audit_logger',
    'AuditLogger',
    'AuditEventType',
]

