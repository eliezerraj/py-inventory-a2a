import logging
from opentelemetry import trace

from domain.service.inventory_service import inventory_runout_analysis, price_analysis

#---------------------------------
# Configure logging
#---------------------------------
tracer = trace.get_tracer(__name__)
logger = logging.getLogger(__name__)

#---------------------------------
# Handler for price analysis
def handler_price_analysis(registry, payload: dict) -> dict:
    with tracer.start_as_current_span("infrastructure.adapter.handler.handler_price_analysis") as span:
        logger.info("def.handler_price_analysis()")  

        result = price_analysis(registry, payload["product"])
        
        return {
            "message": "price analysis requested",
            "result": result
        }
    
def handler_inventory_runout_analysis(registry, payload: dict) -> dict:
    with tracer.start_as_current_span("infrastructure.adapter.handler.handler_inventory_runout_analysis") as span:
        logger.info("def.handler_inventory_runout_analysis()")  

        result = inventory_runout_analysis(registry, payload["product"])
        
        return {
            "message": "inventory runout analysis requested",
            "result": result
        }