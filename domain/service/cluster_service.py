import logging

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

WINDOWSIZE=settings.WINDOWSIZE

LIMIT=5
OFFSET=0
SKU="coffee"

#---------------------------------
def _get_sub_agent_url(sub_agent: dict) -> str | None:
    supported_interfaces = sub_agent.get("supportedInterfaces", []) if isinstance(sub_agent, dict) else []
    if supported_interfaces:
        first_interface = supported_interfaces[0]
        if isinstance(first_interface, dict):
            return first_interface.get("url")

    return sub_agent.get("url") if isinstance(sub_agent, dict) else None

def cluster_fit(registry, product: dict) -> dict:
    with tracer.start_as_current_span("domain.service.cluster_fit"):
        logger.info("def.cluster_fit()")

        headers = {"Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-Request-ID": REQUEST_ID_CTX.get()}

        res_list_inventory = send_message( f"{settings.URL_SERVICE_01}/list/inventory/product?sku={SKU}&window={LIMIT}&offset={OFFSET}", 
            method="GET",
            headers=headers,
            timeout=10.0)

        raw_items = res_list_inventory.get("data", []) if isinstance(res_list_inventory.get("data"), dict) else res_list_inventory
        if isinstance(raw_items, dict):
            raw_items = raw_items.get("data", [])

        #print("-------------raw_items-----------------------")
        #print(raw_items[:5])
        #print("-------------raw_items-----------------------")

        for item in raw_items:
            product = item.get("product", {})
            sku = product.get("sku")
            if not sku:
                continue

            print(f"sku: {sku}")

            res_inventory_window = send_message( f"{settings.URL_SERVICE_01}/timeseries/product?sku={sku}&window={WINDOWSIZE}", 
                method="GET",
                headers=headers,
                timeout=10.0)

            raw_items = res_inventory_window.get("data", []) if isinstance(res_inventory_window.get("data"), dict) else res_inventory_window
            if isinstance(raw_items, dict):
                raw_items = raw_items.get("data", [])

            data_pending = []
            for item in raw_items:
                pending = item.get("pending") if isinstance(item, dict) else getattr(item, "pending", None)
                if pending is not None:
                    data_pending.append(pending)

            data_available = []
            for item in raw_items:
                available = item.get("available") if isinstance(item, dict) else getattr(item, "available", None)
                if available is not None:
                    data_available.append(available)

            # -----------------------------------------------------
            # Calculate PENDING ORDER the stats using a2a stat
            sub_agent = registry.get("COMPUTE_STAT")
            sub_agent_host = _get_sub_agent_url(sub_agent)
            sub_agent_name = sub_agent["name"]
            sub_agent_msg_type = "COMPUTE_STAT"
            
            envelope = A2AEnvelope(
                source_agent=settings.APP_NAME,
                target_agent=sub_agent_name,
                message_type=sub_agent_msg_type,
                payload={
                    "data": data_pending,
                }
            )
            
            stats_pending = send_message(sub_agent_host,
                method="POST",
                headers=headers,
                body=envelope.model_dump() if hasattr(envelope, "model_dump") else envelope.dict(),
                timeout=10.0)

            slope_pending = (
                stats_pending.get("data", {})
                .get("payload", {})
                .get("data", {})
                .get("n_slope")
            ) if isinstance(stats_pending, dict) else None

            print("-------------stats_pending-----------------------")
            print(stats_pending)
            #print("-------------stats_available-----------------------")
            #print(stats_available)
            #print("-------------res_inventory_window-----------------------")
            #print(res_inventory_window)
            #print("-------------res_list_inventory-----------------------")
