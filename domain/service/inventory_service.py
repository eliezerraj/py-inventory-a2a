import logging
import numpy as np

from shared.log.logger import REQUEST_ID_CTX
from a2a.envelope import A2AEnvelope

from infrastructure.adapter.http_client import send_message
from infrastructure.config.config import settings

from opentelemetry import trace

#---------------------------------
# Configure logging
#---------------------------------
tracer = trace.get_tracer(__name__)
logger = logging.getLogger(__name__)

#---------------------------------
# Compute Statistical Metrics

def inventory_request(registry, product: dict) -> dict:
    with tracer.start_as_current_span("domain.service.inventory_request"):
        logger.info("def.inventory_request()")    

        print("------------------------------------")
        print(registry)
        print("------------------------------------")
        print(product)
        print("------------------------------------")

        if not product:
            logger.warning("No values enough provided for inventory inference.")
            return "false"
        
        headers = {"Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-Request-ID": REQUEST_ID_CTX.get()}

        # -----------------------------------------------------
        # check and get the cart item data (service cart-item)
        res_cart_item_window = send_message(settings.URL_SERVICE_00 + "/cartItem/list/product/" + product.get("sku", ""), 
            method="GET",
            headers=headers,
            timeout=10.0)

        raw_items = res_cart_item_window.get("data", []) if isinstance(res_cart_item_window.get("data"), dict) else res_cart_item_window
        if isinstance(raw_items, dict):
            raw_items = raw_items.get("data", [])

        data = []
        for item in raw_items:
            quantity = item.get("quantity") if isinstance(item, dict) else getattr(item, "quantity", None)
            if quantity is not None:
                data.append(quantity)
            
        print("-------------data-----------------------")
        print(data)

        # Calculate the stats quantity using a2a stat
        sub_agent = registry.get("COMPUTE_STAT")
        sub_agent_host = sub_agent.get("url")
        sub_agent_name = sub_agent["name"]
        sub_agent_msg_type = "COMPUTE_STAT"
        
        envelope = A2AEnvelope(
            source_agent=settings.APP_NAME,
            target_agent=sub_agent_name,
            message_type=sub_agent_msg_type,
            payload={
                "data": data,
            }
        )
        
        stats = send_message(sub_agent_host + "/a2a/message", 
            method="POST",
            headers=headers,
            body=envelope.model_dump() if hasattr(envelope, "model_dump") else envelope.dict(),
            timeout=10.0)

        # -----------------------------------------------------
        # check and get the inventory data (service inventory)
        res_inventory = send_message(settings.URL_SERVICE_01 + "/inventory/product/" + product.get("sku", ""), 
            method="GET",
            headers=headers,
            timeout=10.0)

        print("-------------res_inventory-----------------------")
        print(res_inventory)

        return stats
    
def inventory_runout_analysis(registry, product: dict) -> dict:
    with tracer.start_as_current_span("domain.service.inventory_runout_analysis"):
        logger.info("def.inventory_runout_analysis()")    

        print("------------------------------------")
        print(registry)
        print("------------------------------------")
        print(product)
        print("------------------------------------")

        if not product:
            logger.warning("No values enough provided for inventory inference.")
            return "false"
        
        headers = {"Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-Request-ID": REQUEST_ID_CTX.get()}

        # -----------------------------------------------------
        # check and get the cart item data (service cart-item)
        res_cart_item_window = send_message(settings.URL_SERVICE_00 + "/cartItem/list/product/" + product.get("sku", ""), 
            method="GET",
            headers=headers,
            timeout=10.0)

        raw_items = res_cart_item_window.get("data", []) if isinstance(res_cart_item_window.get("data"), dict) else res_cart_item_window
        if isinstance(raw_items, dict):
            raw_items = raw_items.get("data", [])

        data = []
        for item in raw_items:
            quantity = item.get("quantity") if isinstance(item, dict) else getattr(item, "quantity", None)
            if quantity is not None:
                data.append(quantity)
            
        print("-------------data-----------------------")
        print(data)

        # Calculate the stats quantity using a2a stat
        sub_agent = registry.get("COMPUTE_STAT")
        sub_agent_host = sub_agent.get("url")
        sub_agent_name = sub_agent["name"]
        sub_agent_msg_type = "COMPUTE_STAT"
        
        envelope = A2AEnvelope(
            source_agent=settings.APP_NAME,
            target_agent=sub_agent_name,
            message_type=sub_agent_msg_type,
            payload={
                "data": data,
            }
        )
        
        stats = send_message(sub_agent_host + "/a2a/message", 
            method="POST",
            headers=headers,
            body=envelope.model_dump() if hasattr(envelope, "model_dump") else envelope.dict(),
            timeout=10.0)

        # -----------------------------------------------------
        # check and get the inventory data (service inventory)
        res_inventory = send_message(settings.URL_SERVICE_01 + "/inventory/product/" + product.get("sku", ""), 
            method="GET",
            headers=headers,
            timeout=10.0)

        print("-------------res_inventory-----------------------")
        print(res_inventory)

        return stats    