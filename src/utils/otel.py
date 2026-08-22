import os
import logging

logger = logging.getLogger(__name__)

OTEL_SERVICE_NAME = os.environ.get("OTEL_SERVICE_NAME", "bayesian-agi-core")


def setup_opentelemetry():
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        resource = Resource.create({"service.name": OTEL_SERVICE_NAME})
        provider = TracerProvider(resource=resource)

        exporter_type = os.environ.get("OTEL_EXPORTER", "console")
        if exporter_type == "otlp":
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318/v1/traces")
            span_exporter = OTLPSpanExporter(endpoint=endpoint)
        else:
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter
            span_exporter = ConsoleSpanExporter()

        processor = BatchSpanProcessor(span_exporter)
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

        logger.info(f"OpenTelemetry initialized (exporter={exporter_type}, service={OTEL_SERVICE_NAME})")
        return provider
    except ImportError:
        logger.warning("OpenTelemetry packages not installed. Run: pip install opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi")
        return None


def instrument_fastapi(app):
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumented with OpenTelemetry")
    except ImportError:
        logger.warning("OpenTelemetry FastAPI instrumentation not available")
