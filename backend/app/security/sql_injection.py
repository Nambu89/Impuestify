"""
SQL Injection Prevention for TaxIA

Capa 4 del `security_pipeline`. Es **defensa en profundidad**, no el control
principal: la protección de verdad son las consultas parametrizadas
(`WHERE email = ?`), regla número 1 del proyecto. Esto solo mira el texto que
el usuario manda al chat.

Cómo decide, en orden:

1. `_regex_only()` — patrones deterministas que NO aparecen en castellano
   fiscal (`UNION SELECT`, `; DROP TABLE`, `' OR '1'='1`…). Corren siempre que
   el LLM no esté disponible.
2. Groq (`gpt-oss-safeguard-20b`, categoría S14) para el resto.

Sin cliente Groq o ante un error de API se degrada a (1). NUNCA devuelve
"seguro" sin haber mirado nada: eso era el fail-open que se arregló el
2026-08-22.

OJO — código muerto pendiente de limpiar (no lo llama nadie, verificado en todo
el repo): `DANGEROUS_KEYWORDS`, `_sanitize_input()`, `validate_generated_sql()`
y `validate_parameterized_query()`. Dan la impresión de que aquí hay más capas
de las que se ejecutan. Se dejan fuera de este arreglo para no mezclarlo con una
limpieza.
"""

import logging
import re
from urllib.parse import unquote

from pydantic import BaseModel, Field

from app.config import settings  # ← FIX: Import settings at module level

logger = logging.getLogger(__name__)


class SQLInjectionResult(BaseModel):
    """Result of SQL injection check"""

    is_safe: bool
    risk_level: str = Field(description="none, low, medium, high, critical")
    violations: list[str] = Field(default_factory=list)
    sanitized_input: str | None = None


class SQLInjectionValidator:
    """
    Validates inputs and generated SQL for injection attacks.

    Implements OWASP recommendations for SQL injection prevention.
    """

    # Dangerous SQL keywords that should trigger alerts
    DANGEROUS_KEYWORDS = [
        # Data manipulation
        "DROP",
        "DELETE",
        "TRUNCATE",
        "ALTER",
        "CREATE",
        # Access control
        "GRANT",
        "REVOKE",
        # System functions
        "EXEC",
        "EXECUTE",
        "SYSTEM",
        "SHELL",
        # Union-based injection
        "UNION SELECT",
        # Comment-based injection
        "--",
        "/*",
        "*/",
        "#",
        # Stacked queries
        ";DROP",
        ";DELETE",
        ";UPDATE",
    ]

    # Patrones que pueden BLOQUEAR por sí solos, sin veredicto del LLM.
    #
    # El criterio para entrar aquí es uno: que la cadena no aparezca en
    # castellano fiscal. Se midió contra texto real de la app y estos cinco
    # quedaron FUERA por ruidosos —cada uno rechazaba una consulta legítima:
    #
    #   r"(--[^\n]*)"          "El IRPF -- que es progresivo -- sube"
    #   r"(/\*.*?\*/)"         "La casilla 0505 /* la de rendimientos */"
    #   r"(\bCHAR\s*\()"       "CHAR( es una funcion de Excel que uso"
    #   r"(\bHEX\s*\()"        misma familia
    #   r"(0x[0-9a-fA-F]+)"    "El codigo hex 0x1F aparece en el fichero"
    #
    # Es la misma leccion que el Bug 114 con el codigo postal: un patron que
    # describe una forma compartida por texto legitimo no puede bloquear. Esos
    # cinco los sigue evaluando el LLM, que ve la frase entera.
    # Los patrones son ESTRUCTURALES, no cadenas literales. Una primera version
    # enumeraba ejemplos de manual (`UNION SELECT`, `' OR '1'='1`) y 8 de 9
    # evasiones triviales la esquivaban: `' OR 'x'='x`, `UNION ALL SELECT`,
    # `UNION/**/SELECT`, `; DELETE FROM`, `OR TRUE`, `pg_sleep(`… Enumerar
    # ejemplos da cobertura aparente; hay que describir la FORMA del ataque.
    _BLOCKING_PATTERNS = [
        re.compile(p, re.IGNORECASE)
        for p in (
            # Tautologia con comillas: cubre '1'='1, 'x'='x, ' OR 1=1
            r"'\s*OR\s*['\"]?[\w']+['\"]?\s*=\s*['\"]?[\w']+",
            r"\bOR\b\s+\d+\s*=\s*\d+",  # boolean-based blind
            r"\bOR\b\s+(?:TRUE|FALSE)\b",  # variante sin comillas
            # UNION [ALL] SELECT, admitiendo comentario intercalado como
            # separador (UNION/**/SELECT es la evasion clasica)
            r"\bUNION\b(?:\s|/\*.*?\*/)+(?:ALL(?:\s|/\*.*?\*/)+)?SELECT\b",
            # Stacked queries: no solo DROP
            r";\s*(?:DROP|DELETE|UPDATE|INSERT|TRUNCATE|ALTER|CREATE)\b",
            r"\bWAITFOR\s+DELAY\b",  # time-based blind
            r"\b(?:PG_)?SLEEP\s*\(",  # time-based (MySQL y PostgreSQL)
            r"\bBENCHMARK\s*\(",  # time-based MySQL
            r"\bLOAD_FILE\s*\(",  # lectura de ficheros
            r"\bINTO\s+(?:OUT|DUMP)FILE\b",  # escritura de ficheros
        )
    ]

    def __init__(self):
        """
        Initialize the SQL injection validator with Groq client.
        """
        from groq import Groq

        self.client = None
        if settings.GROQ_API_KEY:
            try:
                self.client = Groq(api_key=settings.GROQ_API_KEY)
                logger.info(
                    f"✅ SQL Injection Validator initialized with Groq model: {settings.GROQ_MODEL_SAFETY}"
                )
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
            # Sin LLM NO se puede concluir "seguro": eso era fail-open total.
            # A diferencia del detector de PII —donde `detect()` corre el regex
            # por su cuenta y hay red de seguridad aguas arriba—, aquí el
            # pipeline llama a esta función y se fía del resultado. Comprobado.
            return self._regex_only(user_input, marker="GROQ_CLIENT_MISSING")

        try:
            from app.config import settings

            completion = self.client.chat.completions.create(
                model=settings.GROQ_MODEL_SAFETY,
                messages=[{"role": "user", "content": user_input}],
                temperature=0.0,
            )

            response = completion.choices[0].message.content.strip()

            # Support both Llama Guard format ("unsafe\nS14") and
            # gpt-oss-safeguard-20b format (empty = safe, refusal text = unsafe)
            response_lower = response.lower()
            if not response:
                # Empty response = safe (gpt-oss-safeguard-20b)
                is_unsafe = False
            elif response_lower.startswith("unsafe") and "S14" in response:
                # Llama Guard format with specific S14 category
                is_unsafe = True
            elif response_lower.startswith("safe"):
                is_unsafe = False
            else:
                # Natural language refusal = model considers content unsafe
                refusal_indicators = [
                    "i'm sorry",
                    "i cannot",
                    "i can't",
                    "cannot help",
                    "can't help",
                    "unable to",
                ]
                is_unsafe = any(ind in response_lower for ind in refusal_indicators)

            violations = []
            if is_unsafe:
                violations.append("AI Detected: Code Interpreter Abuse / SQL Injection (S14)")
                logger.warning(f"🚨 SQL Injection detected by moderation model: {response}")

            return SQLInjectionResult(
                is_safe=not is_unsafe,
                risk_level="critical" if is_unsafe else "low",
                violations=violations,
                sanitized_input=user_input,
            )

        except Exception as e:
            # Mismo criterio que arriba, y esta rama importa MÁS: un 429 o un
            # timeout de Groq es mucho más frecuente que una API key ausente,
            # así que este era el fail-open que se dispararía en producción.
            logger.error(f"❌ SQL Validator API Error: {e}")
            return self._regex_only(user_input, marker=f"API_ERROR: {e}")

    def _regex_only(self, user_input: str, *, marker: str) -> SQLInjectionResult:
        """Veredicto determinista para cuando el LLM no está disponible.

        Solo usa `_BLOCKING_PATTERNS`, que son los que no aparecen en castellano
        fiscal. Si no encuentra nada devuelve `is_safe=True`, pero habiendo
        mirado — que es la diferencia con el fail-open anterior.

        `marker` deja en `violations` POR QUÉ se degradó, para que la caída del
        LLM sea visible en los logs en vez de silenciosa.
        """
        # Se analiza el texto crudo Y su version url-decodificada: `%27%20OR%201%3D1`
        # esquivaba todos los patrones. Decodificar no introduce falsos positivos
        # con texto fiscal —"IVA 21%" o "100% deducible" no son escapes validos y
        # `unquote` los deja tal cual—, pero cierra la evasion por codificacion.
        candidatos = {user_input, unquote(user_input)}
        matched = [
            p.pattern for p in self._BLOCKING_PATTERNS if any(p.search(c) for c in candidatos)
        ]

        if not matched:
            return SQLInjectionResult(
                is_safe=True,
                risk_level="low",
                violations=[marker],
                sanitized_input=user_input,
            )

        logger.warning(f"🚨 SQL Injection detectada por regex (LLM no disponible: {marker})")
        return SQLInjectionResult(
            is_safe=False,
            # "critical" a propósito: el pipeline solo rechaza con
            # risk_level in ("high", "critical").
            risk_level="critical",
            violations=[f"Regex determinista: {len(matched)} patrón(es) SQLi", marker],
            sanitized_input=user_input,
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
        destructive_keywords = ["DROP", "DELETE", "TRUNCATE", "ALTER TABLE", "UPDATE"]
        upper_sql = sql_query.upper()

        for keyword in destructive_keywords:
            if keyword in upper_sql:
                violations.append(f"Destructive SQL operation: {keyword}")
                risk_level = "critical"

        # Check for unauthorized data access
        if "UNION SELECT" in upper_sql:
            violations.append("UNION-based query detected (potential data exfiltration)")
            risk_level = "critical"

        # Our database should be read-only for user queries
        if any(kw in upper_sql for kw in ["INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER"]):
            violations.append("Write operation in read-only context")
            risk_level = "critical"

        # Check for multi-statement queries (stacked queries)
        if ";" in sql_query and sql_query.count(";") > 1:
            violations.append("Multiple SQL statements detected (stacked queries)")
            risk_level = "high"

        is_safe = risk_level in ["none", "low"]

        if not is_safe:
            logger.error(f"🚨 Indirect SQL Injection in generated SQL! Risk: {risk_level}")
            logger.error(f"SQL: {sql_query}")
            logger.error(f"Context: {context}")

        return SQLInjectionResult(
            is_safe=is_safe, risk_level=risk_level, violations=violations, sanitized_input=None
        )

    def _sanitize_input(self, text: str) -> str:
        """
        Sanitize user input for safe use.

        Note: This is for informational purposes only.
        Always use parameterized queries in production.
        """
        # Remove SQL comments
        sanitized = re.sub(r"--[^\n]*", "", text)
        sanitized = re.sub(r"/\*.*?\*/", "", sanitized, flags=re.DOTALL)

        # Remove semicolons (prevent stacked queries)
        sanitized = sanitized.replace(";", "")

        # Escape single quotes (but we should use parameters instead)
        # sanitized = sanitized.replace("'", "''")

        return sanitized.strip()

    def validate_parameterized_query(
        self, query: str, params: list | None = None
    ) -> tuple[bool, list[str]]:
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
        placeholder_count = query.count("?")
        param_count = len(params) if params else 0

        if placeholder_count != param_count:
            warnings.append(
                f"Parameter mismatch: {placeholder_count} placeholders, {param_count} params"
            )

        # Check for string concatenation in query (anti-pattern)
        if any(op in query for op in [" + ", " || ", ".format(", 'f"', "f'"]):
            warnings.append("String concatenation detected in SQL query (use parameters instead)")

        # Ensure no direct value insertion
        if re.search(r"=\s*['\"]", query):
            warnings.append("Direct string value in query (should use placeholder '?')")

        is_valid = len(warnings) == 0

        return is_valid, warnings


# Global validator instance
sql_validator = SQLInjectionValidator()
