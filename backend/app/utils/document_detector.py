"""
Document Type Detector

Detects whether a PDF is a payslip, AEAT notification, or other document type.
Uses LLM to analyze document content and classify it.
"""
import logging
from typing import Dict
from openai import OpenAI
import os

logger = logging.getLogger(__name__)


class DocumentDetector:
    """Detects document type using LLM analysis"""
    
    def __init__(self):
        """Initialize with OpenAI client"""
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.model = "gpt-5-mini"  # Fast and accurate for classification
    
    async def detect_type(self, pdf_text: str, max_chars: int = 3000) -> Dict:
        """
        Detect document type from PDF text.
        
        Args:
            pdf_text: Extracted text from PDF (first 2 pages recommended)
            max_chars: Maximum characters to analyze (default: 3000)
            
        Returns:
            {
                "type": "payslip" | "aeat_notification" | "other",
                "confidence": 0.0-1.0,
                "reasoning": "Explanation of classification",
                "detected_keywords": ["keyword1", "keyword2", ...]
            }
        """
        try:
            # Truncate text to avoid token limits
            text_sample = pdf_text[:max_chars]
            
            # Create classification prompt
            prompt = f"""Analiza el siguiente texto extraído de un PDF y clasifícalo en UNA de estas categorías:

1. **payslip** (nómina): Documento que muestra el salario de un empleado
   - Keywords típicos: "nómina", "salario base", "devengos", "deducciones", "líquido a percibir", "cotización", "IRPF", "seguridad social", "empresa", "trabajador", "periodo de liquidación"
   
2. **aeat_notification** (notificación de Hacienda): Comunicación oficial de la Agencia Tributaria
   - Keywords típicos: "AEAT", "Agencia Tributaria", "notificación", "requerimiento", "providencia", "apremio", "liquidación", "sanción", "NIF", "expediente", "plazo", "alegaciones"
   
3. **other** (otro tipo de documento): Cualquier otro documento

**TEXTO DEL DOCUMENTO:**
```
{text_sample}
```

**INSTRUCCIONES:**
1. Lee el texto cuidadosamente
2. Identifica keywords clave que indiquen el tipo
3. Clasifica en UNA categoría
4. Asigna confianza (0.0-1.0):
   - 0.9-1.0: Muy seguro (muchos keywords específicos)
   - 0.7-0.9: Seguro (varios keywords relevantes)
   - 0.5-0.7: Moderado (algunos keywords, pero ambiguo)
   - 0.0-0.5: Inseguro (pocos o ningún keyword claro)

**RESPONDE EN FORMATO JSON:**
{{
    "type": "payslip" | "aeat_notification" | "other",
    "confidence": 0.85,
    "reasoning": "Breve explicación de por qué clasificaste así",
    "detected_keywords": ["keyword1", "keyword2", "keyword3"]
}}
"""
            
            # Call OpenAI
            logger.info("🔍 Detecting document type with LLM...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un experto en clasificación de documentos fiscales y laborales españoles. Respondes SOLO en formato JSON válido."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=1,  # Required for gpt-5-mini
                max_completion_tokens=300,  # gpt-5-mini uses max_completion_tokens, not max_tokens
                response_format={"type": "json_object"}
            )
            
            # Parse response
            import json
            result = json.loads(response.choices[0].message.content)
            
            logger.info(f"✅ Document classified as: {result['type']} (confidence: {result['confidence']})")
            logger.info(f"   Keywords detected: {result.get('detected_keywords', [])}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error detecting document type: {e}", exc_info=True)
            # Return safe default
            return {
                "type": "other",
                "confidence": 0.0,
                "reasoning": f"Error during classification: {str(e)}",
                "detected_keywords": []
            }
    
    def should_ask_user(self, detection_result: Dict) -> bool:
        """
        Determine if we should ask user to clarify document type.
        
        Args:
            detection_result: Result from detect_type()
            
        Returns:
            True if confidence is too low and we should ask user
        """
        confidence = detection_result.get("confidence", 0.0)
        doc_type = detection_result.get("type", "other")
        
        # Ask user if:
        # 1. Confidence < 0.7, OR
        # 2. Type is "other"
        return confidence < 0.7 or doc_type == "other"
