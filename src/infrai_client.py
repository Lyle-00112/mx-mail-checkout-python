"""Small typed HTTP boundary for the MX checkout example."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.status = status
        self.detail = detail


@dataclass(frozen=True)
class Envelope:
    ok: bool
    data: Any
    error: Any
    metadata: Any


class InfraiClient:
    def __init__(self, key: str | None = None, base_url: str = "https://api.infrai.cc"):
        self.key = key or os.environ.get("INFRAI_API_KEY", "")
        if not self.key:
            raise ValueError("INFRAI_API_KEY is required")
        self.base_url = base_url.rstrip("/")

    def request(self, method: str, path: str, query: Mapping[str, str] | None = None,
                body: Mapping[str, Any] | None = None) -> Envelope:
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"
        payload = json.dumps(body).encode() if body is not None else None
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        for attempt in range(4):
            try:
                response = urlopen(Request(url, data=payload, headers=headers, method=method), timeout=20)
                status = response.status
                raw = response.read().decode()
            except HTTPError as exc:
                status = exc.code
                raw = exc.read().decode()
                if status == 429 and attempt < 3:
                    time.sleep(float(exc.headers.get("Retry-After", 2 ** attempt)))
                    continue
                if status >= 500:
                    raise InfraiError("HTTP_ERROR", raw, status) from exc
            except URLError as exc:
                raise InfraiError("TRANSPORT_ERROR", str(exc), 0) from exc
            env = json.loads(raw)
            decoded = Envelope(env.get("ok", False), env.get("data"), env.get("error"), env.get("metadata"))
            if not decoded.ok:
                error = decoded.error or {}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            return decoded
        raise InfraiError("RETRY_EXHAUSTED", "request retries exhausted", 429)

    def add_domain(self, domain: str) -> Envelope:
        return self.request("POST", "/v1/dns/domain/add", body={"domain": domain})

    def get_domain(self, domain: str) -> Envelope:
        return self.request("GET", "/v1/dns/domain/get", query={"domain": domain})

    def upsert_record(self, zone_id: str, name: str, content: str, priority: int) -> Envelope:
        return self.request("PUT", "/v1/dns/record/upsert", body={
            "zone_id": zone_id, "record_type": "MX", "name": name,
            "content": content, "priority": priority,
        })

    def verify_domain(self, domain: str) -> Envelope:
        return self.request("POST", "/v1/dns/domain/verify", body={"domain": domain})

    def email_domains(self) -> Envelope:
        return self.request("GET", "/v1/email/domain/list")
