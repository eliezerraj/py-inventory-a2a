import logging
import numpy as np

from shared.log.logger import REQUEST_ID_CTX
from a2a.envelope import A2AEnvelope

from infrastructure.adapter.http_client import send_message
from infrastructure.config.config import settings

from domain.service.cluster_service import cluster_data

from opentelemetry import trace

#---------------------------------
# Configure logging
#---------------------------------
tracer = trace.get_tracer(__name__)
logger = logging.getLogger(__name__)

#default values for inventory runout analysis
WINDOWSIZE=settings.WINDOWSIZE
OFFSET=0
BUFFER=1

#---------------------------------
def _get_sub_agent_url(sub_agent: dict) -> str | None:
    supported_interfaces = sub_agent.get("supportedInterfaces", []) if isinstance(sub_agent, dict) else []
    if supported_interfaces:
        first_interface = supported_interfaces[0]
        if isinstance(first_interface, dict):
            return first_interface.get("url")

    return sub_agent.get("url") if isinstance(sub_agent, dict) else None

#---------------------------------

def calculate_stock_index(days_of_cover, lead_time):
    if lead_time == 0:
        return 1.0 if days_of_cover > 0 else 0.0
    
    # Calculate ratio
    index = days_of_cover / (lead_time * BUFFER)
    
    # Clamp the value between 0 and 1
    return max(0.0, min(1.0, index))

def calculate_acceleration_index(slope, days_of_cover, threshold=3.0):
    """
    Calculates a normalized Inventory Acceleration Index.
    
    Args:
        slope (float): Units lost per day (usually negative).
        days_of_cover (float): How many days current stock will last.
        threshold (float): velocity index of acceleration.
    
    Returns:
        float: A value between 0 (stuck) and 1 (full speed/critical).
    """
    # 1. Handle 'Stuck' or Restocking (Slope >= 0)
    if slope >= 0:
        return 0.0
    
    # 2. Handle 'Empty' (Days of Cover = 0)
    # If we are out of stock, we are at maximum 'urgency' status.
    if days_of_cover <= 0:
        return 1.0
    
    # 3. Calculate the raw ratio
    # Speed of depletion relative to the remaining time buffer
    abs_slope = abs(slope)
    raw_ratio = abs_slope / days_of_cover
    
    # 4. Normalize and Clamp
    normalized_val = raw_ratio / threshold
    
    print("**** normalized_val:", normalized_val)
    
    # Ensure result is between 0 and 1
    return float(np.clip(normalized_val, 0.0, 1.0))

"""
Steady Runout: Low Lead Time + High Inventory + Low Slope 
Warning Runout: Low Lead Time  + High Inventory + High Slope  
Critical Runout: High Lead Time  + Low Inventory +  High Slope  
"""
def inventory_runout_analysis(registry, product: dict, period: dict) -> dict:
    with tracer.start_as_current_span("domain.service.inventory_runout_analysis"):
        logger.info("def.inventory_runout_analysis()")    

        print("------------------------------------")
        print(product)
        print(period)
        print("------------------------------------")

        if not product:
            logger.warning("No values enough provided for inventory inference.")
            return "false"
        
        if not period:
            logger.warning("No period provided for inventory inference, using default values.")
            period = {"step_behind": WINDOWSIZE, "duration": OFFSET}
        
        headers = {"Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-Request-ID": REQUEST_ID_CTX.get()}

        # -----------------------------------------------------
        # get the timeseries inventory window data (service inventory).
        res_inventory_window = send_message( f"{settings.URL_SERVICE_01}/inventory/timeseries/product?sku={product.get('sku', '')}&window={period['duration']}&offset={period['step_behind']}", 
            method="GET",
            headers=headers,
            timeout=settings.REQUEST_TIMEOUT)

        raw_items = res_inventory_window.get("data", []) if isinstance(res_inventory_window.get("data"), dict) else res_inventory_window
        if isinstance(raw_items, dict):
            raw_items = raw_items.get("data", [])

        if not raw_items:
            logger.warning(f"No inventory data found for sku: {product.get('sku')}")
            return f"No inventory data found for sku: {product.get('sku')}"

        #extract inventory only the lines with sold 
        raw_items = [item for item in raw_items if isinstance(item, dict) and "sold" in item]

        if not raw_items:
            logger.warning(f"No valid sold items found in inventory data for sku: {product.get('sku')}")
            return f"No valid sold items found in inventory data for sku: {product.get('sku')}"

        inventory_sold = []
        for item in raw_items:
            sold = item.get("sold") if isinstance(item, dict) else getattr(item, "sold", None)
            if sold is not None:
                inventory_sold.append(sold)

        inventory_available = []
        for item in raw_items:
            available = item.get("available") if isinstance(item, dict) else getattr(item, "available", None)
            if available is not None:
                inventory_available.append(available)

        print("-------------inventory_sold-----------------------")
        print(inventory_sold)
        print("-------------inventory_available-----------------------")
        print(inventory_available)
        print("-------------inventory_available-----------------------")

        # -----------------------------------------------------
        # Calculate PENDING ORDER the stats using a2a stat
        sub_agent = registry.get("py-stat-inference-a2a.localhost")
        sub_agent_host = _get_sub_agent_url(sub_agent)
        sub_agent_name = sub_agent["name"]
        sub_agent_msg_type = "COMPUTE_STAT"
        
        envelope = A2AEnvelope(
            source_agent=settings.APP_NAME,
            target_agent=sub_agent_name,
            message_type=sub_agent_msg_type,
            payload={
                "data": inventory_sold,
            }
        )
        
        inventory_sold_stats = send_message(sub_agent_host,
            method="POST",
            headers=headers,
            body=envelope.model_dump() if hasattr(envelope, "model_dump") else envelope.dict(),
            timeout=settings.REQUEST_TIMEOUT)

        # extract the features
        inventory_sold_slope = (
            inventory_sold_stats.get("data", {})
            .get("payload", {})
            .get("data", {})
            .get("slope")
        ) if isinstance(inventory_sold_stats, dict) else None

        inventory_sold_n_slope = (
            inventory_sold_stats.get("data", {})
            .get("payload", {})
            .get("data", {})
            .get("n_slope")
        ) if isinstance(inventory_sold_stats, dict) else None
        
        # -----------------------------------------------------
        # calculate INVENTORY AVAILABLE using a2a stat
        envelope = A2AEnvelope(
            source_agent=settings.APP_NAME,
            target_agent=sub_agent_name,
            message_type=sub_agent_msg_type,
            payload={
                "data": inventory_available,
            }
        )
        
        inventory_available_stats = send_message(sub_agent_host,
            method="POST",
            headers=headers,
            body=envelope.model_dump() if hasattr(envelope, "model_dump") else envelope.dict(),
            timeout=settings.REQUEST_TIMEOUT)

        # extract the features
        inventory_available_slope = (
            inventory_available_stats.get("data", {})
            .get("payload", {})
            .get("data", {})
            .get("slope")
        ) if isinstance(inventory_available_stats, dict) else None

        inventory_available_n_slope = (
            inventory_available_stats.get("data", {})
            .get("payload", {})
            .get("data", {})
            .get("n_slope")
        ) if isinstance(inventory_available_stats, dict) else None
        
        #print("-------------inventory_pending_stats-----------------------")
        #print(inventory_pending_stats)
        #print("-------------inventory_available_stats-----------------------")
        #print(inventory_available_stats)
        #print("-------------res_inventory_window-----------------------")
        #print(res_inventory_window)

        current_inventory_available = None
        lead_time = None
        if isinstance(res_inventory_window, dict):
            inventory_data = res_inventory_window.get("data", [])
            if isinstance(inventory_data, list) and len(inventory_data) > 0 and isinstance(inventory_data[-1], dict):
                current_inventory_available = inventory_data[-1].get("available")
                lead_time = inventory_data[-1].get("product", {}).get("lead_time")

        days_of_cover = current_inventory_available/abs(inventory_available_slope) if inventory_available_slope and inventory_available_slope != 0 else None

        # Check the current cluster assigend
        res_cluster = cluster_data(registry, product)
        print("-------------cluster_data-----------------------")
        print(res_cluster)
        print("-------------cluster_data-----------------------")

        return {
            "sku": product.get("sku"),
            "action": "INVENTORY:CRITICAL" if days_of_cover < inventory_data[-1].get("product", {}).get("lead_time", 0) else "INVENTORY:OK",
            "k_means_data":{
                "cluster_id": res_cluster.get("data", {}).get("cluster", {}).get("id", "cluster_unknown") if isinstance(res_cluster, dict) else "cluster_unknown",
                "label_map": res_cluster.get("data", {}).get("label_map", {}) if isinstance(res_cluster, dict) else {},  
            },
            "metadata": {  
                "inventory_sold_slope": inventory_sold_slope,
                "inventory_sold_n_slope": inventory_sold_n_slope,
                "inventory_available_slope": inventory_available_slope,
                "inventory_available_n_slope": inventory_available_n_slope,
                "current_inventory_available": current_inventory_available,
                "lead_time": lead_time,
                "days_of_cover": days_of_cover,
                "normalized_data": {
                    "days_of_cover_index": calculate_stock_index(days_of_cover, lead_time) if days_of_cover is not None and lead_time is not None else None,                
                    "inventory_acceleration_index": calculate_acceleration_index(inventory_available_slope, days_of_cover) if inventory_available_slope is not None and days_of_cover is not None else None,
                },
                "data" : {
                    "inventory_sold": inventory_sold,
                    "inventory_available": inventory_available
                }
            }
        }
           
def inventory_windowed_runout_analysis(registry, product: dict, periods: list) -> list:
    with tracer.start_as_current_span("domain.service.inventory_windowed_runout_analysis"):
        logger.info("def.inventory_windowed_runout_analysis()")    

        print("------------------------------------")
        print(product)
        print(periods)
        print("------------------------------------")

        if not product:
            logger.warning("No values enough provided for inventory inference.")
            return ["false"]
        
        if not periods:
            logger.warning("No period provided for inventory inference, using default values.")
            periods = [{"step_behind": WINDOWSIZE, "duration": OFFSET}]
        elif isinstance(periods, dict):
            periods = [periods]
        
        headers = {"Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-Request-ID": REQUEST_ID_CTX.get()
                }

        results = []
        for period in periods:
            for key in ["step_behind", "duration"]:
                if key not in period:
                    logger.warning(f"Period missing '{key}' value for inventory inference, using default value.")
                    period[key] = WINDOWSIZE if key == "step_behind" else OFFSET
                    
            # -----------------------------------------------------
            # get the timeseries inventory window data (service inventory).
            res_inventory_window = send_message( f"{settings.URL_SERVICE_01}/inventory/timeseries/product?sku={product.get('sku', '')}&window={period['duration']}&offset={period['step_behind']}", 
                method="GET",
                headers=headers,
                timeout=settings.REQUEST_TIMEOUT)

            raw_items = res_inventory_window.get("data", []) if isinstance(res_inventory_window.get("data"), dict) else res_inventory_window
            if isinstance(raw_items, dict):
                raw_items = raw_items.get("data", [])

            if not raw_items:
                logger.warning(f"No inventory data found for sku: {product.get('sku')}")
                results.append(f"No inventory data found for sku: {product.get('sku')}")
                continue

            #extract inventory only the lines with sold 
            raw_items = [item for item in raw_items if isinstance(item, dict) and "sold" in item]

            if not raw_items:
                logger.warning(f"No valid sold items found in inventory data for sku: {product.get('sku')}")
                results.append(f"No valid sold items found in inventory data for sku: {product.get('sku')}")
                continue

            inventory_sold = []
            for item in raw_items:
                sold = item.get("sold") if isinstance(item, dict) else getattr(item, "sold", None)
                if sold is not None:
                    inventory_sold.append(sold)

            inventory_available = []
            for item in raw_items:
                available = item.get("available") if isinstance(item, dict) else getattr(item, "available", None)
                if available is not None:
                    inventory_available.append(available)

            print("-------------inventory_sold-----------------------")
            print(inventory_sold)
            print("-------------inventory_available-----------------------")
            print(inventory_available)
            print("-------------inventory_available-----------------------")

            # -----------------------------------------------------
            # Calculate PENDING ORDER the stats using a2a stat
            sub_agent = registry.get("py-stat-inference-a2a.localhost")
            sub_agent_host = _get_sub_agent_url(sub_agent)
            sub_agent_name = sub_agent["name"]
            sub_agent_msg_type = "COMPUTE_STAT"
            
            envelope = A2AEnvelope(
                source_agent=settings.APP_NAME,
                target_agent=sub_agent_name,
                message_type=sub_agent_msg_type,
                payload={
                    "data": inventory_sold,
                }
            )
            
            inventory_sold_stats = send_message(sub_agent_host,
                method="POST",
                headers=headers,
                body=envelope.model_dump() if hasattr(envelope, "model_dump") else envelope.dict(),
                timeout=settings.REQUEST_TIMEOUT)

            # extract the features
            inventory_sold_slope = (
                inventory_sold_stats.get("data", {})
                .get("payload", {})
                .get("data", {})
                .get("slope")
            ) if isinstance(inventory_sold_stats, dict) else None

            inventory_sold_n_slope = (
                inventory_sold_stats.get("data", {})
                .get("payload", {})
                .get("data", {})
                .get("n_slope")
            ) if isinstance(inventory_sold_stats, dict) else None
            
            # -----------------------------------------------------
            # calculate INVENTORY AVAILABLE using a2a stat
            envelope = A2AEnvelope(
                source_agent=settings.APP_NAME,
                target_agent=sub_agent_name,
                message_type=sub_agent_msg_type,
                payload={
                    "data": inventory_available,
                }
            )
            
            inventory_available_stats = send_message(sub_agent_host,
                method="POST",
                headers=headers,
                body=envelope.model_dump() if hasattr(envelope, "model_dump") else envelope.dict(),
                timeout=settings.REQUEST_TIMEOUT)

            # extract the features
            inventory_available_slope = (
                inventory_available_stats.get("data", {})
                .get("payload", {})
                .get("data", {})
                .get("slope")
            ) if isinstance(inventory_available_stats, dict) else None

            inventory_available_n_slope = (
                inventory_available_stats.get("data", {})
                .get("payload", {})
                .get("data", {})
                .get("n_slope")
            ) if isinstance(inventory_available_stats, dict) else None
            
            current_inventory_available = None
            lead_time = None
            if isinstance(res_inventory_window, dict):
                inventory_data = res_inventory_window.get("data", [])
                if isinstance(inventory_data, list) and len(inventory_data) > 0 and isinstance(inventory_data[-1], dict):
                    current_inventory_available = inventory_data[-1].get("available")
                    lead_time = inventory_data[-1].get("product", {}).get("lead_time")

            days_of_cover = current_inventory_available/abs(inventory_available_slope) if inventory_available_slope and inventory_available_slope != 0 else None

            results.append({
                "period": period,
                "action_doc": "DOC:INVENTORY:CRITICAL" if days_of_cover is not None and lead_time is not None and days_of_cover < lead_time else "DOC:INVENTORY:OK",
                "metadata": {  
                    "inventory_sold_slope": inventory_sold_slope,
                    "inventory_sold_n_slope": inventory_sold_n_slope,
                    "inventory_available_slope": inventory_available_slope,
                    "inventory_available_n_slope": inventory_available_n_slope,
                    "current_inventory_available": current_inventory_available,
                    "lead_time": lead_time,
                    "days_of_cover": days_of_cover,
                    "normalized_data": {
                        "days_of_cover_index": calculate_stock_index(days_of_cover, lead_time) if days_of_cover is not None and lead_time is not None else None,                
                        "inventory_acceleration_index": calculate_acceleration_index(inventory_available_slope, days_of_cover) if inventory_available_slope is not None and days_of_cover is not None else None,
                    },
                    "data" : {
                        "inventory_sold": inventory_sold,
                        "inventory_available": inventory_available
                    }
                }
            })

        res = {
            "sku": product.get("sku"), 
            "result_period": results
        }
        
        return res