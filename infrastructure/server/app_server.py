import logging
import time
from uuid import uuid4

from shared.log.logger import setup_logger, REQUEST_ID_CTX
from shared.tracing.tracer import setup_tracer
from shared.exception.exceptions import A2ARouterError

from infrastructure.config.config import settings

from agent import AgentImplementation
from a2a.envelope import A2AEnvelope

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi import status
from starlette.middleware.base import BaseHTTPMiddleware

from contextlib import asynccontextmanager

from opentelemetry import trace
from opentelemetry.trace.status import Status, StatusCode
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

#---------------------------------
# Initialize variables from environment
#---------------------------------
print("---" * 15)
print("Starting application with the following settings:")
for key, value in vars(settings).items():
    print(f"{key}: {value}")
print("---" * 15)

#---------------------------------
# Configure logging
#---------------------------------
setup_logger(settings.LOG_LEVEL, settings.APP_NAME, settings.OTEL_STDOUT_LOG_GROUP, settings.LOG_GROUP)
logger = logging.getLogger(__name__)

# Middleware to extract headers and add to request.state for tracing and logging
class MiddlewareHeaderContext(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        request_id = request.headers.get("x-request-id") or str(uuid4())
        authorization = request.headers.get("authorization")

        request_id_token = REQUEST_ID_CTX.set(request_id)

        request.state.request_id = request_id
        request.state.authorization = authorization
        
        try:
            response = await call_next(request)
            response.headers["x-request-id"] = request_id
            return response
        finally:
            REQUEST_ID_CTX.reset(request_id_token)

# ---------------------------------
# Lifespan (startup/shutdown)
# ---------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """ Load the ML model """
    logger.info(" **** Starting up the application...")

    logger.info(" **** Loading sub-agents...")        
    await agent.register_sub_agents(settings.URL_AGENT_REGISTER_00) 
    await agent.register_sub_agents(settings.URL_AGENT_REGISTER_01) 

    yield
    logger.info(" **** Shutting down the application...")
    logger.info(" **** Closing resources (5 seconds)...")
    time.sleep(0)
    logger.info(" **** Resources Closed...")
    logger.info(" **** Shutting down complete, bye ...")

# ---------------------------------
# Create FastAPI instance
# ---------------------------------
app = FastAPI(
    title="Stat Inference API",
    version="1.0.0",
    lifespan=lifespan
)
app.add_middleware(MiddlewareHeaderContext)

#---------------------------------
# Configure tracer
#---------------------------------
setup_tracer(settings.APP_NAME, settings.OTEL_EXPORTER_OTLP_ENDPOINT)
tracer = trace.get_tracer(__name__)

# Instrument FastAPI + requests
FastAPIInstrumentor.instrument_app(app)
RequestsInstrumentor().instrument()

agent = AgentImplementation()

# ---------------------------------------------------------------
# methods memory
# ---------------------------------------------------------------
@app.get("/info")
def get_info():
    with tracer.start_as_current_span("infrastructure.server.get_info") as span:
        """Get application settings information."""
        logger.info("func.get_info()")

        return settings

@app.get("/.well-known/agent.json")
def agent_card():
    with tracer.start_as_current_span("infrastructure.server.get_agent_card") as span:
        """Get application agent card information."""
        logger.info("func.get_agent_card()")
        
        return agent.capabilities

@app.get("/agent_card_register")
def train():
    with tracer.start_as_current_span("infrastructure.server.agent_card_register"):
        """Get all agents discovered."""
        logger.info("func.agent_card_register()")

        return agent.agent_card_register

@app.post("/a2a/message")
def handle_a2a_message(envelope: A2AEnvelope, request: Request):
    with tracer.start_as_current_span("infrastructure.server.handle_a2a_message") as span:
        """Handle an A2A message."""
        request_id = getattr(request.state, "request_id", "unknown")
        has_authorization = bool(getattr(request.state, "authorization", None))

        span.set_attribute("request.id", request_id)
        span.set_attribute("request.has_authorization", has_authorization)
        logger.info("func.handle_a2a_message() request_id=%s has_authorization=%s", request_id, has_authorization)
    
        try:
            result = agent.receive(envelope)

            span.set_status(Status(StatusCode.OK))
            return result
            
        except A2ARouterError as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            logger.warning(f"Bad request from A2ARouterError: {e}")
            return JSONResponse(content={"message": str(e)}, status_code=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            logger.error(f"Error uncaught exception: {e}")
            return JSONResponse(content={"message": str(e)}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)