# Columna A: Patrones Claude Code para Impuestify

> Spec aprobada: 2026-03-31
> Origen: Filtración código fuente Claude Code v2.1.88 (source maps npm)
> Enfoque: Big Bang territorial primero, luego features incrementales

---

## 1. Modularización Territorial (Plugin System)

### Objetivo
Encapsular toda la lógica fiscal específica de cada territorio en plugins independientes, eliminando if/else dispersos en el código.

### Estructura

```
backend/app/territories/
├── __init__.py              # Registry: load_territory(), get_territory()
├── base.py                  # TerritoryPlugin (clase abstracta)
├── comun/
│   ├── __init__.py
│   └── plugin.py            # CommonTerritory — 15 CCAA régimen común
├── foral_vasco/
│   ├── __init__.py
│   └── plugin.py            # ForalVasco — Araba, Bizkaia, Gipuzkoa
├── foral_navarra/
│   ├── __init__.py
│   └── plugin.py            # ForalNavarra — escala y mínimos propios
├── canarias/
│   ├── __init__.py
│   └── plugin.py            # Canarias — IGIC en vez de IVA
└── ceuta_melilla/
    ├── __init__.py
    └── plugin.py            # CeutaMelilla — IPSI + 60% deducción
```

### Interfaz base

```python
class TerritoryPlugin(ABC):
    territories: list[str]       # ["Araba", "Bizkaia", "Gipuzkoa"]
    regime: str                  # "foral_vasco"

    @abstractmethod
    async def get_irpf_scales(self, year: int) -> ScaleData

    @abstractmethod
    async def simulate_irpf(self, profile: FiscalProfile) -> SimulationResult

    @abstractmethod
    async def get_deductions(self, ccaa: str, year: int) -> list[Deduction]

    @abstractmethod
    def get_indirect_tax_model(self) -> str  # "303" | "420" | "ipsi"

    @abstractmethod
    def get_minimos_personales(self) -> MinimosConfig

    def get_rag_filters(self, ccaa: str) -> dict

    def get_upcoming_deadlines(self) -> list[Deadline]
```

### Registry

```python
_registry: dict[str, TerritoryPlugin] = {}

def get_territory(ccaa: str) -> TerritoryPlugin:
    regime = classify_regime(ccaa)
    return _registry[regime]
```

### Migración

- `irpf_simulator.py`: el método `simulate()` delega a `territory.simulate_irpf()` en vez de if/else foral vs común
- `deduction_service.py`: delega a `territory.get_deductions()`
- Calculadores existentes (`modelo_ipsi.py`, `modelo_420.py`, `modelo_303.py`) se mantienen — cada plugin los importa internamente
- No se borra código, se mueve y se conecta via la interfaz
- Tests existentes (test_foral_simulator, test_ceuta_melilla, etc.) deben seguir pasando

### 5 regímenes fiscales

| Plugin | Territorios | IRPF | Impuesto indirecto | Particularidades |
|--------|-------------|------|--------------------|------------------|
| `comun` | 15 CCAA | Estatal + Autonómica | IVA (303) | Base general |
| `foral_vasco` | Araba, Bizkaia, Gipuzkoa | Escala única foral (7 tramos) | IVA + TicketBAI | EPSV, mínimos como deducción directa |
| `foral_navarra` | Navarra | Escala única foral (11 tramos) | IVA + F69 | Mínimos propios |
| `canarias` | Canarias | Estatal (ambas) | IGIC 7% (420) | Sin Modelo 349 |
| `ceuta_melilla` | Ceuta, Melilla | Estatal (ambas) + 60% deducción | IPSI 0.5%-10% | 6 tipos IPSI |

---

## 2. Eliminar Prometheus + Cost Tracking Admin

### Eliminar

- Borrar `backend/app/metrics.py` (Prometheus)
- Borrar endpoint `/metrics` de `main.py`
- Borrar `prometheus_client` de `requirements.txt`
- Limpiar imports en archivos que usen métricas Prometheus

### Nuevo servicio

```python
# backend/app/services/cost_tracker.py
class CostTracker:
    PRICING = {
        "gpt-4o": {"input": 2.50, "output": 10.00},  # USD por 1M tokens
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "text-embedding-3-large": {"input": 0.13, "output": 0},
    }

    async def track(self, user_id, model, input_tokens, output_tokens, endpoint):
        """Guarda en usage_metrics con coste USD calculado"""

    async def get_user_summary(self, user_id, period="month") -> UserCostSummary:
        """Coste total, por modelo, por endpoint"""

    async def get_global_summary(self, period="month") -> GlobalCostSummary:
        """Dashboard admin: coste total, por plan, por CCAA, top users"""
```

### Admin endpoint

```python
@router.get("/admin/costs")  # owner-only
async def get_cost_dashboard(period: str = "month"):
    return await cost_tracker.get_global_summary(period)
```

### Frontend admin

Widget en `/admin` existente:
- Coste total del mes (EUR, conversión USD→EUR)
- Breakdown por plan (Particular 5EUR / Creator 49EUR / Autónomo 39EUR)
- Top 10 usuarios por consumo
- Tendencia 30 días (gráfico simple)

Reutilizar tabla `usage_metrics` existente en Turso.

---

## 3. Memory Extraction (Regex + LLM)

### Capa 1: Regex en tiempo real (ampliar lo existente)

Ampliar `user_memory_service.py` con nuevos patrones:

```python
EXTRACTION_PATTERNS = {
    "hipoteca": r"hipoteca|préstamo hipotecario|pago mensual de (\d+)",
    "guarderia": r"guardería|escuela infantil|0[- ]?3 años",
    "plan_pensiones": r"plan de pensiones|aporta(?:ción|ndo).*?(\d+[\.,]?\d*)",
    "donaciones": r"donativos?|dona(?:ción|ndo)|ONG|fundación",
    "criptomonedas": r"cripto|bitcoin|ethereum|binance|coinbase",
    "alquiler": r"alquil(?:o|er)|inquilino|arrendamiento|(\d+).*mes.*piso",
    "autonomo_gastos": r"deducir.*gastos|factur(?:a|o)|suministros|coworking",
    "discapacidad": r"discapacidad|minusvalía|(\d+)\s*%.*discapacidad",
    "familia_numerosa": r"familia numerosa|3 hijos|4 hijos|título.*familia",
}
```

### Capa 2: LLM post-conversación (nuevo)

```python
# backend/app/services/conversation_analyzer.py
class ConversationAnalyzer:
    EXTRACTION_PROMPT = """
    Analiza esta conversación fiscal y extrae datos estructurados del usuario.
    Devuelve SOLO un JSON con los campos que se mencionan explícitamente.
    Si un dato no se menciona, NO lo incluyas.
    """

    async def analyze(self, conversation_id: str, user_id: str) -> dict:
        """Background task: se ejecuta al cerrar conversación o tras 5min inactivo"""
        messages = await conversation_service.get_messages(conversation_id)
        if len(messages) < 3:
            return {}  # no hay datos suficientes
        extracted = await openai_call("gpt-4o-mini", self.EXTRACTION_PROMPT, messages)
        await user_memory_service.merge_facts(user_id, extracted, source="llm")
        return extracted
```

### Prioridad de merge

```
manual (usuario edita perfil) > llm (post-conversación) > regex (tiempo real)
```

Campo `_source` existente en `datos_fiscales` JSON se reutiliza.

### Trigger

- FastAPI `BackgroundTasks` al finalizar conversación
- Conversaciones con < 3 mensajes no se analizan

---

## 4. Pre-calentamiento RAG + Bienvenida Personalizada

### Servicio

```python
# backend/app/services/warmup_service.py
class WarmupService:
    async def warmup(self, user_id: str) -> WarmupResult:
        profile = await fiscal_profile_service.get(user_id)
        ccaa = profile.ccaa_residencia
        territory = get_territory(ccaa)  # Plugin territorial

        # 1. Pre-cargar chunks RAG del territorio
        rag_chunks = await rag_search.preload(
            territory=ccaa,
            role=profile.situacion_laboral,
            limit=20
        )
        await conversation_cache.set_rag_context(user_id, rag_chunks)

        # 2. Generar bienvenida personalizada (gpt-4o-mini, ~0.001 USD)
        greeting = await self._generate_greeting(profile, territory)
        return WarmupResult(rag_preloaded=True, greeting=greeting)

    async def _generate_greeting(self, profile, territory) -> str:
        deadlines = territory.get_upcoming_deadlines()
        unclaimed = await deduction_service.get_unclaimed(profile)
        # Prompt corto → "Hola Fernando. Tienes el modelo 130 el 20 de abril..."
```

### Endpoint

```python
@router.post("/api/chat/warmup")
async def warmup_chat(request: Request, user = Depends(get_current_user)):
    result = await warmup_service.warmup(user.id)
    return {"greeting": result.greeting, "rag_preloaded": result.rag_preloaded}
```

### Frontend

```typescript
const openConversation = async (convId: string) => {
    const [conv, warmup] = await Promise.all([
        api.getConversation(convId),
        api.post('/api/chat/warmup')
    ]);
    if (warmup.greeting) {
        setMessages([{ role: 'assistant', content: warmup.greeting }]);
    }
};
```

### Reglas

- Usuario sin perfil fiscal → bienvenida genérica estática (sin LLM)
- Conversación existente con mensajes → solo pre-cargar RAG, no sobrescribir
- Rate limit: 1 warmup cada 5 minutos por usuario

---

## 5. Ventana Semántica (Context Compaction)

### Problema

`conversation_cache.py` envía los últimos 20 mensajes al LLM. Pierde contexto antiguo relevante.

### Solución

```python
# backend/app/services/semantic_window.py
class SemanticWindow:
    def __init__(self, max_messages: int = 15, recent_guaranteed: int = 5):
        self.max_messages = max_messages
        self.recent_guaranteed = recent_guaranteed

    async def select(self, conversation_id: str, current_query: str) -> list[Message]:
        all_messages = await conversation_service.get_messages(conversation_id)

        if len(all_messages) <= self.max_messages:
            return all_messages

        # Últimos 5 siempre incluidos
        recent = all_messages[-self.recent_guaranteed:]
        candidates = all_messages[:-self.recent_guaranteed]

        # Embed query actual
        query_embedding = await embed(current_query)

        # Score candidatos por similitud semántica
        scored = []
        for msg in candidates:
            msg_embedding = await get_or_create_embedding(msg.id, msg.content)
            score = cosine_similarity(query_embedding, msg_embedding)
            scored.append((score, msg))

        scored.sort(reverse=True)
        selected = [msg for _, msg in scored[:self.max_messages - self.recent_guaranteed]]

        # Ordenar cronológicamente
        selected.sort(key=lambda m: m.created_at)
        return selected + recent
```

### Cache de embeddings

- Mensajes son inmutables → embeddear una vez, cachear para siempre
- Opción A: nueva tabla `message_embeddings` en Turso (id, message_id, embedding BLOB)
- Opción B: Upstash Vector namespace `messages` (ya tenemos la infra)
- Decisión: **Opción B** (Upstash Vector) — evita almacenar blobs en SQLite, ya pagamos Upstash

### Integración

Reemplazar en `/api/ask/stream`:

```python
# Antes:
messages = await cache.get_recent_messages(user_id, limit=20)

# Después:
messages = await semantic_window.select(conversation_id, user_query)
```

### Coste

- Embedding por mensaje: ~50 tokens x $0.13/1M = despreciable
- Solo mensajes nuevos se embeddean
- Sin llamadas LLM extra — cosine similarity es cálculo local

---

## Orden de implementación

| Fase | Feature | Dependencias | Estimación |
|------|---------|-------------|------------|
| 1 | Modularización territorial | Ninguna | La más grande — base para todo |
| 2 | Eliminar Prometheus + Cost Tracker | Ninguna (parallelizable con F1) | Independiente |
| 3 | Memory Extraction LLM | F1 (usa territory plugins) | Requiere territories |
| 4 | Pre-calentamiento + Bienvenida | F1 + F3 (usa territory + memory) | Requiere ambos |
| 5 | Ventana Semántica | Ninguna (parallelizable con F3/F4) | Independiente |

### Paralelización con RuFlo

- **Wave 1**: F1 (territories, backend) + F2 (Prometheus cleanup, backend+frontend) en paralelo
- **Wave 2**: F3 (memory extraction) + F5 (semantic window) en paralelo
- **Wave 3**: F4 (warmup + bienvenida, backend+frontend) — depende de F1+F3

---

## Tests requeridos

- Todos los tests existentes de foral/territorial DEBEN seguir pasando tras modularización
- Nuevos tests unitarios para cada plugin territorial
- Tests de integración para cost_tracker, conversation_analyzer, warmup_service, semantic_window
- Tests E2E: bienvenida personalizada visible en chat

## Archivos afectados (principales)

### Modificar
- `backend/app/utils/irpf_simulator.py` — simplificar, delegar a plugins
- `backend/app/services/deduction_service.py` — delegar a plugins
- `backend/app/services/user_memory_service.py` — ampliar regex
- `backend/app/services/conversation_cache.py` — reemplazar con semantic_window
- `backend/app/main.py` — eliminar Prometheus, registrar territory plugins
- `backend/app/routers/irpf_estimate.py` — usar territory registry
- `backend/requirements.txt` — eliminar prometheus_client
- `frontend/src/hooks/useConversations.ts` — integrar warmup
- `frontend/src/pages/AdminDashboardPage.tsx` — widget de costes

### Crear
- `backend/app/territories/` — todo el directorio (6 archivos)
- `backend/app/services/cost_tracker.py`
- `backend/app/services/conversation_analyzer.py`
- `backend/app/services/warmup_service.py`
- `backend/app/services/semantic_window.py`
- `backend/app/routers/admin_costs.py` (o en admin.py existente)

### Eliminar
- `backend/app/metrics.py`
