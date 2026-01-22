# 🧾 Impuestify - Asistente Fiscal Inteligente

Impuestify es un asistente fiscal especializado en normativa española que utiliza **RAG (Retrieval-Augmented Generation)** con **OpenAI GPT-5-mini** para proporcionar respuestas precisas, conversacionales y contextualizadas sobre temas fiscales.

## ✨ Características Principales

### 🤖 Sistema Multi-Agente (Microsoft Agent Framework)
- **CoordinatorAgent**: Router inteligente que decide qué agente especializado usar
- **TaxAgent**: Experto en fiscalidad general (IRPF, cuotas autónomos, deducciones)
- **PayslipAgent**: Especializado en análisis de nóminas españolas
- **WorkspaceAgent**: Gestión de espacios de trabajo con archivos fiscales del usuario
- **Routing automático**: Detecta el tipo de consulta y enruta al agente correcto

### 🛠️ Herramientas Fiscales
- **calculate_irpf**: Cálculo exacto de IRPF por tramos y CCAA
- **calculate_autonomous_quota**: Cuotas de autónomos según rendimientos 2025
- **search_tax_regulations**: Búsqueda web en fuentes oficiales (AEAT, BOE, SS)
- **analyze_payslip**: Análisis completo de nóminas con recomendaciones

### 📊 Análisis de Nóminas
- **Upload de PDFs**: Extrae datos automáticamente con PyMuPDF4LLM
- **13 patrones regex**: Identifica período, salarios, IRPF, SS, extras
- **Proyecciones anuales**: Calcula ingresos y retenciones anuales
- **Recomendaciones personalizadas**: Según rango salarial y retenciones

### 📋 Análisis de Notificaciones AEAT
- **Upload de PDFs**: Analiza notificaciones de la AEAT automáticamente
- **Extracción inteligente**: Identifica importes, plazos y conceptos clave
- **Contexto persistente**: Mantiene la notificación en toda la conversación

### 📁 Workspaces - Espacios de Trabajo Personalizados
- **Gestión de archivos fiscales**: Sube facturas, nóminas y declaraciones
- **Extracción automática de facturas**: 15 patrones regex para datos fiscales españoles
- **Embeddings semánticos**: OpenAI text-embedding-3-large (3072 dimensiones)
- **Búsqueda inteligente**: Encuentra información relevante en tus documentos
- **Contexto en chat**: El asistente conoce tus archivos y puede responder sobre ellos

### ⚡ Alto Rendimiento
- **Redis Cache**: Sistema de caché con Upstash para contexto de conversaciones
- **Cache-first strategy**: ~100ms de mejora en respuestas
- **TTL inteligente**: Renovación automática de caché (1 hora)

### 🔐 Sistema de Roles
- **Admin dashboard**: Estadísticas del sistema solo para administradores
- **Control de acceso**: JWT con claims de rol
- **Gestión de usuarios**: Scripts para asignar roles admin

### 🎨 UI/UX Premium
- **Diseño responsive**: Mobile, tablet y desktop optimizado
- **Sidebar de conversaciones**: Historial persistente con metadata
- **Chat interactivo**: Sugerencias contextuales y fuentes citadas

### ✨ Nuevas Funcionalidades (v2.7 - Diciembre 2024)

#### 🛡️ Seguridad Avanzada

| Feature | Descripción | API |
|---------|-------------|-----|
| 🛡️ **Llama Guard 4** | Moderación de contenido IA con 14 categorías de riesgo | Groq (GRATIS) |
| 🧠 **Semantic Cache** | Cache por similaridad semántica - reduce costes OpenAI ~30% | Upstash Vector |
| ⚡ **Complexity Router** | Clasificación automática de queries (simple/moderate/complex) | Local |
| 📋 **Audit Logger** | Registro inmutable de eventos de seguridad | Local |
| 🚦 **Redis Rate Limiting** | Rate limiting distribuido para múltiples instancias | Upstash Redis |

#### 📄 Procesamiento de PDFs

| Feature | Descripción | Beneficio |
|---------|-------------|----------|
| 📝 **PyMuPDF4LLM** | Extracción de texto optimizada para LLMs | Output en Markdown |
| 📊 **Detección de Tablas** | Reconoce y formatea tablas automáticamente | Mejor contexto |
| 📑 **Multi-columna** | Soporte para layouts complejos | AEAT docs |
| 🔄 **Page Chunking** | División por páginas para mejor contexto | Menos tokens |

## 🏗️ Arquitectura Multi-Agente

```
┌─────────────┐
│   Frontend  │  React + Vite + TypeScript
└──────┬──────┘
       │
       ↓
┌───────────────────────────────────────────────────┐
│              FastAPI Backend                       │
│  ┌─────────────────────────────────────────────┐  │
│  │       CoordinatorAgent (Router)             │  │
│  │     (Microsoft Agent Framework)             │  │
│  └────────┬──────────────┬──────────┬──────────┘  │
│           │              │          │              │
│     ┌─────▼─────┐  ┌────▼─────┐  ┌─▼──────────┐  │
│     │ TaxAgent  │  │ Payslip  │  │ Workspace  │  │
│     │           │  │  Agent   │  │   Agent    │  │
│     └─────┬─────┘  └────┬─────┘  └─────┬──────┘  │
│           │              │              │         │
│     ┌─────▼──────────────▼──────────────▼─────┐  │
│     │           5 Tools Fiscales              │  │
│     │  - calculate_irpf                       │  │
│     │  - autonomous_quota                     │  │
│     │  - search_regulations                   │  │
│     │  - analyze_payslip                      │  │
│     │  - workspace_search (embeddings)        │  │
│     └─────────────────────────────────────────┘  │
└───────────────────────────────────────────────────┘
       │            │            │            │
       ↓            ↓            ↓            ↓
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  Turso   │  │ Upstash  │  │  OpenAI  │  │  OpenAI  │
│  (SQLite)│  │  Redis   │  │   LLM    │  │Embeddings│
└──────────┘  └──────────┘  └──────────┘  └──────────┘
```

### Stack Tecnológico

**Backend:**
- FastAPI (API REST)
- **Microsoft Agent Framework 1.0.0b251211** (Multi-agent orchestration)
- Turso (Database - SQLite distribuido)
- Upstash Redis (Cache + Rate Limiting)
- **Upstash Vector** (Semantic Cache)
- **OpenAI API (GPT-4o-mini / GPT-5-mini)**
- **Groq API** (Llama Guard 4 - Content Moderation)
- PyMuPDF4LLM (PDF extraction optimizada para LLMs)
- pypdf (PDF validation)
- FTS5 (Full-text search)

**Frontend:**
- React 18
- Vite (Build tool)
- TypeScript
- React Router
- Axios
- Lucide React (Icons)

## 🚀 Quick Start

### Requisitos Previos

- Python 3.12+
- Node.js 18+
- **OpenAI API Key** (para LLM)
- Azure Document Intelligence (para OCR de PDFs)
- Cuenta Turso (Database)
- Cuenta Upstash (Redis) - Opcional

### 1. Clonar Repositorio

```bash
git clone https://github.com/Nambu89/Impuestify.git
cd Impuestify
```

### 2. Configurar Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Crea `.env` en `/backend`:

```bash
# OpenAI API (LLM)
OPENAI_API_KEY=sk-proj-your-api-key-here
OPENAI_MODEL=gpt-5-mini

# Azure Document Intelligence (PDF OCR)
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-endpoint.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=your_key

# Turso Database
TURSO_DATABASE_URL=libsql://your-db.turso.io
TURSO_AUTH_TOKEN=your_token

# Upstash Redis (Opcional - para cache)
UPSTASH_REDIS_REST_URL=https://your-redis.upstash.io
UPSTASH_REDIS_REST_TOKEN=your_token

# JWT Authentication
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

Iniciar backend:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Configurar Frontend

```bash
cd frontend
npm install
```

Crea `.env` en `/frontend`:

```bash
VITE_API_URL=http://localhost:8000
```

Iniciar frontend:

```bash
npm run dev
```

La aplicación estará en `http://localhost:5173`

## 📖 Uso

### Registro y Login

1. Accede a `http://localhost:5173`
2. Registra una cuenta nueva
3. Inicia sesión

### Chat Fiscal

1. Haz preguntas sobre fiscalidad española
2. El agente responde con tono conversacional
3. Cita fuentes de documentación AEAT

**Ejemplo:**
```
Usuario: "¿Cuál es el plazo para presentar el IVA?"

Impuestify: "En resumen: El IVA trimestral se presenta los primeros 20 días 
naturales del mes siguiente al trimestre.

Te lo explico:
Si eres autónomo o empresa con facturación normal, presentas el modelo 303 
cada tres meses. Por ejemplo, el IVA del primer trimestre (enero-marzo) 
se presenta entre el 1 y el 20 de abril..."
```

### Análisis de Notificaciones

1. Click en el botón de upload (📎)
2. Selecciona PDF de notificación AEAT
3. El sistema extrae automáticamente:
   - Importes y recargos
   - Plazos de pago
   - Conceptos tributarios
4. Haz preguntas sobre la notificación

### Workspaces - Gestión de Archivos Fiscales

1. **Crear un workspace**:
   - Ve a la sección Workspaces
   - Click en "Nuevo Workspace"
   - Nombra tu espacio (ej: "Empresa 2025")

2. **Subir archivos**:
   - Arrastra PDFs de facturas, nóminas o declaraciones
   - El sistema extrae automáticamente:
     - **Facturas**: Base imponible, IVA (21%/10%/4%), retenciones IRPF
     - **Nóminas**: Salario bruto/neto, IRPF, Seguridad Social
   - Se generan embeddings para búsqueda semántica

3. **Usar en el chat**:
   - Selecciona el workspace en el selector
   - Pregunta sobre tus documentos:
     - "¿Cuánto IVA he pagado este trimestre?"
     - "Resume mis facturas de enero"
     - "¿Cuál es mi retención IRPF media?"

### Dashboard (Solo Admins)

Accede a `/dashboard` para ver:
- Documentos indexados
- Fragmentos de texto en base de datos
- Tiempo promedio de respuesta
- Respuestas en caché

## 🔐 Gestión de Admins

Para marcar un usuario como administrador:

```bash
cd backend
python -m scripts.update_admin
```

Edita el script para cambiar el email del usuario.

## 🚢 Deployment en Railway

### 1. Preparación

El proyecto ya incluye:
- `railway.toml` - Configuración de servicios
- `.railwayignore` - Archivos excluidos
- Scripts de build optimizados

### 2. Conectar GitHub

1. Crea cuenta en [Railway](https://railway.app)
2. New Project → Deploy from GitHub
3. Selecciona el repositorio `Impuestify`

### 3. Configurar Servicios

Railway detectará automáticamente 2 servicios:

**Backend:**
- Root: `/backend`
- Build: `pip install -r requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

**Frontend:**
- Root: `/frontend`
- Build: `npm install && npm run build`
- Start: `npm run preview -- --host 0.0.0.0 --port $PORT`

### 4. Variables de Entorno

En Railway Dashboard, añade las variables del `.env` para cada servicio.

**Backend:**
- Todas las variables de Azure, Turso, Upstash, JWT

**Frontend:**
- `VITE_API_URL=https://tu-backend.railway.app`

### 5. Deploy

Railway desplegará automáticamente en cada push a `main`.

## 📊 Monitorización

### Logs del Backend

```bash
# Railway
railway logs

# Local
tail -f logs/taxia.log
```

### Métricas de Caché

Los logs muestran:
- `💾 Cache HIT` - Contexto encontrado en Redis
- `🔍 Cache MISS` - Carga desde base de datos
- `♻️ Cache TTL renewed` - TTL renovado
- `🗑️ Cache invalidated` - Caché eliminado

### Health Check

```bash
curl http://localhost:8000/health
```

## 🔐 Seguridad

Impuestify implementa múltiples capas de seguridad para proteger contra ataques y vulnerabilidades:

### Capas de Protección

1. **Anti-SQL Injection**:
   - Validación de inputs del usuario
   - Validación de SQL generado por IA
   - Detección de patrones OWASP

2. **AI Guardrails**:
   - Prevención de evasión fiscal
   - Detección de alucinaciones
   - Validación de referencias a fuentes
   - Filtrado de contenido tóxico

3. **File Upload Security**:
   - Validación de magic numbers (PDF real)
   - Límites de tamaño (10MB máx)
   - Detección de scripts embebidos
   - Sanitización de metadatos

4. **DDoS Protection**:
   - Rate limiting por endpoint
   - IP blocking automático (5 violaciones → bloqueo 60min)
   - Limits específicos para operaciones costosas

5. **Security Headers**:
   - Content Security Policy (CSP)
   - XSS Protection
   - Clickjacking prevention
   - MIME type sniffing protection

Ver [SECURITY.md](SECURITY.md) para más detalles.

### Testing de Seguridad

```bash
cd backend
pytest tests/test_security.py -v
```

## 🧪 Testing

### Backend

```bash
cd backend
pytest tests/
```

### Frontend

```bash
cd frontend
npm run build  # Verifica que compila sin errores
```

## 📁 Estructura del Proyecto

```
Impuestify/
├── backend/
│   ├── app/
│   │   ├── agents/          # Multi-agent system
│   │   │   ├── coordinator_agent.py  # Router
│   │   │   ├── tax_agent.py         # Fiscal expert
│   │   │   ├── payslip_agent.py     # Payslip expert
│   │   │   ├── workspace_agent.py   # Workspace expert
│   │   │   └── base_agent.py        # Base wrapper
│   │   ├── tools/           # Agent tools
│   │   │   ├── irpf_calculator_tool.py
│   │   │   ├── autonomous_quota_tool.py
│   │   │   ├── search_tool.py
│   │   │   └── payslip_analysis_tool.py
│   │   ├── services/        # Business logic
│   │   │   ├── payslip_extractor.py       # PDF nómina extraction
│   │   │   ├── invoice_extractor.py       # PDF factura extraction
│   │   │   ├── file_processing_service.py # File upload & processing
│   │   │   ├── workspace_service.py       # Workspace CRUD
│   │   │   └── workspace_embedding_service.py # OpenAI embeddings
│   │   ├── auth/            # JWT authentication
│   │   ├── database/        # Turso client & models
│   │   ├── routers/         # API endpoints
│   │   │   ├── chat.py
│   │   │   ├── chat_stream.py    # SSE streaming
│   │   │   ├── payslips.py       # Payslip management
│   │   │   ├── workspaces.py     # Workspace CRUD & files
│   │   │   └── notifications.py
│   │   └── utils/           # Helpers
│   ├── scripts/             # Admin & maintenance
│   ├── tests/               # Unit tests
│   │   ├── test_coordinator.py
│   │   ├── test_new_tools.py
│   │   ├── test_payslip_analysis.py
│   │   └── test_workspace_components.py  # 34 tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── hooks/           # Custom hooks
│   │   ├── pages/           # Page components
│   │   └── styles/          # CSS
│   └── package.json
├── .gitignore
├── .railwayignore
├── railway.toml
└── README.md
```

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama: `git checkout -b feature/nueva-feature`
3. Commit: `git commit -m 'feat: descripción'`
4. Push: `git push origin feature/nueva-feature`
5. Abre un Pull Request

### Convenciones de Commits

- `feat:` - Nueva funcionalidad
- `fix:` - Corrección de bug
- `docs:` - Documentación
- `style:` - Formato, no afecta código
- `refactor:` - Refactorización
- `test:` - Tests
- `chore:` - Mantenimiento

## 🐛 Troubleshooting

### Backend no conecta a Turso

- Verifica `TURSO_DATABASE_URL` y `TURSO_AUTH_TOKEN`
- Comprueba que la base de datos existe en Turso

### Redis no funciona

- Es opcional, el sistema funciona sin Redis
- Verifica `UPSTASH_REDIS_REST_URL` y token
- Logs mostrarán `⚠️ Upstash Redis no configurado`

### Frontend no se conecta al Backend

- Verifica `VITE_API_URL` en `.env`
- Comprueba CORS en `backend/app/main.py`
- Revisa que el backend esté corriendo

### Dashboard no aparece

- Verifica que tu usuario sea admin
- Cierra sesión y vuelve a iniciar sesión
- Revisa que `is_admin=true` en la base de datos

---

## 🆕 v2.7 Security & Optimization Features

### 🛡️ Llama Guard 4 - Content Moderation

**Moderación de contenido IA antes de enviar a OpenAI**

- ✅ **14 categorías de riesgo**: Violencia, contenido sexual, odio, etc.
- ✅ **API gratuita**: Groq API (14,400 requests/día)
- ✅ **Mensajes en español**: Respuestas personalizadas por categoría
- ✅ **Graceful degradation**: Falla abierto si Groq no disponible
- ✅ **Latencia**: ~200-500ms

**Variables de entorno:**
```env
GROQ_API_KEY=gsk_xxx
ENABLE_CONTENT_MODERATION=true
```

### 🧠 Semantic Cache - Upstash Vector

**Cache inteligente por similaridad semántica**

- ✅ **Reduce costes OpenAI ~30%**: Respuestas cacheadas para queries similares
- ✅ **Umbral de similaridad**: 0.93 (configurable)
- ✅ **Skip queries personales**: No cachea datos personales del usuario
- ✅ **TTL**: 24 horas
- ✅ **API gratuita**: Upstash Vector (10,000 vectores)

**Variables de entorno:**
```env
UPSTASH_VECTOR_REST_URL=https://xxx.upstash.io
UPSTASH_VECTOR_REST_TOKEN=xxx
ENABLE_SEMANTIC_CACHE=true
SEMANTIC_CACHE_THRESHOLD=0.93
```

### ⚡ Complexity Router

**Clasificación automática de queries para optimizar reasoning_effort**

- ✅ **3 niveles**: Simple, Moderate, Complex
- ✅ **Regex patterns**: Clasificación rápida sin LLM
- ✅ **Reasoning effort**: low/medium/high según complejidad
- ✅ **Beneficios**: Respuestas más rápidas para queries simples

**Ejemplos:**
- Simple: "¿Qué es el IVA?" → `reasoning_effort=low`
- Complex: "Analiza implicaciones fiscales de herencia" → `reasoning_effort=high`

### 📋 Audit Logger

**Registro inmutable de eventos de seguridad**

- ✅ **Eventos**: Auth, AI requests, moderation blocks, rate limits
- ✅ **Formato JSON**: Estructurado para parsing
- ✅ **Severidad**: info, warning, error, critical
- ✅ **Compliance**: Logs inmutables para auditoría

### 🚦 Redis Rate Limiting

**Rate limiting distribuido con Upstash Redis**

- ✅ **Distribuido**: Compartido entre múltiples instancias
- ✅ **Fallback automático**: In-memory si Redis no disponible
- ✅ **Custom storage**: Adaptador para Upstash REST API
- ✅ **Escalabilidad**: Listo para horizontal scaling

### 📄 PyMuPDF4LLM - PDF Extraction

**Extracción de texto optimizada para LLMs**

- ✅ **Output Markdown**: Preserva estructura (headers, tablas, listas)
- ✅ **Detección de tablas**: Formatea tablas automáticamente
- ✅ **Multi-columna**: Soporte para layouts complejos
- ✅ **Page chunking**: División por páginas para mejor contexto
- ✅ **Perfecto para AEAT**: Notificaciones fiscales estructuradas

**Uso:**
```python
from app.utils.pdf_extractor import extract_pdf_text

result = await extract_pdf_text(pdf_bytes, "notificacion.pdf")
if result.success:
    markdown = result.markdown_text  # Listo para LLM
```

---

## 🆕 v2.8 Workspaces - Espacios de Trabajo (Enero 2026)

### 📁 Workspaces - Gestión de Archivos Fiscales

**Espacios de trabajo personalizados para organizar documentos fiscales**

| Feature | Descripción | Tecnología |
|---------|-------------|------------|
| 📁 **Workspaces** | Espacios de trabajo por usuario/empresa | Turso SQLite |
| 📤 **File Upload** | Drag & drop de PDFs (facturas, nóminas) | FastAPI + PyMuPDF4LLM |
| 🧾 **Invoice Extractor** | 15 patrones regex para facturas españolas | Python regex |
| 🔢 **Embeddings** | Búsqueda semántica en documentos | OpenAI text-embedding-3-large |
| 🔍 **Semantic Search** | Encuentra info relevante por contexto | Cosine similarity |
| 💬 **Chat Context** | El asistente conoce tus archivos | WorkspaceAgent |

### 🧾 Invoice Extractor - Campos Extraídos

```
✅ Número de factura          ✅ Base imponible 21%
✅ Fecha de factura           ✅ Base imponible 10%
✅ NIF/CIF emisor             ✅ Base imponible 4%
✅ NIF/CIF receptor           ✅ Cuota IVA por tipo
✅ Retención IRPF             ✅ Total factura
✅ Porcentaje retención       ✅ Confidence score
```

### 🔢 Workspace Embeddings

**Embeddings semánticos para búsqueda inteligente**

- ✅ **Modelo**: OpenAI text-embedding-3-large (3072 dimensiones)
- ✅ **Chunking**: 1000 caracteres con 200 de overlap
- ✅ **Almacenamiento**: BLOB en Turso SQLite
- ✅ **Búsqueda**: Cosine similarity con threshold 0.7
- ✅ **Índices**: Por workspace y por archivo

### 📡 API Endpoints - Workspaces

```bash
# Crear workspace
POST /api/workspaces
{"name": "Mi Empresa 2025", "description": "Facturas Q1"}

# Listar workspaces
GET /api/workspaces

# Subir archivo
POST /api/workspaces/{id}/files
Content-Type: multipart/form-data
file: factura.pdf

# Listar archivos
GET /api/workspaces/{id}/files

# Eliminar archivo
DELETE /api/workspaces/{id}/files/{file_id}

# Eliminar workspace
DELETE /api/workspaces/{id}
```

### 🧪 Tests - 34 tests automatizados

```bash
cd backend
pytest tests/test_workspace_components.py -v

# Cobertura:
# - InvoiceExtractor: 10 tests
# - WorkspaceEmbeddingService: 6 tests
# - FileProcessingService: 6 tests
# - WorkspaceAgent: 3 tests
# - WorkspaceAPIEndpoints: 3 tests
# - WorkspaceDatabaseSchema: 2 tests
# - WorkspaceIntegration: 4 tests
```

---

## 📄 Licencia

MIT License - ver archivo `LICENSE` para detalles.

## ⚠️ Disclaimer Legal

Impuestify es una herramienta de asistencia informativa. **No constituye asesoramiento fiscal profesional**. Siempre consulta con un asesor fiscal cualificado para decisiones importantes.

## 🆘 Soporte

- 🐛 Issues: [GitHub Issues](https://github.com/Nambu89/Impuestify/issues)
- 💬 Discusiones: [GitHub Discussions](https://github.com/Nambu89/Impuestify/discussions)

---

**Fernando Prada - AI Engineer - Senior Consultant**

**¡Impuestify - Haciendo la fiscalidad española más accesible!**