"""
Prometheus метрики для мониторинга.
"""

try:
    from prometheus_client import Counter, Histogram, Gauge
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Mock для случая когда prometheus_client не установлен
    class Counter:
        def __init__(self, *args, **kwargs):
            pass
        def inc(self, *args, **kwargs):
            pass
    class Histogram:
        def __init__(self, *args, **kwargs):
            pass
        def observe(self, *args, **kwargs):
            pass
        def labels(self, **kwargs):
            return self
    class MockHistogram:
        def observe(self, *args, **kwargs):
            pass
    class Gauge:
        def __init__(self, *args, **kwargs):
            pass
        def set(self, *args, **kwargs):
            pass

# Токены
if PROMETHEUS_AVAILABLE:
    tokens_used = Counter(
        "agent_tokens_used_total",
        "Total tokens used",
        ["component"]
    )
else:
    # Mock для случая когда prometheus_client не установлен
    class MockCounter:
        def labels(self, **kwargs):
            return self
        def inc(self, *args, **kwargs):
            pass
    tokens_used = MockCounter()

if PROMETHEUS_AVAILABLE:
    tokens_per_query = Histogram(
        "agent_tokens_per_query",
        "Tokens per query",
        buckets=[100, 500, 1000, 2000, 5000]
    )
else:
    tokens_per_query = MockHistogram()

# Память
memory_size = Gauge(
    "agent_memory_size",
    "Memory size by level",
    ["level"]
)

# Латентность
if PROMETHEUS_AVAILABLE:
    retrieval_latency = Histogram(
        "retrieval_latency_seconds",
        "Retrieval latency",
        ["stage"],
        buckets=[0.01, 0.05, 0.1, 0.3, 0.5, 1.0]
    )
else:
    retrieval_latency = MockHistogram()

# Circuit Breaker
circuit_breaker_state = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half_open)",
    ["service"]
)

# Learning
if PROMETHEUS_AVAILABLE:
    strategy_success_rate = Gauge(
        "strategy_success_rate",
        "Strategy success rate",
        ["strategy_id"]
    )
else:
    # Mock для случая когда prometheus_client не установлен
    class MockGauge:
        def labels(self, **kwargs):
            return self
        def set(self, *args, **kwargs):
            pass
    strategy_success_rate = MockGauge()

