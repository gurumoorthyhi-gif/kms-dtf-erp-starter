import json
import threading
from pathlib import Path

import pytest

from app.modules.ai_engine import (
    AIEngineClient,
    AIEngineUnavailableError,
    AIJobManager,
    AIJobRequest,
    AIJobStatus,
    AITool,
    EngineJobResponse,
    HttpResponse,
)


class FakeTransport:
    def __init__(self, responses) -> None:
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, *, headers, body, timeout):
        self.calls.append((method, url, headers, body, timeout))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_client_submits_multipart_and_parses_progress(tmp_path: Path) -> None:
    source = tmp_path / "input.png"
    source.write_bytes(b"image-data")
    transport = FakeTransport(
        [
            HttpResponse(
                202,
                json.dumps({"job_id": "engine-1", "status": "queued", "progress": 0}).encode(),
            ),
            HttpResponse(
                200,
                b'{"job_id":"engine-1","status":"running","progress":45}',
            ),
        ]
    )
    client = AIEngineClient(
        "http://engine.test",
        "test-key",
        transport=transport,
    )

    submitted = client.submit(
        AIJobRequest(1, AITool.REMOVE_BACKGROUND, source, {"protect_subject": True})
    )
    progress = client.status(submitted.job_id)

    assert submitted.job_id == "engine-1"
    assert progress.status == AIJobStatus.RUNNING
    assert progress.progress == 45
    assert transport.calls[0][0:2] == (
        "POST",
        "http://engine.test/v1/jobs",
    )
    assert transport.calls[0][2]["Authorization"] == "Bearer test-key"
    assert b"remove_background" in transport.calls[0][3]
    assert b"image-data" in transport.calls[0][3]


def test_client_handles_unavailable_and_binary_result(tmp_path: Path) -> None:
    unavailable = AIEngineUnavailableError("offline")
    client = AIEngineClient(
        "http://engine.test",
        transport=FakeTransport([unavailable]),
    )
    with pytest.raises(AIEngineUnavailableError):
        client.status("job")

    destination = tmp_path / "result.png"
    client = AIEngineClient(
        "http://engine.test",
        transport=FakeTransport([HttpResponse(200, b"processed-image", "image/png")]),
    )
    assert client.download_result("job", destination) == destination
    assert destination.read_bytes() == b"processed-image"


class FakeResultHandler:
    def __init__(self, preview: Path) -> None:
        self.preview = preview
        self.saved = []

    def save(self, artwork_id: int, result_path: Path, tool_name: str) -> Path:
        self.saved.append((artwork_id, result_path, tool_name))
        return self.preview


class SuccessfulClient:
    def __init__(self) -> None:
        self.status_calls = 0
        self.cancelled = []

    def submit(self, request):
        return EngineJobResponse("engine-1", AIJobStatus.QUEUED)

    def status(self, job_id):
        self.status_calls += 1
        if self.status_calls == 1:
            return EngineJobResponse(job_id, AIJobStatus.RUNNING, 50, "Processing")
        return EngineJobResponse(job_id, AIJobStatus.COMPLETED, 100, "Done")

    def cancel(self, job_id):
        self.cancelled.append(job_id)

    def download_result(self, job_id, destination):
        destination.write_bytes(b"result")
        return destination


def request(tmp_path: Path) -> AIJobRequest:
    source = tmp_path / "source.png"
    source.write_bytes(b"source")
    return AIJobRequest(7, AITool.ENHANCE, source)


def test_job_manager_tracks_progress_and_saves_result(tmp_path: Path) -> None:
    client = SuccessfulClient()
    handler = FakeResultHandler(tmp_path / "preview.png")
    completed = threading.Event()
    updates = []

    def listener(snapshot):
        updates.append(snapshot)
        if snapshot.status == AIJobStatus.COMPLETED:
            completed.set()

    manager = AIJobManager(
        client,
        handler,
        tmp_path / "results",
        poll_interval=0.001,
        retry_delay=0.001,
    )
    job_id = manager.submit(request(tmp_path), listener)

    assert completed.wait(2)
    snapshot = manager.snapshot(job_id)
    assert snapshot.status == AIJobStatus.COMPLETED
    assert snapshot.progress == 100
    assert any(update.progress == 50 for update in updates)
    assert handler.saved[0][0] == 7
    assert handler.saved[0][2] == "enhance"
    manager.close()


class RetryClient(SuccessfulClient):
    def __init__(self) -> None:
        super().__init__()
        self.submit_calls = 0

    def submit(self, request):
        self.submit_calls += 1
        if self.submit_calls == 1:
            raise AIEngineUnavailableError("offline")
        return super().submit(request)


def test_unavailable_submission_is_retried(tmp_path: Path) -> None:
    client = RetryClient()
    completed = threading.Event()
    manager = AIJobManager(
        client,
        FakeResultHandler(tmp_path / "preview.png"),
        tmp_path / "results",
        poll_interval=0.001,
        retry_delay=0.001,
    )
    job_id = manager.submit(
        request(tmp_path),
        lambda snapshot: completed.set() if snapshot.status == AIJobStatus.COMPLETED else None,
    )

    assert completed.wait(2)
    assert manager.snapshot(job_id).attempts == 2
    manager.close()


def test_job_can_be_cancelled_without_blocking(tmp_path: Path) -> None:
    client = SuccessfulClient()
    manager = AIJobManager(
        client,
        FakeResultHandler(tmp_path / "preview.png"),
        tmp_path / "results",
        poll_interval=1,
    )
    job_id = manager.submit(request(tmp_path))
    manager.cancel(job_id)

    assert manager.snapshot(job_id).status == AIJobStatus.CANCELLED
    manager.close()


class FailedThenSuccessfulClient(SuccessfulClient):
    def __init__(self) -> None:
        super().__init__()
        self.job_number = 0

    def submit(self, request):
        self.job_number += 1
        return EngineJobResponse(f"engine-{self.job_number}", AIJobStatus.RUNNING)

    def status(self, job_id):
        if job_id == "engine-1":
            return EngineJobResponse(job_id, AIJobStatus.FAILED, 25, "Failed")
        return EngineJobResponse(job_id, AIJobStatus.COMPLETED, 100, "Done")


def test_failed_job_can_be_explicitly_retried(tmp_path: Path) -> None:
    client = FailedThenSuccessfulClient()
    manager = AIJobManager(
        client,
        FakeResultHandler(tmp_path / "preview.png"),
        tmp_path / "results",
        poll_interval=0.001,
    )
    failed = threading.Event()
    first_id = manager.submit(
        request(tmp_path),
        lambda snapshot: failed.set() if snapshot.status == AIJobStatus.FAILED else None,
    )
    assert failed.wait(2)

    completed = threading.Event()
    retry_id = manager.retry(
        first_id,
        lambda snapshot: completed.set() if snapshot.status == AIJobStatus.COMPLETED else None,
    )

    assert retry_id != first_id
    assert completed.wait(2)
    assert manager.snapshot(retry_id).status == AIJobStatus.COMPLETED
    manager.close()
