import logging
from opentelemetry import trace

from pydantic import BaseModel, Field

from datetime import datetime, timezone
from uuid import uuid4
from typing import Any

#---------------------------------
# Configure logging
#---------------------------------
tracer = trace.get_tracer(__name__)
logger = logging.getLogger(__name__)

class A2AEnvelope(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid4()))
    source_agent: str
    target_agent: str
    message_type: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    payload: Any

    @staticmethod
    def create(source, target, msg_type, payload):
        with tracer.start_as_current_span("a2a.create_envelope") as span:    
            logger.info("def.create()") 

            span.set_attribute("a2a.msg_type", msg_type)
            span.set_attribute("a2a.source", source)

            return A2AEnvelope(
                source_agent=source,
                target_agent=target,
                message_type=msg_type,
                payload=payload,
            )
