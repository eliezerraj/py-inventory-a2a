# Define environment variables
export VERSION=0.1
export ACCOUNT=aws:999999999
export APP_NAME=py-inventory-a2a.localhost
export HOST=127.0.0.1
export URL_AGENT=http://127.0.0.1:7000
export PORT=7100
export URL_SERVICE_00=http://127.0.0.1:7000

export SESSION_TIMEOUT=3000
export OTEL_EXPORTER_OTLP_ENDPOINT=http://pi-home-01.architecture.caradhras.io:4318/v1/traces
export LOG_LEVEL=DEBUG
export OTEL_STDOUT_LOG_GROUP=True
export LOG_GROUP=/mnt/c/Eliezer/log/py-inventory-a2a.log

# Default target
all: env activate run

# Show environment variables
env:
	@echo "Current Environment Variables:"
	@echo "VERSION=$(VERSION)"
	@echo "APP_NAME=$(APP_NAME)"
	@echo "PORT=$(PORT)"
activate:
	@echo "Activate venv..."
	@bash -c "source ../.venv/bin/activate"

# Run the Go application
run:
	@echo "Running application with environment variables..."
	@bash -c "source ../.venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port $(PORT) --no-access-log --log-level debug"
    
.PHONY: all env run