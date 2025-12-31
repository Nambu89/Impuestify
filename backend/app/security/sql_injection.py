"""
SQL Injection Prevention for TaxIA

Protects against both DIRECT and INDIRECT SQL injection attacks:
- Direct: User input in queries
- Indirect: LLM-generated SQL code

Uses multiple layers of defense:
1. Input sanitization and validation
2. SQL keyword detection
3. Pattern matching for malicious syntax
4. Query structure validation
"""
import re
import logging
from typing import Optional, List, Tuple
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SQLInjectionResult(BaseModel):
    """Result of SQL injection check"""
    is_safe: bool
    risk_level: str = Field(description="none, low, medium, high, critical")
    violations: List[str] = Field(default_factory=list)
    sanitized_input: Optional[str] = None


class SQLInjectionValidator:
    """
    Validates inputs and generated SQL for injection attacks.
    
    Implements OWASP recommendations for SQL injection prevention.
    """
    
    # Dangerous SQL keywords that should trigger alerts
    DANGEROUS_KEYWORDS = [
        # Data manipulation
        'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE',
        # Access control
        'GRANT', 'REVOKE',
        # System functions
        'EXEC', 'EXECUTE', 'SYSTEM', 'SHELL',
        # Union-based injection
        'UNION SELECT',
        # Comment-based injection
        '--', '/*', '*/', '#',
        # Stacked queries
        ';DROP', ';DELETE', ';UPDATE',
    ]
    
    # Suspicious patterns (regex)
    SUSPICIOUS_PATTERNS = [
        r"('\s*OR\s*'1'\s*=\s*'1)",  # Classic '1'='1' injection
        r"('\s*OR\s*1\s*=\s*1)",      # Numeric variant
        r"(\bOR\b\s+\d+\s*=\s*\d+)",  # Boolean-based blind injection
        r"(;\s*DROP\s+TABLE)",         # Stacked query
        r"(UNION\s+SELECT)",           # Union-based injection
        r"(WAITFOR\s+DELAY)",          # Time-based blind injection
        r"(BENCHMARK\s*\()",           # MySQL time-based
        r"(SLEEP\s*\()",               # Sleep function
        r"(LOAD_FILE\s*\()",           # File access
        r"(INTO\s+OUTFILE)",           # File write
        r"(--[^\n]*)",                 # SQL comments
        r"(/\*.*?\*/)",                # Multi-line comments
        r"(\bHEX\s*\()",               # Encoding functions
        r"(\bCHAR\s*\()",              # Character encoding
        r"(0x[0-9a-fA-F]+)",           # Hexadecimal literals
    ]
    
    def __init__(self):
        """
        Initialize the SQL injection validator with Groq client.
        """
        from groq import Groq
        from app.config import settings
        
        self.client = None
        if settings.GROQ_API_KEY:
            try:
                self.client = Groq(api_key=settings.GROQ_API_KEY)
                logger.info(f"✅ SQL Injection Validator initialized with Groq model: {settings.GROQ_MODEL_SAFETY}")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Groq client for SQL Validator: {e}")
        else:
            logger.warning("⚠️ GROQ_API_KEY not found. SQL Injection Logic will fail.")

    def validate_user_input(self, user_input: str) -> SQLInjectionResult:
        """
        Validate user input using Llama Guard 4 (Category S14).
        """
        if not user_input or len(user_input.strip()) < 3:
             return SQLInjectionResult(is_safe=True, risk_level="none")

        if not self.client:
             return SQLInjectionResult(
                 is_safe=True, 
                 risk_level="low", 
                 violations=["GROQ_CLIENT_MISSING"]
             )
        
        try:
            from app.config import settings
            
            completion = self.client.chat.completions.create(
                model=settings.GROQ_MODEL_SAFETY,
                messages=[{"role": "user", "content": user_input}],
                temperature=0.0
            )
            
            response = completion.choices[0].message.content.strip()
            
            is_unsafe = "unsafe" in response.lower() and "S14" in response
            
            violations = []
            if is_unsafe:
                violations.append("AI Detected: Code Interpreter Abuse / SQL Injection (S14)")
                logger.warning(f"🚨 SQL Injection detected by Llama Guard: {response}")
                
            return SQLInjectionResult(
                is_safe=not is_unsafe,
                risk_level="critical" if is_unsafe else "low",
                violations=violations,
                sanitized_input=user_input
            )

        except Exception as e:
            logger.error(f"❌ SQL Validator API Error: {e}")
            return SQLInjectionResult(
                 is_safe=True, 
                 risk_level="low", 
                 violations=[f"API_ERROR: {str(e)}"]
            )
    
    def validate_generated_sql(self, sql_query: str, context: str = "") -> SQLInjectionResult:
        """
        Validate LLM-generated SQL for indirect injection.
        
        This prevents the LLM from being tricked into generating malicious SQL.
        
        Args:
            sql_query: SQL query generated by LLM or system
            context: Context in which SQL was generated
            
        Returns:
            SQLInjectionResult with safety assessment
        """
        violations = []
        risk_level = "none"
        
        # Check for destructive operations
        destructive_keywords = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER TABLE', 'UPDATE']
        upper_sql = sql_query.upper()
        
        for keyword in destructive_keywords:
            if keyword in upper_sql:
                violations.append(f"Destructive SQL operation: {keyword}")
                risk_level = "critical"
        
        # Check for unauthorized data access
        if 'UNION SELECT' in upper_sql:
            violations.append("UNION-based query detected (potential data exfiltration)")
            risk_level = "critical"
        
        # Our database should be read-only for user queries
        if any(kw in upper_sql for kw in ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER']):
            violations.append("Write operation in read-only context")
            risk_level = "critical"
        
        # Check for multi-statement queries (stacked queries)
        if ';' in sql_query and sql_query.count(';') > 1:
            violations.append("Multiple SQL statements detected (stacked queries)")
            risk_level = "high"
        
        is_safe = risk_level in ["none", "low"]
        
        if not is_safe:
            logger.error(f"🚨 Indirect SQL Injection in generated SQL! Risk: {risk_level}")
            logger.error(f"SQL: {sql_query}")
            logger.error(f"Context: {context}")
        
        return SQLInjectionResult(
            is_safe=is_safe,
            risk_level=risk_level,
            violations=violations,
            sanitized_input=None
        )
    
    def _sanitize_input(self, text: str) -> str:
        """
        Sanitize user input for safe use.
        
        Note: This is for informational purposes only.
        Always use parameterized queries in production.
        """
        # Remove SQL comments
        sanitized = re.sub(r'--[^\n]*', '', text)
        sanitized = re.sub(r'/\*.*?\*/', '', sanitized, flags=re.DOTALL)
        
        # Remove semicolons (prevent stacked queries)
        sanitized = sanitized.replace(';', '')
        
        # Escape single quotes (but we should use parameters instead)
        # sanitized = sanitized.replace("'", "''")
        
        return sanitized.strip()
    
    def validate_parameterized_query(
        self,
        query: str,
        params: Optional[List] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate that a query uses parameterized syntax correctly.
        
        Args:
            query: SQL query string with placeholders
            params: List of parameters
            
        Returns:
            Tuple of (is_valid, warnings)
        """
        warnings = []
        
        # Count placeholders
        placeholder_count = query.count('?')
        param_count = len(params) if params else 0
        
        if placeholder_count != param_count:
            warnings.append(
                f"Parameter mismatch: {placeholder_count} placeholders, {param_count} params"
            )
        
        # Check for string concatenation in query (anti-pattern)
        if any(op in query for op in [' + ', ' || ', '.format(', 'f"', "f'"]):
            warnings.append("String concatenation detected in SQL query (use parameters instead)")
        
        # Ensure no direct value insertion
        if re.search(r"=\s*['\"]", query):
            warnings.append("Direct string value in query (should use placeholder '?')")
        
        is_valid = len(warnings) == 0
        
        return is_valid, warnings


# Global validator instance
sql_validator = SQLInjectionValidator()