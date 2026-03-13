"""
PII (Personally Identifiable Information) Detector for TaxIA

Detects and masks sensitive personal information in user inputs
to protect privacy and comply with data protection regulations.
"""
import re
import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass

from app.config import settings  # ← FIX: Import settings at module level

logger = logging.getLogger(__name__)


@dataclass
class PIIDetectionResult:
    """Result of PII detection"""
    has_pii: bool
    detected_types: List[str]
    masked_text: str
    original_text: str
    detections: Dict[str, List[str]]


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
    - Postal codes
    """
    
    # PII patterns for Spanish context
    PII_PATTERNS = {
        "dni": {
            "pattern": r"\b\d{8}\s*[-]?\s*[A-Za-z]\b",
            "mask": "[DNI_OCULTO]",
            "description": "DNI español"
        },
        "nie": {
            "pattern": r"\b[XYZxyz]\s*[-]?\s*\d{7}\s*[-]?\s*[A-Za-z]\b",
            "mask": "[NIE_OCULTO]",
            "description": "NIE extranjero"
        },
        "phone": {
            "pattern": r"\b(?:\+34|0034)?\s*[6789]\d{2}\s*\d{3}\s*\d{3}\b",
            "mask": "[TELEFONO_OCULTO]",
            "description": "Teléfono español"
        },
        "email": {
            "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "mask": "[EMAIL_OCULTO]",
            "description": "Correo electrónico"
        },
        "iban": {
            "pattern": r"\b[A-Z]{2}\d{2}\s*\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\b",
            "mask": "[IBAN_OCULTO]",
            "description": "Cuenta bancaria IBAN"
        },
        "spanish_iban": {
            "pattern": r"\bES\s*\d{2}\s*\d{4}\s*\d{4}\s*\d{2}\s*\d{10}\b",
            "mask": "[IBAN_OCULTO]",
            "description": "IBAN español"
        },
        "credit_card": {
            "pattern": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
            "mask": "[TARJETA_OCULTA]",
            "description": "Tarjeta de crédito/débito"
        },
        "social_security": {
            "pattern": r"\b\d{2}/?\d{8}/?\d{2}\b",
            "mask": "[NSS_OCULTO]",
            "description": "Número Seguridad Social"
        },
        "postal_code": {
            "pattern": r"\b(?:0[1-9]|[1-4]\d|5[0-2])\d{3}\b",
            "mask": "[CP_OCULTO]",
            "description": "Código Postal"
        },
        "passport": {
            "pattern": r"\b[A-Z]{2,3}\d{6,9}\b",
            "mask": "[PASAPORTE_OCULTO]",
            "description": "Número de pasaporte"
        },
        "cif": {
            "pattern": r"\b[A-HJNP-SUVW]\d{7}[0-9A-J]\b",
            "mask": "[CIF_OCULTO]",
            "description": "CIF empresa"
        },
    }
    
    def __init__(self, mask_pii: bool = True, log_detections: bool = True):
        """
        Initialize the PII detector with Groq client.
        """
        from groq import Groq
        from app.config import settings
        
        self.mask_pii = mask_pii
        self.log_detections = log_detections
        self.client = None
        
        if settings.GROQ_API_KEY:
            try:
                self.client = Groq(api_key=settings.GROQ_API_KEY)
                logger.info(f"✅ PII Detector initialized with Groq model: {settings.GROQ_MODEL_SAFETY}")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Groq client for PII Detector: {e}")
        else:
            logger.warning("⚠️ GROQ_API_KEY not found. PII Detection Logic will fail.")

    def detect(self, text: str) -> PIIDetectionResult:
        """
        Detect PII in text using Llama Guard 4 (Category S7: Privacy).
        """
        if not text:
            return PIIDetectionResult(has_pii=False, detected_types=[], masked_text="", original_text="", detections={})

        if not self.client:
             return PIIDetectionResult(
                 has_pii=False, 
                 detected_types=["GROQ_CLIENT_MISSING"], 
                 masked_text=text, 
                 original_text=text,
                 detections={}
             )

        try:
            from app.config import settings
            
            # Use Llama Guard 4 to detect S7 (Privacy)
            completion = self.client.chat.completions.create(
                model=settings.GROQ_MODEL_SAFETY,
                messages=[{"role": "user", "content": text}],
                temperature=0.0
            )
            
            response = completion.choices[0].message.content.strip()
            
            # Llama Guard Check
            is_unsafe = "unsafe" in response.lower() and "S7" in response
            
            detected_types = ["PII (Privacy Violation S7)"] if is_unsafe else []
            
            if is_unsafe and self.log_detections:
                 logger.warning(f"🚨 PII detected by Llama Guard: {response}")

            return PIIDetectionResult(
                has_pii=is_unsafe,
                detected_types=detected_types,
                masked_text="[PII REMOVED BY AI]" if (is_unsafe and self.mask_pii) else text,
                original_text=text,
                detections={"S7": ["[Content Blocked]"]} if is_unsafe else {}
            )

        except Exception as e:
            logger.error(f"❌ PII Detector API Error: {e}")
            return PIIDetectionResult(has_pii=False, detected_types=[f"API_ERROR: {str(e)}"], masked_text=text, original_text=text, detections={})
    
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
    
    def validate(self, text: str) -> Tuple[bool, str, List[str]]:
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
