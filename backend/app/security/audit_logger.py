"""
Audit Logger for TaxIA

Immutable logging for security-critical events.
Logs to structured format for monitoring and compliance.

Events logged:
- Authentication (login, logout, failed attempts)
- AI requests (queries, moderation blocks)
- Rate limit violations
- Admin actions
"""
import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass, asdict

logger = logging.getLogger("audit")


class AuditEventType(Enum):
    """Types of auditable events."""
    # Authentication
    AUTH_LOGIN_SUCCESS = "auth.login.success"
    AUTH_LOGIN_FAILED = "auth.login.failed"
    AUTH_LOGOUT = "auth.logout"
    AUTH_TOKEN_REFRESH = "auth.token.refresh"
    AUTH_REGISTER = "auth.register"
    
    # AI Operations
    AI_QUERY = "ai.query"
    AI_RESPONSE = "ai.response"
    AI_MODERATION_BLOCK = "ai.moderation.block"
    AI_CACHE_HIT = "ai.cache.hit"
    AI_TOOL_CALL = "ai.tool.call"
    
    # Rate Limiting
    RATE_LIMIT_EXCEEDED = "rate.limit.exceeded"
    RATE_LIMIT_IP_BLOCKED = "rate.limit.ip_blocked"
    
    # File Operations
    FILE_UPLOAD = "file.upload"
    FILE_UPLOAD_REJECTED = "file.upload.rejected"
    
    # Admin Actions
    ADMIN_USER_UPDATE = "admin.user.update"
    ADMIN_CONFIG_CHANGE = "admin.config.change"
    
    # Security Events
    SECURITY_INJECTION_ATTEMPT = "security.injection.attempt"
    SECURITY_PII_DETECTED = "security.pii.detected"


@dataclass
class AuditEvent:
    """Immutable audit event record."""
    event_type: str
    timestamp: str
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    severity: str = "info"  # info, warning, error, critical
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False)


class AuditLogger:
    """
    Structured audit logger for security events.
    
    Logs are immutable and structured for easy parsing
    and monitoring integration.
    """
    
    SEVERITY_LEVELS = {
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL
    }
    
    def __init__(self):
        """Initialize audit logger."""
        # Configure audit logger with structured format
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                '%(asctime)s | AUDIT | %(message)s'
            ))
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
    
    def log(
        self,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "info"
    ):
        """
        Log an audit event.
        
        Args:
            event_type: Type of event
            user_id: User identifier (if available)
            ip_address: Client IP address
            details: Additional event details
            severity: Event severity level
        """
        event = AuditEvent(
            event_type=event_type.value,
            timestamp=datetime.utcnow().isoformat() + "Z",
            user_id=user_id,
            ip_address=ip_address,
            details=details,
            severity=severity
        )
        
        log_level = self.SEVERITY_LEVELS.get(severity, logging.INFO)
        logger.log(log_level, event.to_json())
    
    # Convenience methods for common events
    
    def log_login_success(self, user_id: str, ip_address: str):
        """Log successful login."""
        self.log(
            AuditEventType.AUTH_LOGIN_SUCCESS,
            user_id=user_id,
            ip_address=ip_address,
            severity="info"
        )
    
    def log_login_failed(self, email: str, ip_address: str, reason: str = "invalid_credentials"):
        """Log failed login attempt."""
        self.log(
            AuditEventType.AUTH_LOGIN_FAILED,
            ip_address=ip_address,
            details={"email": email, "reason": reason},
            severity="warning"
        )
    
    def log_ai_query(self, user_id: str, query_preview: str, ip_address: Optional[str] = None):
        """Log AI query."""
        self.log(
            AuditEventType.AI_QUERY,
            user_id=user_id,
            ip_address=ip_address,
            details={"query_preview": query_preview[:100]}
        )
    
    def log_moderation_block(
        self,
        user_id: str,
        categories: list,
        ip_address: Optional[str] = None
    ):
        """Log content moderation block."""
        self.log(
            AuditEventType.AI_MODERATION_BLOCK,
            user_id=user_id,
            ip_address=ip_address,
            details={"blocked_categories": categories},
            severity="warning"
        )
    
    def log_rate_limit_exceeded(self, ip_address: str, endpoint: str, user_id: Optional[str] = None):
        """Log rate limit violation."""
        self.log(
            AuditEventType.RATE_LIMIT_EXCEEDED,
            user_id=user_id,
            ip_address=ip_address,
            details={"endpoint": endpoint},
            severity="warning"
        )
    
    def log_ip_blocked(self, ip_address: str, violation_count: int):
        """Log IP blocking."""
        self.log(
            AuditEventType.RATE_LIMIT_IP_BLOCKED,
            ip_address=ip_address,
            details={"violation_count": violation_count},
            severity="error"
        )
    
    def log_injection_attempt(self, ip_address: str, patterns: list, user_id: Optional[str] = None):
        """Log injection attempt detection."""
        self.log(
            AuditEventType.SECURITY_INJECTION_ATTEMPT,
            user_id=user_id,
            ip_address=ip_address,
            details={"matched_patterns": patterns},
            severity="critical"
        )
    
    def log_cache_hit(self, user_id: str, similarity: float):
        """Log semantic cache hit."""
        self.log(
            AuditEventType.AI_CACHE_HIT,
            user_id=user_id,
            details={"similarity": round(similarity, 3)}
        )


# Global instance
audit_logger = AuditLogger()
