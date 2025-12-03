# 🧾 TaxIA - Asistente Fiscal Español

TaxIA es un asistente fiscal especializado en normativa española que utiliza **RAG (Retrieval-Augmented Generation)** con **guardrails** para proporcionar respuestas precisas y seguras sobre temas fiscales.

## ✨ Características

- 🔍 **RAG Avanzado**: Recuperación inteligente con reranking y caché optimizado
- 🛡️ **Sistema de Guardrails**: Previene alucinaciones y consultas sobre evasión fiscal
- 📋 **Respuestas Estructuradas**: Formato consistente con veredicto, explicación y citas
- ⚡ **Alto Rendimiento**: Caché multinivel y optimizaciones de velocidad
- 🚀 **Deploy Fácil**: Compatible con Railway, Render, Fly.io y Docker
- 📊 **Monitorización**: Logs estructurados y métricas de rendimiento

## 🏗️ Arquitectura

```
[Usuario] → [FastAPI] → [Guardrails Input] → [RAG Engine] → [OpenAI] → [Guardrails Output] → [Respuesta]
                                ↓
                         [FAISS Index] ← [Embeddings] ← [PDFs AEAT]
```

### Componentes Principales

- **FastAPI**: API REST con documentación automática
- **Guardrails AI**: Sistema de seguridad y validación
- **FAISS**: Búsqueda vectorial de alta velocidad
- **Sentence Transformers**: Embeddings y reranking
- **OpenAI GPT**: Generación de respuestas
- **Caché Inteligente**: Redis opcional + caché local

## 🚀 Quick Start

### 1. Clonar y Configurar

```bash
git clone <tu-repo>
cd taxia
cp .env.example .env
```

Edita `.env` con tus credenciales:

```bash
OPENAI_API_KEY=sk-tu-api-key-aqui
PDF_DIR=./data
```

### 2. Añadir Documentos

Coloca los PDFs de la AEAT en el directorio `data/`:

```bash
mkdir -p data
# Copia tus PDFs de manuales AEAT aquí
```

### 3. Deploy Rápido con Railway

```bash
# Instalar Railway CLI
npm install -g @railway/cli

# Hacer el script ejecutable y deployar
chmod +x deploy.sh
./deploy.sh railway
```

### 4. Deploy Local para Testing

```bash
./deploy.sh local
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

La API estará disponible en `http://localhost:8000`

## 📖 Uso de la API

### Endpoint Principal: `/ask`

```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "¿Estoy obligado a presentar IRPF si gané 25.000€?",
    "k": 6
  }'
```

### Respuesta Típica

```json
{
  "answer": "**Veredicto corto:** Sí - estás obligado a presentar la declaración...",
  "sources": [
    {
      "id": "uuid-123",
      "source": "Manual_IRPF_2024.pdf",
      "page": 15,
      "title": "Obligación de declarar",
      "text_preview": "Los contribuyentes están obligados..."
    }
  ],
  "metadata": {
    "retrieval_time": 0.12,
    "rerank_time": 0.03,
    "similarity_scores": [0.85, 0.82, 0.79],
    "k_retrieved": 6
  },
  "processing_time": 1.45,
  "cached": false,
  "guardrails_violations": []
}
```

### Otros Endpoints

- `GET /health` - Estado del sistema
- `GET /stats` - Estadísticas del RAG
- `GET /docs` - Documentación interactiva (Swagger)
- `POST /admin/rebuild` - Reconstruir índice (requiere API key admin)

## 🛡️ Sistema de Guardrails

### Guardrails de Entrada

- **Detección de Evasión**: Bloquea consultas sobre ocultar ingresos, no declarar, etc.
- **Filtro de Toxicidad**: Detecta lenguaje ofensivo
- **Detector PII**: Identifica información personal sensible
- **Filtro de Competidores**: Evita menciones de otros asesores fiscales

### Guardrails de Salida

- **Restricción de Temas**: Mantiene respuestas en fiscalidad española
- **Detector de Alucinaciones**: Verifica referencias específicas contra el contexto
- **Validación de Citas**: Asegura que las fuentes citadas existan

### Ejemplos de Consultas Bloqueadas

❌ "¿Cómo puedo ocultar ingresos para pagar menos impuestos?"
❌ "¿Me dices cómo no declarar el IVA?"
❌ "Formas de evadir Hacienda"

✅ "¿Qué deducciones legales puedo aplicar en IRPF?"
✅ "¿Cómo presentar una declaración complementaria?"

## 🔧 Configuración Avanzada

### Variables de Entorno Importantes

```bash
# Modelos IA
EMBEDDING_MODEL=mixedbread-ai/mxbai-embed-large-v1
RERANKING_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2

# Configuración RAG
CHUNK_SIZE=1200
CHUNK_OVERLAP=150
RETRIEVAL_K=6
RERANK_K=3

# Guardrails
ENABLE_GUARDRAILS=true
TOXICITY_THRESHOLD=0.8
HALLUCINATION_THRESHOLD=0.85
```

### Personalización de Guardrails

Edita `guardrails.py` para añadir reglas específicas:

```python
# Añadir nuevos patrones de evasión
self.forbidden_patterns.append(r"\bnuevo_patron_prohibido\b")

# Modificar temas válidos
VALID_TOPICS += ["nuevo_tema_fiscal"]
```

## 📊 Monitorización y Logs

### Logs Estructurados

```python
import structlog
logger = structlog.get_logger()

logger.info("Consulta procesada", 
           question_length=len(question),
           processing_time=1.45,
           cached=True)
```

### Métricas Disponibles

- Tiempo de procesamiento promedio
- Ratio de cache hits/misses
- Tasa de errores
- Violaciones de guardrails
- Estadísticas de chunks y fuentes

## 🚢 Opciones de Deployment

### Railway (Recomendado para MVP)

```bash
./deploy.sh railway
```

**Pros**: Setup instantáneo, pricing justo, logs en tiempo real
**Contras**: Créditos limitados iniciales

### Render

```bash
./deploy.sh render
```

**Pros**: Plan gratuito, SSL automático, buena estabilidad
**Contras**: Cold starts en plan gratuito

### Fly.io

```bash
./deploy.sh fly
```

**Pros**: Plan gratuito generoso, latencia global baja
**Contras**: Configuración más compleja

### Docker Local

```bash
./deploy.sh docker
docker-compose up -d
```

### Coolify (Auto-hospedado)

1. Configura un VPS (€5/mes en Hetzner)
2. Instala Coolify: `https://coolify.io/docs/installation`
3. Conecta tu repo GitHub
4. Deploy automático

## 🧪 Testing y Validación

### Validación Completa del Sistema

```bash
python utils.py
```

Verifica:
- API key de OpenAI
- Modelos de ML disponibles
- Archivos PDF válidos
- Configuración correcta

### Test de Guardrails

```bash
curl http://localhost:8000/test/guardrails
```

### Test de Funcionalidad

```bash
./deploy.sh test
```

## 📁 Estructura del Proyecto

```
taxia/
├── main.py              # API FastAPI principal
├── rag_engine.py        # Motor RAG con reranking
├── guardrails.py        # Sistema de guardrails
├── config.py            # Configuración centralizada
├── utils.py             # Utilidades y validación
├── requirements.txt     # Dependencias Python
├── Dockerfile          # Contenedor Docker
├── railway.toml        # Configuración Railway
├── deploy.sh           # Scripts de deployment
├── .env.example        # Variables de entorno template
├── data/               # PDFs de documentos AEAT
├── cache/              # Caché local de embeddings
└── README.md           # Esta documentación
```

## 🔄 Actualización del Índice

### Añadir Nuevos Documentos

1. Coloca nuevos PDFs en `data/`
2. Reconstruye el índice:

```bash
curl -X POST "http://localhost:8000/admin/rebuild?api_key=tu-admin-key" \
  -H "Content-Type: application/json" \
  -d '{"force": true}'
```

### Limpiar Caché

```bash
curl "http://localhost:8000/admin/cache/clear?api_key=tu-admin-key"
```

## 🐛 Debugging

### Logs Comunes

```bash
# Ver logs en Railway
railway logs

# Ver logs locales
tail -f logs/taxia.log

# Debug modo desarrollador
uvicorn main:app --reload --log-level debug
```

### Problemas Frecuentes

**Error: "Motor RAG no inicializado"**
- Verifica que los PDFs estén en `data/`
- Revisa que la API key de OpenAI sea válida
- Comprueba disponibilidad de modelos

**Respuestas de baja calidad**
- Ajusta `CHUNK_SIZE` y `CHUNK_OVERLAP`
- Incrementa `RETRIEVAL_K` para más contexto
- Verifica calidad de documentos fuente

**Lentitud en respuestas**
- Habilita caché Redis con `ENABLE_CACHE=true`
- Reduce `RETRIEVAL_K` si es muy alto
- Considera usar modelo de embeddings más rápido

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama: `git checkout -b feature/nueva-caracteristica`
3. Commit: `git commit -m 'Añadir nueva característica'`
4. Push: `git push origin feature/nueva-caracteristica`
5. Abre un Pull Request

### Áreas de Mejora

- [ ] Soporte para más tipos de documento (Word, Excel)
- [ ] Interface web con Streamlit/Gradio
- [ ] Métricas avanzadas con Prometheus
- [ ] Fine-tuning del modelo base
- [ ] Soporte multiidioma
- [ ] Integración con bases de datos vectoriales externas

## 📄 Licencia

MIT License - ver archivo `LICENSE` para detalles.

## ⚠️ Disclaimer Legal

TaxIA es una herramienta de asistencia informativa. **No constituye asesoramiento fiscal profesional**. Siempre consulta con un asesor fiscal cualificado para decisiones importantes.

## 🆘 Soporte

- 📧 Email: soporte@taxia.com
- 🐛 Issues: GitHub Issues
- 💬 Discusiones: GitHub Discussions

---

**¡TaxIA - Haciendo la fiscalidad española más accesible! 🇪🇸**