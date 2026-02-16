# TaxIA - Roadmap de Desarrollo

## Estado del Proyecto: Enero 2026

### ✅ Completado - Sistema de Memoria a Largo Plazo

#### Implementación Realizada
1. **Servicio de Memoria de Usuario** ([`user_memory_service.py`](backend/app/services/user_memory_service.py))
   - Extracción automática de hechos del usuario (residencia, empleo, familia, propiedad, donaciones)
   - Almacenamiento en Upstash Vector para memoria semántica
   - Perfil estructurado en Turso DB
   - Cross-session memory persistence

2. **Tabla de Perfiles de Usuario** ([`turso_client.py`](backend/app/database/turso_client.py:182))
   - `user_profiles` con campos: ccaa_residencia, situacion_laboral, tiene_vivienda, primera_vivienda, datos_fiscales

3. **Integración en TaxAgent** ([`tax_agent.py`](backend/app/agents/tax_agent.py:295))
   - Parámetro `db_client` para acceso a memoria
   - Extracción de hechos en cada mensaje
   - Contexto de usuario enriquecido en prompts

4. **Flujo de Chat Actualizado** ([`chat_stream.py`](backend/app/routers/chat_stream.py:246))
   - Pasa `db_client` al TaxAgent para memoria

---

## 🚧 En Progreso - Mejoras Prioritarias

### 1. Herramienta de Cálculo ISD (Impuesto Sucesiones y Donaciones)
**Prioridad: ALTA** | **Estimación: 2-3 días**

**Problema:**
- El usuario pregunta sobre donación de 60,000€ de su madre para compra de vivienda en Aragón
- El sistema no tiene herramienta para calcular ISD
- Falta normativa autonómica de Aragón en la base de datos

**Solución:**
```python
# Nueva herramienta: calculate_isd
# backend/app/tools/isd_calculator_tool.py

async def calculate_isd(
    amount: float,
    relationship: str,  # "padres_hijos", "conyuge", "otros"
    ccaa: str,  # "Aragón", "Madrid", etc.
    destination: Optional[str] = None,  # "primera_vivienda", etc.
    age: Optional[int] = None
) -> Dict[str, Any]:
    """
    Calcula el Impuesto sobre Sucesiones y Donaciones.
    
    Returns:
        - base_imponible
        - reduccion_aplicable
        - cuota_tributaria
        - plazo_presentacion
        - bonificaciones_autonomicas
    """
```

**Tareas:**
- [ ] Crear `isd_calculator_tool.py`
- [ ] Añadir tablas de tarifas ISD por CCAA
- [ ] Implementar reducciones por parentesco
- [ ] Implementar bonificaciones autonómicas (especialmente Aragón)
- [ ] Integrar con TaxAgent

### 2. Agente de Actualización Documental
**Prioridad: MEDIA** | **Estimación: 1-2 semanas**

**Objetivo:**
Automatizar la descarga y actualización de documentos fiscales desde AEAT y otras fuentes oficiales.

**Arquitectura Propuesta:**
```
┌─────────────────────────────────────────────────────────────┐
│                    Document Update Agent                     │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Scheduler │───▶│   Scraper   │───▶│  Validator  │     │
│  │  (Cron/CEL) │    │ (Playwright)│    │  (Checksum) │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│                            │                   │             │
│                            ▼                   ▼             │
│                    ┌─────────────────────────────┐          │
│                    │     Document Processor      │          │
│                    │  - PDF Extraction           │          │
│                    │  - Chunking                 │          │
│                    │  - Embedding Generation     │          │
│                    └─────────────────────────────┘          │
│                            │                                 │
│                            ▼                                 │
│                    ┌─────────────────────────────┐          │
│                    │       Turso Database        │          │
│                    │  - documents                │          │
│                    │  - chunks                   │          │
│                    │  - embeddings               │          │
│                    └─────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

**Fuentes a Monitorizar:**
- [ ] AEAT (Modelos fiscales, manuales, guías)
- [ ] BOE (Boletín Oficial del Estado)
- [ ] BOA (Boletín Oficial de Aragón)
- [ ] BOCM (Boletín Oficial de la Comunidad de Madrid)
- [ ] DOGC (Diari Oficial de la Generalitat de Catalunya)
- [ ] Otras CCAA según demanda

**Tareas:**
- [ ] Crear `backend/app/agents/document_update_agent.py`
- [ ] Implementar scraper respetando robots.txt y rate limits
- [ ] Sistema de detección de cambios (hash comparison)
- [ ] Pipeline de ingesta automática
- [ ] Notificaciones de actualizaciones

### 3. Enriquecimiento de Base de Datos RAG
**Prioridad: ALTA** | **Estimación: 1 semana**

**Contenido Faltante:**
- [ ] Normativa ISD por CCAA (especialmente Aragón)
- [ ] Tablas de tarifas autonómicas actualizadas
- [ ] Reducciones y bonificaciones por CCAA
- [ ] Plazos de presentación por tipo de impuesto y CCAA

**Fuentes:**
```
Aragón:
- https://www.aragon.es/-/impuesto-sobre-sucesiones-y-donaciones
- Ley 13/1997, de 23 de diciembre, de la Comunidad Autónoma de Aragón

Madrid:
- https://www.comunidad.madrid/hacienda/impuestos/impuesto-sucesiones-donaciones

Cataluña:
- https://economia.gencat.cat/ca/tributs/tributos-cedidos/successions-donacions/
```

---

## 📋 Backlog - Futuras Mejoras

### 4. Sistema de Alertas Fiscales
**Prioridad: BAJA** | **Estimación: 1 semana**

- Notificaciones de plazos fiscales
- Recordatorios de declaraciones
- Alertas de cambios normativos

### 5. Integración con Factura Electrónica
**Prioridad: BAJA** | **Estimación: 2 semanas**

- Soporte para FacturaE
- Integración con sistemas contables
- Automatización de IVA

### 6. App Móvil
**Prioridad: FUTURA** | **Estimación: 4-6 semanas**

- React Native / Flutter
- Notificaciones push
- Escaneo de documentos con cámara

---

## 🔧 Mejoras Técnicas Pendientes

### Configuración Upstash Vector
**Problema:** Error en logs: "index not configured for automatic embeddings"

**Solución:**
1. Crear índice en Upstash Vector con modelo de embeddings
2. Configurar `UPSTASH_VECTOR_URL` y `UPSTASH_VECTOR_TOKEN`
3. Actualizar `semantic_cache.py` para usar el índice correcto

### Optimización de Rendimiento
- [ ] Implementar caché de respuestas frecuentes
- [ ] Optimizar consultas FTS5
- [ ] Reducir latencia de streaming

---

## 📊 Métricas Actuales

| Métrica | Valor |
|---------|-------|
| Documentos en BD | 49 |
| Chunks | 11,071 |
| Embeddings | 8,060 |
| Tiempo respuesta medio | ~30s |
| Cache hit rate | ~15% |

---

## 🎯 Objetivos Q1 2026

1. **Completar herramienta ISD** - Permitir cálculos de donaciones y sucesiones
2. **Implementar agente de actualización** - Mantener BD actualizada automáticamente
3. **Enriquecer base de datos** - Añadir normativa autonómica faltante
4. **Mejorar memoria de usuario** - Persistencia cross-session completa
5. **Alcanzar 80% cache hit rate** - Optimizar respuestas frecuentes

---

## 📝 Notas de Desarrollo

### Commits Recientes
- `feat: Add user memory service for long-term context`
- `feat: Add user_profiles table to Turso schema`
- `feat: Integrate memory service in TaxAgent`
- `feat: Pass db_client to TaxAgent in chat_stream`

### Próximos Commits Planificados
- `feat: Add ISD calculator tool`
- `feat: Add Aragón ISD regulations to knowledge base`
- `feat: Create document update agent`
