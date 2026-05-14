"""Requests session with structured outbound API logging."""
from __future__ import annotations

import json
import time
from typing import Any, Optional
from uuid import uuid4

import requests

from backend.app.core.logging import get_logger, mask_sensitive

logger = get_logger(__name__)


def _safe_json_from_response(response: requests.Response) -> Any:
    text = response.text.strip()
    if not text:
        return None
    try:
        return response.json()
    except ValueError:
        return text[:2000]


def _safe_json_from_body(body: Any) -> Any:
    if body is None:
        return None
    if isinstance(body, (dict, list)):
        return body
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="replace")
    if isinstance(body, str):
        try:
            return json.loads(body)
        except ValueError:
            return body[:2000]
    return str(body)[:2000]


class LoggedSession(requests.Session):
    """Drop-in `requests.Session` that logs masked request and response data."""

    def __init__(self, *, network: str, job_id: Optional[str] = None, step_id: Optional[str] = None) -> None:
        super().__init__()
        self.network = network
        self.job_id = job_id
        self.step_id = step_id

    def request(self, method: str, url: str, **kwargs):  # type: ignore[override]
        call_id = str(uuid4())
        start = time.perf_counter()
        request_body = kwargs.get("json", kwargs.get("data"))

        logger.info(
            "external_api_request",
            extra={
                "api_call_id": call_id,
                "network": self.network,
                "job_id": self.job_id,
                "step_id": self.step_id,
                "method": method.upper(),
                "url": url,
                "headers": mask_sensitive(dict(kwargs.get("headers") or {})),
                "params": mask_sensitive(kwargs.get("params") or {}),
                "body": mask_sensitive(_safe_json_from_body(request_body)),
            },
        )

        try:
            response = super().request(method, url, **kwargs)
        except requests.RequestException as exc:
            duration_ms = int((time.perf_counter() - start) * 1000)
            logger.exception(
                "external_api_request_failed",
                extra={
                    "api_call_id": call_id,
                    "network": self.network,
                    "job_id": self.job_id,
                    "step_id": self.step_id,
                    "method": method.upper(),
                    "url": url,
                    "duration_ms": duration_ms,
                },
            )
            raise exc

        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            "external_api_response",
            extra={
                "api_call_id": call_id,
                "network": self.network,
                "job_id": self.job_id,
                "step_id": self.step_id,
                "method": method.upper(),
                "url": url,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "headers": mask_sensitive(dict(response.headers)),
                "body": mask_sensitive(_safe_json_from_response(response)),
            },
        )
        return response
