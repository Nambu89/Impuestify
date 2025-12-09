# 🧾 TaxIA - Asistente Fiscal Inteligente

TaxIA es un asistente fiscal especializado en normativa española que utiliza **RAG (Retrieval-Augmented Generation)** con **Azure AI** para proporcionar respuestas precisas, conversacionales y contextualizadas sobre temas fiscales.

## ✨ Características Principales

### 🤖 IA Conversacional
- **Tono humano y cercano**: Respuestas como si hablaras con un asesor fiscal amigable
- **Traduce términos técnicos**: Explica conceptos fiscales en lenguaje coloquial
- **Contextual**: Mantiene el contexto de conversaciones y notificaciones

### ⚡ Alto Rendimiento
- **Redis Cache**: Sistema de caché con Upstash para contexto de conversaciones
- **Cache-first strategy**: ~100ms de mejora en respuestas
- **TTL inteligente**: Renovación automática de caché (1 hora)

### 📋 Análisis de Notificaciones
- **Upload de PDFs**: Analiza notificaciones de la AEAT automáticamente
- **Extracción inteligente**: Identifica importes, plazos y conceptos clave
- **Contexto persistente**: Mantiene la notificación en toda la conversación

### 🔐 Sistema de Roles
- **Admin dashboard**: Estadísticas del sistema solo para administradores
- **Control de acceso**: JWT con claims de rol
- **Gestión de usuarios**: Scripts para asignar roles admin

### 🎨 UI/UX Premium
- **Diseño responsive**: Mobile, tablet y desktop optimizado
- **Sidebar de conversaciones**: Historial persistente con metadata
- **Chat interactivo**: Sugerencias contextuales y fuentes citadas

## 🏗️ Arquitectura

```
┌─────────────┐
│   Frontend  │  React + Vite + TypeScript
│  (Vite/TS)  │  - Responsive design
└──────┬──────┘  - Conversation sidebar
       │         - Notification upload
       ↓
┌─────────────┐
│   Backend   │  FastAPI + Python 3.12
│  (FastAPI)  │  - Auth (JWT)
└──────┬──────┘  - Rate limiting
       │         - Structured logging
       ↓
┌─────────────────────────────────────┐
│         Services Layer              │
├─────────────┬───────────┬───────────┤
│ Conversation│  Cache    │   User    │
│  Service    │  Service  │  Service  │
└─────────────┴───────────┴───────────┘
       │            │            │
       ↓            ↓            ↓
┌──────────┐  ┌──────────┐  ┌──────────┐
│  Turso   │  │ Upstash  │  │  Azure   │
│  (SQLite)│  │  Redis   │  │   AI     │
└──────────┘  └──────────┘  └──────────┘
```

### Stack Tecnológico

**Backend:**
- FastAPI (API REST)
- Turso (Database - SQLite distribuido)
- Upstash Redis (Cache)
- Azure OpenAI (GPT-5 mini)
- Azure Document Intelligence (OCR)
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
- Cuenta Azure (OpenAI + Document Intelligence)
- Cuenta Turso (Database)
- Cuenta Upstash (Redis) - Opcional

### 1. Clonar Repositorio

```bash
git clone https://github.com/Nambu89/TaxIA.git
cd TaxIA
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
# Azure AI Foundry (LLM)
AZURE_OPENAI_ENDPOINT=https://your-endpoint.cognitiveservices.azure.com/
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_DEPLOYMENT=gpt-5-mini
AZURE_OPENAI_API_VERSION=2025-04-01-preview

# Azure Document Intelligence
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-endpoint.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=your_key

# Turso Database
TURSO_DATABASE_URL=libsql://your-db.turso.io
TURSO_AUTH_TOKEN=your_token

# Upstash Redis (Opcional)
UPSTASH_REDIS_REST_URL=https://your-redis.upstash.io
UPSTASH_REDIS_REST_TOKEN=your_token

# JWT
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

TaxIA: "En resumen: El IVA trimestral se presenta los primeros 20 días 
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
3. Selecciona el repositorio `TaxIA`

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

TaxIA implementa múltiples capas de seguridad para proteger contra ataques y vulnerabilidades:

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
TaxIA/
├── backend/
│   ├── app/
│   │   ├── agents/          # Tax & Notification agents
│   │   ├── auth/            # JWT authentication
│   │   ├── database/        # Turso client & models
│   │   ├── routers/         # API endpoints
│   │   ├── services/        # Business logic
│   │   └── utils/           # Helpers
│   ├── scripts/             # Admin & maintenance
│   ├── tests/               # Unit tests
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

## 📄 Licencia

MIT License - ver archivo `LICENSE` para detalles.

## ⚠️ Disclaimer Legal

TaxIA es una herramienta de asistencia informativa. **No constituye asesoramiento fiscal profesional**. Siempre consulta con un asesor fiscal cualificado para decisiones importantes.

## 🆘 Soporte

- 🐛 Issues: [GitHub Issues](https://github.com/Nambu89/TaxIA/issues)
- 💬 Discusiones: [GitHub Discussions](https://github.com/Nambu89/TaxIA/discussions)

---

**Fernando Prada - AI Engineer - Senior Consultant**

**¡TaxIA - Haciendo la fiscalidad española más accesible!**