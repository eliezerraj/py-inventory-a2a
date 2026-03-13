import logging
from opentelemetry import trace

from domain.service.inventory_service import inventory_request

#---------------------------------
# Configure logging
#---------------------------------
tracer = trace.get_tracer(__name__)
logger = logging.getLogger(__name__)

#---------------------------------
# Handler for inventory request
def handler_inventory_request(payload: dict) -> dict:
    with tracer.start_as_current_span("infrastructure.adapter.handler.handler_inventory_request") as span:
        logger.info("def.handler_inventory_request()")  

        result = inventory_request(payload["product"])

        return {
            "message": "inventory requested",
            "result": result
        }