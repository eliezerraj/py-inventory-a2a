import logging
from opentelemetry import trace

from domain.service.inventory_service import inventory_runout_analysis
from domain.service.cluster_service import cluster_fit, cluster_data
from shared.exception.exceptions import A2ARouterError

#---------------------------------
# Configure logging
#---------------------------------
tracer = trace.get_tracer(__name__)
logger = logging.getLogger(__name__)

#---------------------------------
def validate_payload(payload: dict) -> dict:
    if not payload:
        raise A2ARouterError("Payload is empty.")

    product = payload.get("product")
    if not product:
        raise A2ARouterError("Payload product is empty.")

    return payload

#---------------------------------
def handler_inventory_runout_analysis(registry, payload: dict) -> dict:
    with tracer.start_as_current_span("infrastructure.adapter.handler_inventory_runout_analysis") as span:
        logger.info("def.handler_inventory_runout_analysis()")  

        validated_payload = validate_payload(payload)

        result = inventory_runout_analysis(registry, validated_payload["product"], validated_payload.get("period", {}))
        
        return {
            "message": "inventory runout analysis requested",
            "result": result
        }
    
def handler_cluster_fit(registry, payload: dict) -> dict:
    with tracer.start_as_current_span("infrastructure.adapter.handler_cluster_fit") as span:
        logger.info("def.handler_cluster_fit()")  

        validated_payload = validate_payload(payload)

        result = cluster_fit(registry, validated_payload["product"])
        
        return {
            "message": "cluster fit analysis requested",
            "result": result
        }
    
def handler_cluster_data(registry, payload: dict) -> dict:
    with tracer.start_as_current_span("infrastructure.adapter.handler_cluster_data") as span:
        logger.info("def.handler_cluster_data()")  

        validated_payload = validate_payload(payload)

        result = cluster_data(registry, validated_payload["product"])
        
        return {
            "message": "cluster data analysis requested",
            "result": result
        }