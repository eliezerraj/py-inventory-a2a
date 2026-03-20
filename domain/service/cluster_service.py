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

LIMIT=30
OFFSET=0

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

        if not product:
            logger.warning("No values enough provided for inventory inference.")
            return "false"
        
        sku = product.get('sku', '')
        
        headers = {"Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-Request-ID": REQUEST_ID_CTX.get()}

        res_list_inventory = send_message( f"{settings.URL_SERVICE_01}/list/inventory/product?sku={sku}&window={LIMIT}&offset={OFFSET}", 
            method="GET",
            headers=headers,
            timeout=10.0)

        raw_items = res_list_inventory.get("data", []) if isinstance(res_list_inventory.get("data"), dict) else res_list_inventory
        if isinstance(raw_items, dict):
            raw_items = raw_items.get("data", [])

        list_features = []
        list_skus = []
        for item in raw_items:
            product = item.get("product", {})
            sku = product.get("sku")
            if not sku:
                continue

            list_skus.append(sku)
            print(f"sku: {sku}")

            # get timeseries inventory data
            res_inventory_window = send_message( f"{settings.URL_SERVICE_01}/timeseries/product?sku={sku}&window={WINDOWSIZE}", 
                method="GET",
                headers=headers,
                timeout=10.0)

            raw_items = res_inventory_window.get("data", []) if isinstance(res_inventory_window.get("data"), dict) else res_inventory_window
            if isinstance(raw_items, dict):
                raw_items = raw_items.get("data", [])

            inventory_pending = []
            for item in raw_items:
                pending = item.get("pending") if isinstance(item, dict) else getattr(item, "pending", None)
                if pending is not None:
                    inventory_pending.append(pending)

            inventory_available = []
            for item in raw_items:
                available = item.get("available") if isinstance(item, dict) else getattr(item, "available", None)
                if available is not None:
                    inventory_available.append(available)

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
                    "data": inventory_available,
                }
            )
            
            inventory_available_stat= send_message(sub_agent_host,
                method="POST",
                headers=headers,
                body=envelope.model_dump() if hasattr(envelope, "model_dump") else envelope.dict(),
                timeout=10.0)

            # extract the features
            inventory_available_slope = (
                inventory_available_stat.get("data", {})
                .get("payload", {})
                .get("data", {})
                .get("n_slope")
            ) if isinstance(inventory_available_stat, dict) else None

            inventory_available_mean = (
                inventory_available_stat.get("data", {})
                .get("payload", {})
                .get("data", {})
                .get("mean")
            ) if isinstance(inventory_available_stat, dict) else None

            inventory_available_median_abs_deviation = (
                inventory_available_stat.get("data", {})
                .get("payload", {})
                .get("data", {})
                .get("median_abs_deviation")
            ) if isinstance(inventory_available_stat, dict) else None

            print("-------------inventory_data-----------------------")
            print(f"sku {sku} = {inventory_available}")
            print(inventory_available_slope)
            print(inventory_available_mean)
            print(inventory_available_median_abs_deviation)    
            print("-------------inventory_data-----------------------")

            features = {
                "feature_01": inventory_available_mean,
                "feature_02": inventory_available_median_abs_deviation,
                "feature_03": inventory_available_slope
            } 

            list_features.append(features)

        # ------------------------------------------
        # Cluster the products using the a2a cluster agent
        sub_agent = registry.get("CLUSTER_FIT")
        sub_agent_host = _get_sub_agent_url(sub_agent)
        sub_agent_name = sub_agent["name"]
        sub_agent_msg_type = "CLUSTER_FIT"
            
        envelope = A2AEnvelope(
            source_agent=settings.APP_NAME,
            target_agent=sub_agent_name,
            message_type=sub_agent_msg_type,
            payload=list_features
        )

        list_features_fitted= send_message(sub_agent_host,
                method="POST",
                headers=headers,
                body=envelope.model_dump() if hasattr(envelope, "model_dump") else envelope.dict(),
                timeout=10.0)

        return {"data": list_features_fitted.get('data',{}).get('payload',{}).get('data',{}) if isinstance(list_features_fitted, dict) else None    ,
                "metadata:" : {
                    "skus": list_skus,
                    "features": {
                        "feature_01": "inventory_available_mean",
                        "feature_02": "inventory_available_median_abs_deviation",
                        "feature_03": "inventory_available_slope"
                    }
                }
            }

def cluster_data(registry, product: dict) -> dict:
    with tracer.start_as_current_span("domain.service.cluster_data"):
        logger.info("def.cluster_data()")

        if not product:
            logger.warning("No values enough provided for inventory inference.")
            return "false"
        sku = product.get('sku', '')
        
        headers = {"Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-Request-ID": REQUEST_ID_CTX.get()}

        res_inventory_window = send_message( f"{settings.URL_SERVICE_01}/timeseries/product?sku={sku}&window={WINDOWSIZE}", 
            method="GET",
            headers=headers,
            timeout=10.0)

        raw_items = res_inventory_window.get("data", []) if isinstance(res_inventory_window.get("data"), dict) else res_inventory_window
        if isinstance(raw_items, dict):
            raw_items = raw_items.get("data", [])

        inventory_pending = []
        for item in raw_items:
            pending = item.get("pending") if isinstance(item, dict) else getattr(item, "pending", None)
            if pending is not None:
                inventory_pending.append(pending)

        inventory_available = []
        for item in raw_items:
            available = item.get("available") if isinstance(item, dict) else getattr(item, "available", None)
            if available is not None:
                inventory_available.append(available)

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
                "data": inventory_available,
            }
        )
        
        inventory_available_stat= send_message(sub_agent_host,
            method="POST",
            headers=headers,
            body=envelope.model_dump() if hasattr(envelope, "model_dump") else envelope.dict(),
            timeout=10.0)
        
        # extract the features
        inventory_available_slope = (
            inventory_available_stat.get("data", {})
            .get("payload", {})
            .get("data", {})
            .get("n_slope")
        ) if isinstance(inventory_available_stat, dict) else None

        inventory_available_mean = (
            inventory_available_stat.get("data", {})
            .get("payload", {})
            .get("data", {})
            .get("mean")
        ) if isinstance(inventory_available_stat, dict) else None

        inventory_available_median_abs_deviation = (
            inventory_available_stat.get("data", {})
            .get("payload", {})
            .get("data", {})
            .get("median_abs_deviation")
        ) if isinstance(inventory_available_stat, dict) else None


        print("-------------inventory_data-----------------------")
        print(f"sku {sku} = {inventory_available}")
        print(inventory_available_slope)
        print(inventory_available_mean)
        print(inventory_available_median_abs_deviation)    
        print("-------------inventory_data-----------------------")

        features = {
            "feature_01": inventory_available_mean,
            "feature_02": inventory_available_median_abs_deviation,
            "feature_03": inventory_available_slope
        } 

        # Cluster the products using the a2a cluster agent
        sub_agent = registry.get("CLUSTER_DATA")
        sub_agent_host = _get_sub_agent_url(sub_agent)
        sub_agent_name = sub_agent["name"]
        sub_agent_msg_type = "CLUSTER_DATA"
            
        envelope = A2AEnvelope(
            source_agent=settings.APP_NAME,
            target_agent=sub_agent_name,
            message_type=sub_agent_msg_type,
            payload=features
        )

        features_fitted=send_message(sub_agent_host,
                method="POST",
                headers=headers,
                body=envelope.model_dump() if hasattr(envelope, "model_dump") else envelope.dict(),
                timeout=10.0)
        
        return {"data": features_fitted.get('data',{}).get('payload',{}).get('cluster',{}) if isinstance(features_fitted, dict) else None    ,
                "metadata:" : {
                    "sku": sku,
                    "inventory_available": inventory_available,
                    "features": {
                        "feature_01": "inventory_available_mean",
                        "feature_02": "inventory_available_median_abs_deviation",
                        "feature_03": "inventory_available_slope"
                    }
                }
            }