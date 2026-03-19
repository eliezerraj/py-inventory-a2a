import os
from dotenv import load_dotenv

load_dotenv(".env")

class Settings:
    def __init__(self):
        self.VERSION = os.getenv("VERSION")
        self.ACCOUNT = os.getenv("ACCOUNT")
        self.APP_NAME = os.getenv("APP_NAME")

        self.HOST = os.getenv("HOST")
        self.URL_AGENT = os.getenv("URL_AGENT")
        self.PORT = os.getenv("PORT")
        self.SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT")) 

        self.WINDOWSIZE = int(os.getenv("WINDOWSIZE", "24"))  # Default to 24 if not set    
        self.URL_SERVICE_00 = os.getenv("URL_SERVICE_00")
        self.URL_SERVICE_01 = os.getenv("URL_SERVICE_01")

        self.URL_AGENT_REGISTER_00 = os.getenv("URL_AGENT_REGISTER_00")
        self.URL_AGENT_REGISTER_01 = os.getenv("URL_AGENT_REGISTER_01")

        self.OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
        self.OTEL_STDOUT_LOG_GROUP = os.getenv("OTEL_STDOUT_LOG_GROUP", "false").lower() == "true"
        self.LOG_GROUP = os.getenv("LOG_GROUP")

settings = Settings()
