"""
Quick helper to add to chat.py for IRPF calculation detection.
Copy this function into chat.py after the fts_search function.
"""

async def try_irpf_calculation(db, question: str):
    """
    Try to detect and calculate IRPF if query contains amount + location.
    
    Returns dict with formatted answer and sources if successful, None otherwise.
    """
    import re
    from app.utils.irpf_calculator import IRPFCalculator
    from app.utils.region_detector import RegionDetector
    
    question_lower = question.lower()
    
    # Must mention IRPF or related keywords
    if not any(kw in question_lower for kw in ['irpf', 'impuesto', 'renta', 'pagar', 'cuota', 'cuánto', 'pagaré']):
        return None
    
    # Extract amount
    amount_patterns = [
        r'(\d+\.?\d*)\s*(?:mil|k)?\s*(?:€|euros?)',
        r'gan[éeó]\s+(\d+\.?\d*)',
        r'(\d{4,})'  # 4+ digits
    ]
    
    amount = None
    for pattern in amount_patterns:
        match = re.search(pattern, question_lower)
        if match:
            amount_str = match.group(1).replace('.', '').replace(',', '.')
            amount = float(amount_str)
            if 'mil' in match.group(0) or 'k' in match.group(0):
                amount *= 1000
            break
    
    if not amount or amount < 1000:
        return None
    
    # Detect region
    detector = RegionDetector()
    region_info = detector.detect_from_text(question)
    
    if region_info['confidence'] not in ['high', 'medium']:
        return None
    
    ccaa = region_info['region']
    
    # Calculate
    try:
        calculator = IRPFCalculator()
        result = await calculator.calculate_irpf(
            base_liquidable=amount,
            jurisdiction=ccaa,
            year=2024
        )
        await calculator.disconnect()
        
        # Format answer
        answer = f"""**Cálculo Estimado de IRPF 2024**

Para una base liquidable de **{amount:,.0f}€** en **{ccaa}**:

📊 **Desglose del Cálculo:**

• **Cuota Estatal:** {result['cuota_estatal']:,.2f}€
• **Cuota Autonómica ({ccaa}):** {result['cuota_autonomica']:,.2f}€

🎯 **TOTAL IRPF Estimado: {result['cuota_total']:,.2f}€**
   (Tipo medio efectivo: {result['tipo_medio']}%)

---

⚠️ **IMPORTANTE - Disclaimer:**

Este cálculo es una **estimación orientativa** basada únicamente en la base liquidable proporcionada. El IRPF real depende de múltiples factores que NO están incluidos:

**Datos necesarios para un cálculo preciso:**
• Situación familiar (hijos, ascendientes, discapacidad)
• Tipo de rentas (trabajo, actividades, capital, ganancias)
• Cotizaciones y gastos deducibles
• Mínimos personales y familiares
• Deducciones estatales y autonómicas
• Aportaciones a pensiones
• Régimen (individual/conjunta)

**Los {amount:,.0f}€ se asumen como rendimientos brutos anuales** (habitual en nóminas).

**Conclusión:** Para tu cuota exacta, usa el simulador de la AEAT o consulta con un asesor fiscal."""

        from app.routers.chat import Source
        sources = [
            Source(
                id="irpf_calculator",
                source="Escalas IRPF SQL - Cálculo Programático",
                page=0,
                title=f"Escalas IRPF {ccaa} 2024",
                text_preview=f"Cálculo basado en escalas oficiales para {ccaa}"
            )
        ]
        
        return {
            'formatted_answer': answer,
            'sources': sources,
            'cuota_total': result['cuota_total'],
            'jurisdiction': ccaa,
            'base_liquidable': amount
        }
        
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error in IRPF calculation: {e}")
        return None
