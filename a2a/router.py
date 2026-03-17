import logging

from shared.exception.exceptions import A2ARouterError

from infrastructure.adapter.handler import handler_inventory_request, handler_inventory_runout_analysis

from opentelemetry import trace
from opentelemetry.sdk.trace import StatusCode, Status 

#---------------------------------
# Configure logging
#---------------------------------
tracer = trace.get_tracer(__name__)
logger = logging.getLogger(__name__)

#---------------------------------
# A2A Router
class A2ARouter:
    
    def route(self, registry, envelope):
        with tracer.start_as_current_span("a2a.router.route") as span:
            logger.info("def.route()")  

            try:
                if envelope.message_type == "INVENTORY_REQUEST":
                    return handler_inventory_request(registry, envelope.payload)
                elif envelope.message_type == "INVENTORY_RUNOUT_ANALYSIS":
                    return handler_inventory_runout_analysis(registry, envelope.payload)
                else:
                    message = f"Unsupported message type: {envelope.message_type}"
                    e = A2ARouterError(message)
                    raise e
                           
            except A2ARouterError as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                logger.error("Error A2ARouterError message", exc_info=e)
                raise e

            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                logger.error("Error uncaugth Exception", exc_info=e)
                raise e