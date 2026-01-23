"""
Prometheus Metrics Module for Impuestify

Custom metrics for monitoring:
- Token consumption (input/output)
- Request counts by endpoint
- Response times
- Active users
- Security blocks
- Demo endpoint usage
"""
from prometheus_client import Counter, Histogram, Gauge, Info
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_fastapi_instrumentator.metrics import Info as MetricInfo
import time
from functools import wraps
from typing import Callable

# === Token Metrics ===
TOKENS_INPUT = Counter(
    'impuestify_tokens_input_total',
    'Total input tokens consumed',
    ['model', 'endpoint']
)

TOKENS_OUTPUT = Counter(
    'impuestify_tokens_output_total',
    'Total output tokens generated',
    ['model', 'endpoint']
)

TOKENS_COST = Counter(
    'impuestify_tokens_cost_usd',
    'Estimated cost in USD',
    ['model']
)

# === Request Metrics ===
REQUESTS_TOTAL = Counter(
    'impuestify_requests_total',
    'Total requests by endpoint and status',
    ['endpoint', 'method', 'status', 'user_type']
)

RESPONSE_TIME = Histogram(
    'impuestify_response_time_seconds',
    'Response time in seconds',
    ['endpoint'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0]
)

# === User Metrics ===
ACTIVE_USERS = Gauge(
    'impuestify_active_users',
    'Number of active users in the last 24 hours'
)

UNIQUE_USERS_TOTAL = Counter(
    'impuestify_unique_users_total',
    'Total unique users'
)

# === Error Metrics ===
ERRORS_TOTAL = Counter(
    'impuestify_errors_total',
    'Total errors by type',
    ['endpoint', 'error_type', 'status_code']
)

# === Security Metrics ===
SECURITY_BLOCKS = Counter(
    'impuestify_security_blocks_total',
    'Security blocks by type',
    ['block_type']  # sql_injection, prompt_injection, guardrails, llama_guard
)

# === Demo Metrics ===
DEMO_REQUESTS = Counter(
    'impuestify_demo_requests_total',
    'Total demo endpoint requests',
    ['status']  # success, error, rate_limited
)

# === RAG Metrics ===
RAG_CHUNKS = Histogram(
    'impuestify_rag_chunks_retrieved',
    'Number of RAG chunks retrieved per query',
    buckets=[0, 1, 2, 3, 5, 7, 10]
)

RAG_SEARCH_TIME = Histogram(
    'impuestify_rag_search_seconds',
    'RAG search time in seconds',
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0]
)

# === LLM Metrics ===
LLM_LATENCY = Histogram(
    'impuestify_llm_latency_seconds',
    'LLM response latency',
    ['model'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0]
)

# === Application Info ===
APP_INFO = Info('impuestify_app', 'Application information')


# === Token Cost Calculation ===
# Pricing as of 2024 (per 1M tokens)
TOKEN_PRICING = {
    'gpt-4o': {'input': 2.50, 'output': 10.00},
    'gpt-4o-mini': {'input': 0.15, 'output': 0.60},
    'gpt-5-mini': {'input': 0.20, 'output': 0.80},  # Estimated
    'text-embedding-3-large': {'input': 0.13, 'output': 0.0},
}


def record_tokens(model: str, input_tokens: int, output_tokens: int, endpoint: str = 'chat'):
    """Record token usage and estimated cost"""
    TOKENS_INPUT.labels(model=model, endpoint=endpoint).inc(input_tokens)
    TOKENS_OUTPUT.labels(model=model, endpoint=endpoint).inc(output_tokens)
    
    # Calculate cost
    pricing = TOKEN_PRICING.get(model, {'input': 0.15, 'output': 0.60})
    cost = (input_tokens * pricing['input'] / 1_000_000) + \
           (output_tokens * pricing['output'] / 1_000_000)
    TOKENS_COST.labels(model=model).inc(cost)


def record_request(endpoint: str, method: str, status: int, user_type: str = 'authenticated'):
    """Record a request"""
    REQUESTS_TOTAL.labels(
        endpoint=endpoint,
        method=method,
        status=str(status),
        user_type=user_type
    ).inc()


def record_error(endpoint: str, error_type: str, status_code: int):
    """Record an error"""
    ERRORS_TOTAL.labels(
        endpoint=endpoint,
        error_type=error_type,
        status_code=str(status_code)
    ).inc()


def record_security_block(block_type: str):
    """Record a security block"""
    SECURITY_BLOCKS.labels(block_type=block_type).inc()


def record_demo_request(status: str):
    """Record a demo request"""
    DEMO_REQUESTS.labels(status=status).inc()


def record_rag_search(chunks_count: int, search_time: float):
    """Record RAG search metrics"""
    RAG_CHUNKS.observe(chunks_count)
    RAG_SEARCH_TIME.observe(search_time)


def record_llm_latency(model: str, latency: float):
    """Record LLM latency"""
    LLM_LATENCY.labels(model=model).observe(latency)


def set_active_users(count: int):
    """Set the active users gauge"""
    ACTIVE_USERS.set(count)


def set_app_info(version: str, environment: str):
    """Set application info"""
    APP_INFO.info({
        'version': version,
        'environment': environment,
        'name': 'Impuestify'
    })


# === Decorator for timing functions ===
def timed(endpoint: str):
    """Decorator to time function execution"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                RESPONSE_TIME.labels(endpoint=endpoint).observe(time.time() - start)
        return wrapper
    return decorator


# === Enhanced Instrumentator Setup ===
def setup_instrumentator(app):
    """Configure and return enhanced Prometheus instrumentator"""
    try:
        instrumentator = Instrumentator(
            should_group_status_codes=False,
            should_ignore_untemplated=True,
            excluded_handlers=["/health"],
        )
        
        # Instrument and expose
        instrumentator.instrument(app)
        instrumentator.expose(app, endpoint="/metrics", include_in_schema=True)
        
        print("✅ Prometheus /metrics endpoint configured")
        
        return instrumentator
    except Exception as e:
        print(f"❌ Error setting up Prometheus: {e}")
        raise
