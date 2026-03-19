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

            quantities = []
            prices = []

            for item in raw_items:
                quantity = item.get("quantity") if isinstance(item, dict) else getattr(item, "quantity", None)
                if quantity is not None:
                    quantities.append(quantity)
                price = item.get("price") if isinstance(item, dict) else getattr(item, "price", None)
                if price is not None:
                    prices.append(price)

            print("-------------quantities-----------------------")
            print(quantities)
            print("-------------prices-----------------------")
            print(prices)

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
                    "data": prices,
                }
            )
            
            stats_price = send_message(sub_agent_host,
                method="POST",
                headers=headers,
                body=envelope.model_dump() if hasattr(envelope, "model_dump") else envelope.dict(),
                timeout=10.0)
            
            slope_price = (
                stats_price.get("data", {})
                .get("payload", {})
                .get("data", {})
                .get("n_slope")
            ) if isinstance(stats_price, dict) else None

            mean_price = (
                stats_price.get("data", {})
                .get("payload", {})
                .get("data", {})
                .get("mean")
            ) if isinstance(stats_price, dict) else None

            #------------------------------------------------------
            # Calculate the QUANTITY stats using a2a stat
            envelope = A2AEnvelope(
                source_agent=settings.APP_NAME,
                target_agent=sub_agent_name,
                message_type=sub_agent_msg_type,
                payload={
                    "data": quantities,
                }
            )

            stats_quantity = send_message(sub_agent_host,
                method="POST",
                headers=headers,
                body=envelope.model_dump() if hasattr(envelope, "model_dump") else envelope.dict(),
                timeout=10.0)
            
            slope_quantity = (
                stats_quantity.get("data", {})
                .get("payload", {})
                .get("data", {})
                .get("n_slope")
            ) if isinstance(stats_quantity, dict) else None

            mean_quantity = (
                stats_quantity.get("data", {})
                .get("payload", {})
                .get("data", {})
                .get("mean")
            ) if isinstance(stats_quantity, dict) else None

            #------------------------------------------------------

            if slope_price < -2 and slope_quantity > 2:
                action = "INCREASING PRICE"
            elif slope_price < -2 and slope_quantity < -2:
                action = "STOP SALES 10(MINUTES) - CHECK QUALITY"
            elif slope_price > 2 and slope_quantity > 2:
                action = "STOP SALES 10(MINUTES) - RUNOUT RISK"
            else:
                action = "STEADY PRICE"

            result = {
                "sku": sku,
                "action": action,
                "metadata": {  
                    #"cart_item_quantities": quantities,
                    #"cart_item_prices": prices,
                    "mean_price": mean_price,
                    "n_slope_price": slope_price,
                    "mean_quantity": mean_quantity,
                    "n_slope_quantity": slope_quantity,
                }
            }

            data.append(result)

        return {"data": data}
    
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
        # get the timeseries inventory window data (service inventory)

        res_inventory_window = send_message( f"{settings.URL_SERVICE_01}/timeseries/product?sku={product.get('sku', '')}&window={WINDOWSIZE}", 
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

        print("-------------data_pending-----------------------")
        print(data_pending)
        print("-------------data_available-----------------------")
        print(data_available)

        # -----------------------------------------------------
        # Calculate PENDING OREDER the stats using a2a stat
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

        # -----------------------------------------------------
        # calculate INVENTORY AVAILABLE using a2a stat
        envelope = A2AEnvelope(
            source_agent=settings.APP_NAME,
            target_agent=sub_agent_name,
            message_type=sub_agent_msg_type,
            payload={
                "data": data_available,
            }
        )
        
        stats_available = send_message(sub_agent_host,
            method="POST",
            headers=headers,
            body=envelope.model_dump() if hasattr(envelope, "model_dump") else envelope.dict(),
            timeout=10.0)

        slope_available = (
            stats_available.get("data", {})
            .get("payload", {})
            .get("data", {})
            .get("n_slope")
        ) if isinstance(stats_available, dict) else None

        print("-------------stats_pending-----------------------")
        print(stats_pending)
        print("-------------stats_available-----------------------")
        print(stats_available)
        print("-------------res_inventory_window-----------------------")
        print(res_inventory_window)

        available = None
        lead_time = None
        if isinstance(res_inventory_window, dict):
            inventory_data = res_inventory_window.get("data", [])
            if isinstance(inventory_data, list) and len(inventory_data) > 0 and isinstance(inventory_data[-1], dict):
                available = inventory_data[-1].get("available")
                lead_time = inventory_data[-1].get("product", {}).get("lead_time")

        days_of_cover = available/abs(slope_pending) if slope_pending and slope_pending != 0 else None

        return {
            "sku": product.get("sku"),
            "action": "CRITICAL" if days_of_cover < inventory_data[-1].get("product", {}).get("lead_time", 0) else "OK",
            "metadata": {  
                "n_slope_sales_pending": slope_pending,
                "n_slope_inventory_available": slope_available,
                "inventory_available": available,
                "lead_time": lead_time,
                "days_of_cover": days_of_cover
            }
        }