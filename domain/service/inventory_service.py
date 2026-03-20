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

#---------------------------------
def _get_sub_agent_url(sub_agent: dict) -> str | None:
    supported_interfaces = sub_agent.get("supportedInterfaces", []) if isinstance(sub_agent, dict) else []
    if supported_interfaces:
        first_interface = supported_interfaces[0]
        if isinstance(first_interface, dict):
            return first_interface.get("url")

    return sub_agent.get("url") if isinstance(sub_agent, dict) else None

#---------------------------------
def price_analysis(registry, product: dict) -> dict:
    with tracer.start_as_current_span("domain.service.price_analysis"):
        logger.info("def.price_analysis()")    

        print("------------------------------------")
        print(product)
        print("------------------------------------")

        if not product:
            logger.warning("No values enough provided for inventory inference.")
            return "false"
        
        headers = {"Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-Request-ID": REQUEST_ID_CTX.get()}

        data = []
        for item in product:
            sku = item.get("sku")
            if not sku:
                continue

            # -----------------------------------------------------
            # check and get the cart item data (service cart-item) 
            res_cart_item_window = send_message(f"{settings.URL_SERVICE_00}/cartItem/list/product?sku={sku}&window={WINDOWSIZE}",
                method="GET",
                headers=headers,
                timeout=10.0)

            raw_items = res_cart_item_window.get("data", []) if isinstance(res_cart_item_window.get("data"), dict) else res_cart_item_window
            if isinstance(raw_items, dict):
                raw_items = raw_items.get("data", [])

            cart_quantities = []
            cart_prices = []

            for item in raw_items:
                quantity = item.get("quantity") if isinstance(item, dict) else getattr(item, "quantity", None)
                if quantity is not None:
                    cart_quantities.append(quantity)
                price = item.get("price") if isinstance(item, dict) else getattr(item, "price", None)
                if price is not None:
                    cart_prices.append(price)

            print("-------------quantities-----------------------")
            print(cart_quantities)
            print("-------------prices-----------------------")
            print(cart_prices)
            print("-------------prices-----------------------")

            # Calculate the PRICE stats using a2a stat
            sub_agent = registry.get("COMPUTE_STAT")
            sub_agent_host = _get_sub_agent_url(sub_agent)
            sub_agent_name = sub_agent["name"]
            sub_agent_msg_type = "COMPUTE_STAT"
            
            envelope = A2AEnvelope(
                source_agent=settings.APP_NAME,
                target_agent=sub_agent_name,
                message_type=sub_agent_msg_type,
                payload={
                    "data": cart_prices,
                }
            )
            
            prices_stats = send_message(sub_agent_host,
                method="POST",
                headers=headers,
                body=envelope.model_dump() if hasattr(envelope, "model_dump") else envelope.dict(),
                timeout=10.0)
            
            # extract features
            price_n_slope = (
                prices_stats.get("data", {})
                .get("payload", {})
                .get("data", {})
                .get("n_slope")
            ) if isinstance(prices_stats, dict) else None

            price_mean = (
                prices_stats.get("data", {})
                .get("payload", {})
                .get("data", {})
                .get("mean")
            ) if isinstance(prices_stats, dict) else None

            #------------------------------------------------------
            # Calculate the QUANTITY stats using a2a stat
            envelope = A2AEnvelope(
                source_agent=settings.APP_NAME,
                target_agent=sub_agent_name,
                message_type=sub_agent_msg_type,
                payload={
                    "data": cart_quantities,
                }
            )

            quantities_stats = send_message(sub_agent_host,
                method="POST",
                headers=headers,
                body=envelope.model_dump() if hasattr(envelope, "model_dump") else envelope.dict(),
                timeout=10.0)
            
            quantity_n_slope = (
                quantities_stats.get("data", {})
                .get("payload", {})
                .get("data", {})
                .get("n_slope")
            ) if isinstance(quantities_stats, dict) else None

            quantity_mean = (
                quantities_stats.get("data", {})
                .get("payload", {})
                .get("data", {})
                .get("mean")
            ) if isinstance(quantities_stats, dict) else None

            #------------------------------------------------------

            if price_n_slope < -2 and quantity_n_slope > 2:
                action = "INCREASING PRICE"
            elif price_n_slope < -2 and quantity_n_slope < -2:
                action = "STOP SALES 10(MINUTES) - CHECK QUALITY"
            elif price_n_slope > 2 and quantity_n_slope > 2:
                action = "STOP SALES 10(MINUTES) - RUNOUT RISK"
            else:
                action = "STEADY PRICE"

            result = {
                "sku": sku,
                "action": action,
                "metadata": {  
                    "price_mean": price_mean,
                    "price_n_slope": price_n_slope,
                    "quantity_mean": quantity_mean,
                    "quantity_n_slope": quantity_n_slope,
                    "cart_quantities": cart_quantities,
                    "cart_prices": cart_prices,
                }
            }

            data.append(result)

        return {"data": data}
    
def inventory_runout_analysis(registry, product: dict) -> dict:
    with tracer.start_as_current_span("domain.service.inventory_runout_analysis"):
        logger.info("def.inventory_runout_analysis()")    

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
        # get the timeseries inventory window data (service inventory). WINDONSIZE * 2 is because the endpoint returns dupe lines (pending and available in different lines )
        res_inventory_window = send_message( f"{settings.URL_SERVICE_01}/timeseries/product?sku={product.get('sku', '')}&window={WINDOWSIZE*2}", 
            method="GET",
            headers=headers,
            timeout=10.0)

        raw_items = res_inventory_window.get("data", []) if isinstance(res_inventory_window.get("data"), dict) else res_inventory_window
        if isinstance(raw_items, dict):
            raw_items = raw_items.get("data", [])

        #extract inventory only the lines with pending 
        raw_items = [item for item in raw_items if isinstance(item, dict) and "pending" in item]

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

        print("-------------inventory_pending-----------------------")
        print(inventory_pending)
        print("-------------inventory_available-----------------------")
        print(inventory_available)
        print("-------------inventory_available-----------------------")

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
                "data": inventory_pending,
            }
        )
        
        inventory_pending_stats = send_message(sub_agent_host,
            method="POST",
            headers=headers,
            body=envelope.model_dump() if hasattr(envelope, "model_dump") else envelope.dict(),
            timeout=10.0)

        # extract the features
        inventory_pending_slope = (
            inventory_pending_stats.get("data", {})
            .get("payload", {})
            .get("data", {})
            .get("n_slope")
        ) if isinstance(inventory_pending_stats, dict) else None

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
            timeout=10.0)

        # extract the features
        inventory_available_slope = (
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

        days_of_cover = current_inventory_available/abs(inventory_pending_slope) if inventory_pending_slope and inventory_pending_slope != 0 else None

        return {
            "sku": product.get("sku"),
            "action": "CRITICAL" if days_of_cover < inventory_data[-1].get("product", {}).get("lead_time", 0) else "OK",
            "metadata": {  
                "inventory_pending_slope": inventory_pending_slope,
                "inventory_available_slope": inventory_available_slope,
                "current_inventory_available": current_inventory_available,
                "lead_time": lead_time,
                "days_of_cover": days_of_cover,
                "inventory_pending": inventory_pending,
                "inventory_available": inventory_available
            }
        }