# Aviso de Transparencia - Sistema de Inteligencia Artificial

**Reglamento (UE) 2024/1689 del Parlamento Europeo - AI Act**  
**Artículo 52: Obligaciones de Transparencia**

**Última actualización**: 3 de enero de 2026  
**Versión**: 1.0

---

## 🤖 1. Declaración de Uso de IA

**Impuestify utiliza un sistema de inteligencia artificial** para responder a sus consultas fiscales.

**Por qué es importante saberlo**:
- La IA puede cometer errores o "alucinar" información
- No sustituye el asesoramiento profesional
- Debe verificar información importante con un asesor fiscal

---

## 📋 2. Información del Sistema de IA

### 2.1 Proveedor del Sistema

| Componente | Proveedor | Versión |
|------------|-----------|---------|
| **Modelo de lenguaje** | OpenAI | GPT-4o-mini / GPT-5-mini |
| **Moderación de contenido** | Meta (via Groq) | Llama Guard 4 |
| **Orquestador** | Microsoft | Agent Framework 1.0.0 |

### 2.2 Propósito del Sistema

Impuestify es un **asistente fiscal conversacional** que:
- ✅ Responde preguntas sobre normativa fiscal española
- ✅ Calcula IRPF y cuotas de autónomos
- ✅ Analiza nóminas y notificaciones AEAT
- ✅ Busca información en fuentes oficiales (AEAT, BOE)

### 2.3 Clasificación según AI Act

**Categoría**: Sistema de IA de **RIESGO LIMITADO** (Art. 52)

**Por qué**:
- Interactúa directamente con usuarios mediante chat
- Genera contenido que influye en decisiones (aunque no las toma)
- NO es de alto riesgo (no afecta derechos fundamentales ni seguridad)

---

## ⚙️ 3. Cómo Funciona el Sistema

### 3.1 Arquitectura Multi-Agente

```
Usuario hace pregunta
    ↓
Router (CoordinatorAgent)
    ↓
┌─────────────┴───────────────┐
│                              │
TaxAgent                  PayslipAgent
(Consultas generales)    (Análisis nóminas)
    ↓                          ↓
Herramientas especializadas:
- calculate_irpf: Cálculo IRPF
- search_regulations: Búsqueda web AEAT
- analyze_payslip: Análisis PDF nóminas
    ↓
Respuesta al usuario
```

### 3.2 RAG (Retrieval-Augmented Generation)

**Paso 1**: Tu pregunta se procesa para buscar información relevante  
**Paso 2**: El sistema busca en documentación oficial (AEAT, BOE, SS)  
**Paso 3**: La IA genera respuesta basada en fuentes encontradas  
**Paso 4**: Se citan las fuentes utilizadas

**Beneficio**: Reduce alucinaciones y proporciona trazabilidad.

### 3.3 Moderación de Contenido (Llama Guard 4)

Antes de procesar tu consulta, validamos que:
- ❌ No contenga lenguaje tóxico o abusivo
- ❌ No solicite evasión fiscal
- ❌ No incluya contenido inapropiado

**Si se detecta contenido prohibido**: El sistema rechaza la consulta.

---

## 🎯 4. Capacidades del Sistema

### ✅ Qué puede hacer

1. **Responder preguntas fiscales** sobre normativa española:
   - IRPF, IVA, Sociedades
   - Cuotas de autónomos
   - Deducciones fiscales
   - Plazos y obligaciones

2. **Realizar cálculos**:
   - IRPF por tramos y CCAA
   - Cuotas de autónomos según rendimientos
   - Proyecciones anuales de nóminas

3. **Analizar documentos PDF**:
   - Nóminas (salarios, retenciones, SS)
   - Notificaciones AEAT (importes, plazos)

4. **Buscar información actualizada**:
   - Web scraping de AEAT, BOE, Seguridad Social
   - Documentos oficiales en BD vectorial

### ❌ Qué NO puede hacer

1. **NO realiza gestiones fiscales**:
   - No presenta declaraciones en tu nombre
   - No accede a la Sede Electrónica AEAT

2. **NO toma decisiones por ti**:
   - Es un asistente, no un decisor
   - Siempre requiere tu validación

3. **NO sustituye a un asesor fiscal**:
   - No ofrece asesoramiento legal vinculante
   - No se responsabiliza de decisiones fiscales

4. **NO garantiza exactitud al 100%**:
   - Puede cometer errores (ver sección 5)

---

## ⚠️ 5. Limitaciones y Riesgos Conocidos

### 5.1 Alucinaciones de IA

**Qué son**: La IA puede generar información plausible pero **incorrecta**.

**Mitigación aplicada**:
- ✅ RAG: Respuestas basadas en fuentes documentadas
- ✅ Citación de fuentes: Siempre se indican referencias
- ✅ Disclaimers: Recordatorios de verificar con asesor

**Recomendación**: **Siempre verifica** información crítica con asesor fiscal.

### 5.2 Información Desactualizada

**Riesgo**: Normativa fiscal cambia frecuentemente.

**Mitigación**:
- ✅ Búsqueda web en tiempo real (tool: search_regulations)
- ✅ Fecha de actualización en documentación
- ✅ Disclaimer de "información orientativa"

**Recomendación**: Verifica fechas de las fuentes citadas.

### 5.3 Interpretación de Casos Complejos

**Riesgo**: La IA puede simplificar excesivamente situaciones complejas.

**Mitigación**:
- ✅ Complejidad de query clasificada automáticamente
- ✅ Reasoning effort ajustado (simple/moderate/complex)
- ✅ Recomendación de consultar asesor en casos complejos

**Recomendación**: Para situaciones personales complejas, **consulta asesor**.

### 5.4 Sesgo en Respuestas

**Riesgo**: El modelo puede tener sesgos implícitos.

**Mitigación**:
- ✅ Prompts diseñados para objetividad
- ✅ Basados en normativa oficial, no opiniones
- ✅ Moderación de contenido (Llama Guard 4)

### 5.5 Privacidad de Datos

**Riesgo**: Datos sensibles enviados al modelo.

**Mitigación**:
- ✅ OpenAI no usa datos de API para training
- ✅ DPA (Data Processing Agreement) firmado
- ✅ Cifrado TLS en tránsito
- ✅ Logs auditables

**Ver**: [PRIVACY_POLICY.md](./PRIVACY_POLICY.md)

---

## 👤 6. Supervisión Humana Requerida

**Impuestify NO toma decisiones automatizadas** que produzcan efectos jurídicos (RGPD Art. 22).

### El usuario SIEMPRE debe:

1. ✅ **Revisar** las respuestas de la IA
2. ✅ **Verificar** fuentes citadas
3. ✅ **Consultar** con asesor fiscal para decisiones importantes
4. ✅ **Validar** cálculos antes de usarlos

### Disclaimers Automáticos

Todas las respuestas incluyen:
> ⚠️ **Información orientativa**. Consulta con un asesor fiscal para tu caso particular.

---

## 🔒 7. Medidas de Seguridad

### 7.1 Protección contra Jailbreaking

**Qué es**: Intentos de hackear la IA para generar contenido prohibido.

**Protección**:
- ✅ Llama Guard 4: Moderación antes de procesar
- ✅ Guardrails: Validación de outputs
- ✅ Blocklist: Patrones de jailbreak conocidos

### 7.2 Anti-Inyección de Prompts

**Qué es**: Manipular la IA mediante instrucciones maliciosas.

**Protección**:
- ✅ Separación de contexto usuario vs. system prompt
- ✅ Validación de inputs
- ✅ Sanitización de contenido

### 7.3 Rate Limiting

**Protección contra abuso**:
- ✅ Límites por usuario y IP
- ✅ Bloqueo automático tras violaciones
- ✅ Protección DDoS

---

## 📊 8. Calidad y Precisión

### 8.1 Métricas de Rendimiento

| Métrica | Objetivo | Estado Actual |
|---------|----------|---------------|
| **Precisión respuestas** | >90% | ✅ Monit oreado |
| **Rate de alucinaciones** | <5% | ✅ Con RAG |
| **Tiempo de respuesta** | <10s | ✅ Cache activo |
| **Satisfacción usuario** | >4/5 | 📊 En medición |

### 8.2 Mejora Continua

- ✅ Logs de auditoría para análisis de calidad
- ✅ Feedback de usuarios (próximamente)
- ✅ Actualizaciones de documentación periódicas

---

## 🐛 9. Reporte de Errores o Comportamiento Inapropiado

### Si la IA:
- ❌ Proporciona información claramente incorrecta
- ❌ Genera contenido inapropiado
- ❌ No funciona correctamente

### Cómo reportar:

1. **Email**: report@impuestify.com
2. **Incluir**:
   - Pregunta realizada
   - Respuesta recibida
   - Por qué es problemático
3. **Respuesta**: Máximo 48 horas

---

## ⚖️ 10. Cumplimiento Normativo

Impuestify cumple con:

| Normativa | Descripción | Compliance |
|-----------|-------------|-----------|
| **AI Act (UE 2024/1689)** | Ley de IA europea | ✅ Art. 52 |
| **RGPD (UE 2016/679)** | Protección de datos | ✅ Full |
| **LOPDGDD (España)** | Protección datos España | ✅ Sí |
| **LSSI (Ley 34/2002)** | Servicios digitales | ✅ Sí |

---

## 11. Derechos del Usuario

Tiene derecho a (RGPD Art. 15-22):
- ✅ Saber qué datos procesa la IA
- ✅ Acceder a sus conversaciones
- ✅ Eliminar su cuenta y datos
- ✅ No ser objeto de decisiones automatizadas

**Ver**: [PRIVACY_POLICY.md](./PRIVACY_POLICY.md)

---

## 📞 12. Contacto

**Dudas sobre IA**: ai-transparency@impuestify.com  
**Reporte de errores**: report@impuestify.com  
**Privacidad**: privacy@impuestify.com  
**Soporte general**: support@impuestify.com

---

## 13. Actualizaciones

**Esta información se actualiza regularmente**.

**Versión actual**: 1.0 (3 enero 2026)  
**Próxima revisión**: Trimestral

Cambios sustanciales se notificarán con **30 días de antelación**.

---

## ✅ Su Responsabilidad

Al usar Impuestify, usted reconoce que:

1. ✅ Ha sido informado que utiliza un sistema de IA
2. ✅ Entiende las limitaciones y riesgos
3. ✅ Siempre verificará información importante
4. ✅ Consultará con asesor fiscal para decisiones relevantes
5. ✅ No confiará ciegamente en las respuestas de la IA

---

**Impuestify se compromete a la transparencia total sobre el uso de IA.**

**Para cualquier duda**: ai-transparency@impuestify.com

---

**Nota Legal**: Este documento cumple con el **Artículo 52 del Reglamento (UE) 2024/1689** (AI Act) sobre obligaciones de transparencia para sistemas de IA que interactúan con personas.
