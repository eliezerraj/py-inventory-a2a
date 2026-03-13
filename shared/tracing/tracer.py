from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import StatusCode, Status 
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.instrumentation.logging import LoggingInstrumentor

def setup_tracer(APP_NAME: str,
                 OTEL_EXPORTER_OTLP_ENDPOINT: str) -> None:

    resource = Resource.create({
                        "service.name": APP_NAME
                    })
    trace_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(trace_provider)

    # # Configure OTLP exporter and export spans via grpc
    otlp_exporter = OTLPSpanExporter(
        endpoint=OTEL_EXPORTER_OTLP_ENDPOINT,
    )
    trace_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    # Optional: metrics (disabled if not needed)
    metrics.set_meter_provider(MeterProvider(resource=resource))
    LoggingInstrumentor().instrument(set_logging_format=True)

    # create trace
    tracer = trace.get_tracer(APP_NAME)
