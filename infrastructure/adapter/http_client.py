import logging
from typing import Any

import httpx

from a2a.envelope import A2AEnvelope

from opentelemetry import trace
from opentelemetry.sdk.trace import StatusCode, Status

#---------------------------------
# Configure logging
#---------------------------------
tracer = trace.get_tracer(__name__)
logger = logging.getLogger(__name__)


def _extract_backend_message(response_body: Any) -> str | None:
    if isinstance(response_body, dict):
        message = response_body.get("message") or response_body.get("detail")
        if isinstance(message, str) and message.strip():
            return message
    return None


def _to_user_message(status_code: int, response_body: Any) -> str:
    backend_message = _extract_backend_message(response_body)

    if status_code in (200, 201):
        return backend_message or "Request completed successfully."
    if status_code == 202:
        return backend_message or "Request accepted and is being processed."
    if status_code == 204:
        return "Request completed successfully."
    if status_code == 400:
        return backend_message or "Invalid request. Please check your input."
    if status_code == 401:
        return "Authentication required. Please sign in."
    if status_code == 403:
        return "You do not have permission to perform this action."
    if status_code == 404:
        return backend_message or "Requested resource was not found."
    if status_code == 409:
        return backend_message or "Request conflicts with the current resource state."
    if status_code == 422:
        return backend_message or "Validation failed. Please review the provided data."
    if status_code == 429:
        return "Too many requests. Please try again shortly."
    if 500 <= status_code <= 599:
        return "Service is temporarily unavailable. Please try again later."

    return backend_message or "Unexpected response from service."

#------------------------------------
# Core request dispatcher
#------------------------------------
def _request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: Any | None = None,
    body: Any | None = None,
    timeout: float = 10.0,
) -> Any:
    """Send an HTTP request and return a normalized response object.

    Args:
        method:  HTTP verb (GET, POST, PUT, PATCH, DELETE, …).
        url:     Full request URL.
        headers: Optional HTTP headers.
        params:  Optional query-string parameters.
        body:    Optional JSON-serialisable payload for POST/PUT/PATCH.
        timeout: Request timeout in seconds (default 10).

    Returns:
        Dict with keys: ok, status_code, message, data.

    Raises:
        httpx.RequestError: For transport-level errors.
    """
    span_name = f"http_client.{method.lower()}"
    with tracer.start_as_current_span(span_name) as span:
        logger.info("http_client._request() method=%s url=%s", method, url)

        span.set_attribute("http.method", method.upper())
        span.set_attribute("http.url", url)

        try:
            with httpx.Client(timeout=timeout) as client:
                r = client.request(
                    method=method.upper(),
                    url=url,
                    headers=headers,
                    params=params,
                    json=body,
                )
                span.set_attribute("http.status_code", r.status_code)
                logger.debug("http_client response status=%s", r.status_code)

                response_body = None
                if r.content:
                    try:
                        response_body = r.json()
                    except ValueError:
                        response_body = {"raw": r.text}

                user_message = _to_user_message(r.status_code, response_body)
                ok = not r.is_error
                if not ok:
                    span.set_status(Status(StatusCode.ERROR, user_message))

                return {
                    "ok": ok,
                    "status_code": r.status_code,
                    "message": user_message,
                    "data": response_body,
                }

        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            logger.error("http_client error method=%s url=%s", method, url, exc_info=e)
            raise

#------------------------------------
# Per-verb convenience functions
#------------------------------------
def get(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    timeout: float = 10.0,
) -> Any:
    return _request("GET", url, headers=headers, params=params, timeout=timeout)

def post(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    body: Any | None = None,
    timeout: float = 10.0,
) -> Any:
    return _request("POST", url, headers=headers, params=params, body=body, timeout=timeout)


def put(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    body: Any | None = None,
    timeout: float = 10.0,
) -> Any:
    return _request("PUT", url, headers=headers, params=params, body=body, timeout=timeout)


def patch(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    body: Any | None = None,
    timeout: float = 10.0,
) -> Any:
    return _request("PATCH", url, headers=headers, params=params, body=body, timeout=timeout)


def delete(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    timeout: float = 10.0,
) -> Any:
    return _request("DELETE", url, headers=headers, params=params, timeout=timeout)

#------------------------------------
# Domain-level convenience wrapper
#------------------------------------
def send_message(
    target: str | dict,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    params: Any | None = None,
    body: Any | None = None,
    timeout: float = 10.0,
    envelope: A2AEnvelope | None = None,
) -> Any:
    """Flexible request helper.

    Supported forms:
    1) URL-based REST call:
       send_message("http://host/path", method="GET", params={...})
    2) Backward-compatible A2A call:
       send_message(agent_dict, envelope=envelope)
    """
    if isinstance(target, dict):
        if envelope is None:
            raise ValueError("envelope is required when target is an agent dict")

        url = f'{target["url"]}{target["endpoints"]["message"]}'
        envelope_body = envelope.model_dump() if hasattr(envelope, "model_dump") else envelope.dict()
        logger.debug("send_message agent url=%s", url)
        return post(url, headers=headers, params=params, body=envelope_body, timeout=timeout)

    logger.debug("send_message url=%s method=%s", target, method)
    return _request(
        method=method,
        url=target,
        headers=headers,
        params=params,
        body=body,
        timeout=timeout,
    )
