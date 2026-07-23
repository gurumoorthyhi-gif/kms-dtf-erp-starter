"""HTTP client for the separate AI image engine."""

from __future__ import annotations

import json
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from uuid import uuid4

from app.modules.ai_engine.schemas import AIJobRequest, AIJobStatus, EngineJobResponse


class AIEngineError(RuntimeError):
    pass


class AIEngineUnavailableError(AIEngineError):
    pass


@dataclass(frozen=True, slots=True)
class HttpResponse:
    status: int
    body: bytes
    content_type: str = ""


class HttpTransport(Protocol):
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        body: bytes | None,
        timeout: float,
    ) -> HttpResponse: ...


class UrllibTransport:
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        body: bytes | None,
        timeout: float,
    ) -> HttpResponse:
        request = Request(url, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=timeout) as response:
                return HttpResponse(
                    response.status,
                    response.read(),
                    response.headers.get_content_type(),
                )
        except HTTPError as error:
            if error.code >= 500:
                raise AIEngineUnavailableError("AI image service is unavailable") from error
            raise AIEngineError(f"AI image service rejected the request ({error.code})") from error
        except (URLError, TimeoutError, OSError) as error:
            raise AIEngineUnavailableError("AI image service is unavailable") from error


class AIEngineClient:
    def __init__(
        self,
        base_url: str,
        api_key: str = "",
        *,
        transport: HttpTransport | None = None,
        timeout: float = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.transport = transport or UrllibTransport()
        self.timeout = timeout

    def submit(self, request: AIJobRequest) -> EngineJobResponse:
        boundary = f"kms-{uuid4().hex}"
        body = self._multipart(request, boundary)
        response = self._request(
            "POST",
            "/v1/jobs",
            body=body,
            content_type=f"multipart/form-data; boundary={boundary}",
        )
        return self._job_response(response)

    def status(self, job_id: str) -> EngineJobResponse:
        response = self._request("GET", f"/v1/jobs/{quote(job_id, safe='')}")
        return self._job_response(response)

    def cancel(self, job_id: str) -> None:
        self._request("DELETE", f"/v1/jobs/{quote(job_id, safe='')}")

    def download_result(self, job_id: str, destination: Path) -> Path:
        response = self._request("GET", f"/v1/jobs/{quote(job_id, safe='')}/result")
        if not response.body:
            raise AIEngineError("AI image service returned an empty result")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(response.body)
        return destination

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: bytes | None = None,
        content_type: str = "application/json",
    ) -> HttpResponse:
        headers = {"Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = content_type
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        response = self.transport.request(
            method,
            f"{self.base_url}{path}",
            headers=headers,
            body=body,
            timeout=self.timeout,
        )
        if response.status >= 500:
            raise AIEngineUnavailableError("AI image service is unavailable")
        if response.status >= 400:
            raise AIEngineError(f"AI image service returned HTTP {response.status}")
        return response

    @staticmethod
    def _job_response(response: HttpResponse) -> EngineJobResponse:
        try:
            payload = json.loads(response.body)
            status = AIJobStatus(payload["status"])
            return EngineJobResponse(
                str(payload["job_id"]),
                status,
                max(0, min(100, int(payload.get("progress", 0)))),
                str(payload.get("message", "")),
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise AIEngineError("AI image service returned an invalid response") from error

    @staticmethod
    def _multipart(request: AIJobRequest, boundary: str) -> bytes:
        metadata = json.dumps(
            {"tool": request.tool.value, "parameters": request.parameters},
            separators=(",", ":"),
        ).encode()
        source = request.source_path.read_bytes()
        mime_type = mimetypes.guess_type(request.source_path.name)[0] or "application/octet-stream"
        marker = boundary.encode()
        return b"".join(
            (
                b"--" + marker + b"\r\n",
                b'Content-Disposition: form-data; name="metadata"\r\n',
                b"Content-Type: application/json\r\n\r\n",
                metadata,
                b"\r\n--" + marker + b"\r\n",
                (
                    f'Content-Disposition: form-data; name="file"; '
                    f'filename="{request.source_path.name}"\r\n'
                ).encode(),
                f"Content-Type: {mime_type}\r\n\r\n".encode(),
                source,
                b"\r\n--" + marker + b"--\r\n",
            )
        )
