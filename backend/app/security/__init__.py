"""
Security Module for TaxIA

Comprehensive security suite including:
- PII Detection and Redaction
- Prompt Injection Prevention
- Rate Limiting & DDoS Protection
- SQL Injection Prevention (Direct & Indirect)
- AI Guardrails and Safety
- File Upload Validation
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


__all__ = [
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
]
