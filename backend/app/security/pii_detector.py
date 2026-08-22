"""
PII (Personally Identifiable Information) Detector for TaxIA

Detects and masks sensitive personal information in user inputs
to protect privacy and comply with data protection regulations.
"""

import hashlib
import logging
import re
import time
from dataclasses import dataclass

from app.config import settings  # ← FIX: Import settings at module level

logger = logging.getLogger(__name__)

# Texts longer than this skip the Groq call entirely and go straight to the
# deterministic regex scanner. Reasons:
#   1. Groq `gpt-oss-safeguard-20b` rejects requests over its context window
#      with HTTP 413 (observed in prod logs 2026-05-07).
#   2. Long inputs are usually pasted documents — the regex catches the
#      high-value PII (DNI, IBAN, email, phone) without spending Groq quota.
#   3. Latency: avoids a 2-3s LLM call when the user is just pasting their
#      payslip into chat.
_REGEX_FALLBACK_THRESHOLD = 3000


@dataclass
class PIIDetectionResult:
    """Result of PII detection"""

    has_pii: bool
    detected_types: list[str]
    masked_text: str
    original_text: str
    detections: dict[str, list[str]]


class PIIDetector:
    """
    Detector for Spanish PII patterns.

    Detects:
    - DNI (Documento Nacional de Identidad)
    - NIE (Número de Identidad de Extranjero)
    - Phone numbers (Spanish format)
    - Email addresses
    - IBAN (Spanish bank accounts)
    - Credit/debit card numbers
    - Social Security numbers
    - Passport numbers (solo con la palabra "pasaporte" delante)

    NO detecta códigos postales: ver la nota en ``PII_PATTERNS``.
    """

    # PII patterns for Spanish context
    PII_PATTERNS = {
        "dni": {
            "pattern": r"\b\d{8}\s*[-]?\s*[A-Za-z]\b",
            "mask": "[DNI_OCULTO]",
            "description": "DNI español",
        },
        "nie": {
            "pattern": r"\b[XYZxyz]\s*[-]?\s*\d{7}\s*[-]?\s*[A-Za-z]\b",
            "mask": "[NIE_OCULTO]",
            "description": "NIE extranjero",
        },
        "phone": {
            "pattern": r"\b(?:\+34|0034)?\s*[6789]\d{2}\s*\d{3}\s*\d{3}\b",
            "mask": "[TELEFONO_OCULTO]",
            "description": "Teléfono español",
        },
        "email": {
            "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "mask": "[EMAIL_OCULTO]",
            "description": "Correo electrónico",
        },
        "iban": {
            "pattern": r"\b[A-Z]{2}\d{2}\s*\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\b",
            "mask": "[IBAN_OCULTO]",
            "description": "Cuenta bancaria IBAN",
        },
        "spanish_iban": {
            "pattern": r"\bES\s*\d{2}\s*\d{4}\s*\d{4}\s*\d{2}\s*\d{10}\b",
            "mask": "[IBAN_OCULTO]",
            "description": "IBAN español",
        },
        "credit_card": {
            "pattern": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
            "mask": "[TARJETA_OCULTA]",
            "description": "Tarjeta de crédito/débito",
        },
        "social_security": {
            "pattern": r"\b\d{2}/?\d{8}/?\d{2}\b",
            "mask": "[NSS_OCULTO]",
            "description": "Número Seguridad Social",
        },
        "postal_address": {
            # Detecta la FORMA de una direccion, no un numero suelto: codigo
            # postal + poblacion. Es lo que sustituye al viejo `postal_code`
            # (ver la nota justo debajo).
            #
            # Un CP aislado es indistinguible de un importe; un CP SEGUIDO DE
            # POBLACION no lo es, porque un importe va seguido de su moneda o
            # de una preposicion, no de un nombre propio. De ahi la exclusion
            # explicita de monedas: sin ella "ingresos 30000 Euros anuales"
            # casaba, porque "Euros" tambien es una palabra capitalizada.
            #
            # Medido: 5/5 direcciones detectadas ("Calle Mayor 1, 28013 Madrid",
            # "domicilio: 52001 Melilla", "41013 Sevilla"…) y 0 falsos
            # positivos sobre importes, incluidos "30000 Euros" y
            # "12500 Dolares".
            #
            # Cubre el hueco que dejo quitar `postal_code`: un domicilio
            # completo SIN otro identificador al lado (ni DNI, ni NIE, ni IBAN,
            # ni email, ni telefono) en un texto de mas de 3000 caracteres,
            # donde el regex decide solo porque `detect()` salta el LLM.
            "pattern": (
                r"\b(?:0[1-9]|[1-4]\d|5[0-2])\d{3}\s+"
                r"(?!(?i:euros?|eur|d[oó]lares?|pesetas?|mil(?:es)?)\b)"
                r"[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}"
            ),
            "mask": "[DIRECCION_OCULTA]",
            "description": "Dirección postal",
        },
        # `postal_code` (el CP a secas) ELIMINADO A PROPOSITO. No lo
        # reintroduzcas sin leer esto.
        #
        # Formato oficial: 5 cifras, las dos primeras la provincia (01 Alava …
        # 50 Zaragoza, 51 Ceuta, 52 Melilla) y las tres ultimas
        # encaminamiento/ruta/reparto. El rango estaba BIEN; el problema es que
        # "5 cifras entre 01000 y 52999" describe tambien cualquier importe:
        # 30000 EUR de ingresos, una base de 45000, un gasto de 12500. Un CP y
        # un importe son IDENTICOS como numero.
        #
        # Se intentaron dos vueltas de patron con contexto obligatorio ("CP",
        # "codigo postal") y ninguna aguanta el castellano real de esta app:
        #   - "deuda a c.p. 30000 EUR"                → c/p es CORTO PLAZO
        #   - "deuda a corto plazo (C.P.): 30000 EUR" → el parentesis burla
        #     cualquier lookbehind que descarte el sentido contable
        #   - "Enviar a C.P. 28013"                   → ese lookbehind se come
        #     un codigo postal legitimo
        #   - "CP no consta; renta 30000 EUR"         → el conector tiende un
        #     puente hasta el importe
        # Cada parche abria un agujero por el otro lado. Distinguir "c.p." de
        # corto plazo de "C.P." postal es SEMANTICA, no forma: le toca al LLM,
        # que lee la frase entera y ademas conoce la CCAA del perfil.
        #
        # Decision: un codigo postal AISLADO no identifica a una persona
        # —senala un barrio, no a alguien—, asi que no justifica una capa de
        # regex que rechaza preguntas legitimas. Si aparece junto a datos que
        # SI identifican (DNI, NIE, IBAN, email, telefono, CIF), esos patrones
        # lo cazan igual, y si forma parte de una direccion lo caza
        # `postal_address` de aqui arriba.
        #
        # Resumen: se sustituyo un patron que describia un NUMERO por otro que
        # describe una DIRECCION. Lo primero es ambiguo por definicion; lo
        # segundo tiene forma propia.
        "passport": {
            # CONTEXTO OBLIGATORIO. `[A-Z]{2,3}\d{6,9}` a secas casa con
            # cualquier código de expediente o referencia ("expediente
            # ABC123456", "referencia REC1234567"), moneda corriente en
            # DefensIA, y los rechazaba como PII cuando el regex decide solo.
            #
            # A diferencia del código postal, aquí exigir la etiqueta SÍ
            # resuelve: "pasaporte" no tiene otro significado en castellano, no
            # compite con vocabulario contable. Por eso este patrón se queda y
            # el de `postal_code` se fue.
            #
            # El código queda fuera del `(?i:...)` de las palabras de contexto
            # para que `[A-Z]` siga siendo mayúsculas y no capture texto normal.
            #
            # Ventana de 8 = la longitud EXACTA del conector real más largo
            # (" numero "). Se midió: con 20 casaba
            # "pasaporte caducado; ref ABC123456" y con 12 aún colaba
            # "Pasaporte: s/d; exp ABC123456" — en ambos son dos datos
            # distintos en la misma frase. Bajar de 8 empieza a perder
            # pasaportes de verdad. Si alguien la amplía, que mida antes:
            # este patrón está en `_HIGH_CONFIDENCE_PII` y un falso positivo
            # aquí BLOQUEA aunque el LLM diga que el texto es seguro.
            "pattern": r"\b(?i:pasaporte|passport)[^\d\n]{0,8}?([A-Z]{2,3}\d{6,9})\b",
            "mask": "[PASAPORTE_OCULTO]",
            "description": "Número de pasaporte",
        },
        "cif": {
            "pattern": r"\b[A-HJNP-SUVW]\d{7}[0-9A-J]\b",
            "mask": "[CIF_OCULTO]",
            "description": "CIF empresa",
        },
    }

    # Regex types distinctive enough to override a "safe" verdict from the LLM.
    #
    #   - `passport` SI entra: exige la palabra "pasaporte"/"passport" delante,
    #     asi que ya no confunde codigos de expediente, y un numero de pasaporte
    #     es PII fuerte. Se rechaza aunque el LLM lo diera por seguro.
    #
    #   - `postal_address` NO entra, aunque el patron sea preciso. Una direccion
    #     puede no ser la del usuario: las notificaciones AEAT que procesa
    #     DefensIA llevan la direccion de la propia oficina, y bloquear el
    #     analisis por eso seria absurdo. Distinguir "mi domicilio" de "la sede
    #     de la AEAT" es semantica: le toca al LLM. En la ruta regex-only
    #     (>3000 chars) sigue contando, que es justo el hueco que cubre.
    #
    #   - `postal_code` ya no existe (ver la nota en PII_PATTERNS): un numero de
    #     5 cifras no se puede separar de un importe por su forma.
    _HIGH_CONFIDENCE_PII = frozenset(
        {
            "dni",
            "nie",
            "phone",
            "email",
            "iban",
            "spanish_iban",
            "credit_card",
            "social_security",
            "cif",
            "passport",
        }
    )

    # Per-instance cache cap. Reached → cache cleared. Simple LRU-ish.
    _CACHE_MAX = 2048

    def __init__(self, mask_pii: bool = True, log_detections: bool = True):
        """
        Initialize the PII detector with Groq client.
        """
        from groq import Groq

        self.mask_pii = mask_pii
        self.log_detections = log_detections
        self.client = None
        # Per-instance cache so tests with monkey-patched clients keep their
        # own state (Bug C fix). Hash → result.
        self._cache: dict[str, PIIDetectionResult] = {}

        if settings.GROQ_API_KEY:
            try:
                self.client = Groq(api_key=settings.GROQ_API_KEY)
                logger.info(
                    f"PII Detector initialized with Groq model: {settings.GROQ_MODEL_SAFETY}"
                )
            except Exception as e:
                logger.error(f"Failed to initialize Groq client for PII Detector: {e}")
        else:
            logger.warning("GROQ_API_KEY not found. PII Detection Logic will fail.")

    def _cache_clear(self) -> None:
        """Clear the per-instance cache (used by tests)."""
        self._cache.clear()

    def detect(self, text: str) -> PIIDetectionResult:
        """
        Detect PII in text. Uses Llama Guard / gpt-oss-safeguard for general
        privacy reasoning, deterministic regex for long inputs / fallback,
        and an LRU cache to avoid hammering Groq with repeat traffic.

        Behaviour (Bug C fix, sesion 38):
        - Empty / very short input → fast path, no call.
        - >_REGEX_FALLBACK_THRESHOLD chars → regex-only (avoids 413).
        - Otherwise: cache hit → return cached. Cache miss → call Groq.
        - On 429 (rate limit) → sleep 0.5 s, retry once. On any other error
          or repeat 429 → fall back to regex (so we still catch high-value
          PII instead of failing fully open).
        """
        if not text:
            return PIIDetectionResult(
                has_pii=False,
                detected_types=[],
                masked_text="",
                original_text="",
                detections={},
            )

        # Long inputs: skip Groq, deterministic only.
        if len(text) > _REGEX_FALLBACK_THRESHOLD:
            return self._regex_only(text)

        # Per-instance cache: avoids repeat Groq calls on identical inputs.
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]
        cached = self._cache.get(text_hash)
        if cached is not None:
            return cached

        result = self._detect_uncached(text)

        # Union the LLM verdict with the deterministic regex. The safety model
        # is too lenient in fiscal contexts — "mi DNI es 12345678Z" inside a
        # tax question came back as safe. If Groq cleared the text but the
        # regex finds high-confidence Spanish PII, the regex wins.
        #
        # Groq still runs first so its richer categories (S7 etc.) are
        # preserved and the 413/429 fallback path is untouched.
        if not result.has_pii:
            regex_result = self._regex_only(text)
            if any(t in self._HIGH_CONFIDENCE_PII for t in regex_result.detections):
                result = regex_result

        if len(self._cache) >= self._CACHE_MAX:
            # Simple LRU-ish: drop the oldest half. Avoids unbounded growth
            # without the overhead of an OrderedDict / functools wrapper.
            for k in list(self._cache.keys())[: self._CACHE_MAX // 2]:
                self._cache.pop(k, None)
        self._cache[text_hash] = result
        return result

    def _detect_uncached(self, text: str) -> PIIDetectionResult:
        """The Groq-backed path, separated from caching."""
        if not self.client:
            # NO degradar aqui a `_regex_only`. Parece fail-open y no lo es:
            # quien llama es `detect()`, que al ver has_pii=False ejecuta el
            # regex por su cuenta y deja mandar solo a `_HIGH_CONFIDENCE_PII`.
            # Sin cliente Groq, un DNI / NIE / IBAN / email / telefono / CIF
            # SIGUE detectandose; lo unico que no bloquea son los patrones
            # ambiguos, que es exactamente lo que se quiere.
            #
            # Llamar a `_regex_only` desde aqui haria contar TODOS los patrones
            # y convertiria los ambiguos en bloqueantes (un expediente
            # "ABC123456" pasaria a rechazarse como pasaporte).
            return PIIDetectionResult(
                has_pii=False,
                detected_types=["GROQ_CLIENT_MISSING"],
                masked_text=text,
                original_text=text,
                detections={},
            )

        try:
            completion = self.client.chat.completions.create(
                model=settings.GROQ_MODEL_SAFETY,
                messages=[{"role": "user", "content": text}],
                temperature=0.0,
            )
        except Exception as e:
            err_str = str(e)
            if "429" in err_str:
                # Free-tier shared with LlamaGuard. One sync retry buys us
                # the difference; if it fails again we fall back to regex
                # so we still catch DNI / IBAN / email instead of fail-open.
                time.sleep(0.5)
                try:
                    completion = self.client.chat.completions.create(
                        model=settings.GROQ_MODEL_SAFETY,
                        messages=[{"role": "user", "content": text}],
                        temperature=0.0,
                    )
                except Exception as e2:
                    logger.warning(f"PII Detector 429 retry failed, regex fallback: {e2}")
                    return self._regex_only(text)
            else:
                # Includes 413 request-too-large from gpt-oss-safeguard-20b
                # when the input is just under the threshold but still big.
                logger.warning(f"PII Detector API error, regex fallback: {e}")
                return self._regex_only(text)

        try:
            response = completion.choices[0].message.content.strip()

            # Support both Llama Guard format ("unsafe\nS7") and
            # gpt-oss-safeguard-20b format (empty = safe, refusal text = unsafe)
            response_lower = response.lower()
            if not response:
                # Empty response = safe (gpt-oss-safeguard-20b)
                is_unsafe = False
            elif response_lower.startswith("unsafe") and "S7" in response:
                # Llama Guard format with specific S7 category
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

            detected_types = ["PII (Privacy Violation S7)"] if is_unsafe else []

            if is_unsafe and self.log_detections:
                logger.warning(f"PII detected by moderation model: {response}")

            return PIIDetectionResult(
                has_pii=is_unsafe,
                detected_types=detected_types,
                masked_text="[PII REMOVED BY AI]" if (is_unsafe and self.mask_pii) else text,
                original_text=text,
                detections={"S7": ["[Content Blocked]"]} if is_unsafe else {},
            )

        except Exception as e:
            logger.warning(f"PII Detector parse error, regex fallback: {e}")
            return self._regex_only(text)

    def _regex_only(self, text: str) -> PIIDetectionResult:
        """Deterministic-only PII scan using ``self.PII_PATTERNS``.

        Used when:
        - Input exceeds Groq context window (length guard).
        - Groq returns 413 / 429 (after retry) / any other API error.

        Catches the high-value Spanish PII (DNI, NIE, IBAN, email, phone, CIF)
        which is what the prompt-injection regex layer also relies on. Not
        as nuanced as the LLM but never fails open silently.
        """
        detected: dict[str, list[str]] = {}
        masked = text
        detected_types: list[str] = []

        for pii_type, cfg in self.PII_PATTERNS.items():
            try:
                matches = re.findall(cfg["pattern"], text)
            except re.error:
                continue
            if matches:
                detected[pii_type] = (
                    matches if isinstance(matches[0], str) else [str(m) for m in matches]
                )
                detected_types.append(cfg["description"])
                if self.mask_pii:
                    masked = re.sub(cfg["pattern"], cfg["mask"], masked)

        return PIIDetectionResult(
            has_pii=bool(detected),
            detected_types=detected_types,
            masked_text=masked if self.mask_pii else text,
            original_text=text,
            detections=detected,
        )

    def mask(self, text: str) -> str:
        """
        Mask all PII in text.

        Args:
            text: Text to mask

        Returns:
            Text with PII masked
        """
        result = self.detect(text)
        return result.masked_text

    def validate(self, text: str) -> tuple[bool, str, list[str]]:
        """
        Validate text for PII presence.

        Args:
            text: Text to validate

        Returns:
            Tuple of (has_pii, masked_text, detected_types)
        """
        result = self.detect(text)
        return result.has_pii, result.masked_text, result.detected_types


# Global instance
pii_detector = PIIDetector(mask_pii=True, log_detections=True)
