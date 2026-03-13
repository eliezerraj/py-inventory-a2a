import logging
from opentelemetry import trace

from shared.log.logger import REQUEST_ID_CTX

import numpy as np

from domain.model.entities import Stat
from infrastructure.adapter.http_client import send_message
from infrastructure.config.config import settings

#---------------------------------
# Configure logging
#---------------------------------
tracer = trace.get_tracer(__name__)
logger = logging.getLogger(__name__)

#---------------------------------
# Compute Statistical Metrics

def inventory_request(product: dict) -> dict:
    with tracer.start_as_current_span("domain.service.inventory_request"):
        logger.info("def.inventory_request()")    
        logger.debug("values %s: ", product)

        if not product:
            logger.warning("No values enough provided for inventory inference.")
            return "false"
        
        headers = {"Content-Type": "application/json",
                    "Accept": "application/json",
                    "X-Request-ID": REQUEST_ID_CTX.get()}

        result = send_message(settings.URL_SERVICE_00 + "/inventory/product/" + product.get("sku", "")   , 
            method="GET",
            headers=headers,
            timeout=10.0)

        return result