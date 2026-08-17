"""
Tests for ProcessingOrchestrator.

All tests call `_run_sync` directly (the synchronous pipeline).
`run_as_background_task` is the thin wrapper that Starlette calls —
it is tested separately for semaphore + error-propagation behaviour.
"""

import uuid
from unittest.mock import MagicMock

import pytest

from app.ai.models import Chunk
from app.ai.processing_orchestrator import ProcessingOrchestrator


@pytest.fixture
def mock_job_repo(monkeypatch):
    mock = MagicMock()
    mock.claim_job.return_value = {"id": str(uuid.uuid4()), "status": "processing"}
    monkeypatch.setattr("app.ai.processing_orchestrator.job_repository", mock)
    return mock


@pytest.fixture
def mock_doc_repo(monkeypatch):
    mock = MagicMock()
    mock.update_document_status.return_value = True
    mock.update_document_metadata.return_value = None
    monkeypatch.setattr("app.ai.processing_orchestrator.document_repository", mock)
    return mock


@pytest.fixture
def mock_chunk_repo(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr("app.ai.processing_orchestrator.chunk_repository", mock)
    return mock


@pytest.fixture
def mock_storage(monkeypatch):
    mock = MagicMock()
    mock.download_document.return_value = b"fake pdf bytes"
    monkeypatch.setattr("app.ai.processing_orchestrator.storage_service", mock)
    return mock


@pytest.fixture
def orchestrator():
    o = ProcessingOrchestrator()
    o.vision_service = MagicMock()
    o.chunker = MagicMock()
    o.embedding_service = MagicMock()
    o.qdrant_service = MagicMock()
    return o


def _make_chunk(doc_id: str, user_id: str) -> Chunk:
    return Chunk(
        chunk_id=str(uuid.uuid4()),
        document_id=doc_id,
        user_id=user_id,
        chunk_index=0,
        chunk_type="text",
        content="Test content for embedding",
    )


def test_orchestrator_successful_processing(
    orchestrator, mock_job_repo, mock_doc_repo, mock_chunk_repo, mock_storage, monkeypatch
):
    job_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    chunk = _make_chunk(doc_id, user_id)

    mock_doc_repo.get_document_by_id.return_value = {
        "file_path": "fake/path.pdf",
        "file_type": "application/pdf",
        "title": "fake.pdf",
    }

    mock_normalized_doc = MagicMock()
    mock_normalized_doc.document_id = doc_id
    mock_normalized_doc.user_id = user_id
    mock_normalized_doc.page_count = 1
    mock_normalized_doc.processing_metadata = {}
    mock_normalized_doc.blocks = []

    mock_adapter = MagicMock()
    mock_adapter.parse.return_value = mock_normalized_doc
    monkeypatch.setattr(
        "app.ai.processing_orchestrator.get_adapter",
        MagicMock(return_value=mock_adapter),
    )

    orchestrator.vision_service.enrich.return_value = mock_normalized_doc
    orchestrator.chunker.chunk.return_value = [chunk]
    orchestrator.embedding_service.embed.return_value = [(chunk, [0.1] * 768)]

    orchestrator._run_sync(job_id, doc_id, user_id)

    mock_job_repo.claim_job.assert_called_once_with(job_id)
    mock_doc_repo.update_document_status.assert_any_call(doc_id, user_id, "processing")
    mock_doc_repo.update_document_status.assert_any_call(doc_id, user_id, "ready")
    mock_job_repo.complete_job.assert_called_once_with(job_id)
    orchestrator.qdrant_service.upsert.assert_called_once()
    mock_chunk_repo.insert_chunks.assert_called_once()
    mock_job_repo.fail_job.assert_not_called()


def test_orchestrator_skips_already_claimed_job(
    orchestrator, mock_job_repo, mock_doc_repo, mock_chunk_repo, mock_storage
):
    """If claim_job returns None the orchestrator must exit silently."""
    mock_job_repo.claim_job.return_value = None

    orchestrator._run_sync(str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4()))

    mock_doc_repo.update_document_status.assert_not_called()
    orchestrator.chunker.chunk.assert_not_called()
    orchestrator.embedding_service.embed.assert_not_called()


def test_orchestrator_handles_empty_download(
    orchestrator, mock_job_repo, mock_doc_repo, mock_chunk_repo, mock_storage
):
    """Empty download bytes must result in FAILED state."""
    doc_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    mock_storage.download_document.return_value = b""
    mock_doc_repo.get_document_by_id.return_value = {
        "file_path": "fake/path.pdf",
        "file_type": "application/pdf",
        "title": "fake.pdf",
    }

    orchestrator._run_sync(str(uuid.uuid4()), doc_id, user_id)

    mock_job_repo.fail_job.assert_called_once()
    mock_doc_repo.update_document_status.assert_any_call(doc_id, user_id, "failed")


def test_orchestrator_handles_empty_chunks(
    orchestrator, mock_job_repo, mock_doc_repo, mock_chunk_repo, mock_storage, monkeypatch
):
    """Chunker returning [] must result in FAILED state."""
    doc_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    mock_doc_repo.get_document_by_id.return_value = {
        "file_path": "fake/path.pdf",
        "file_type": "application/pdf",
        "title": "fake.pdf",
    }

    mock_normalized_doc = MagicMock()
    mock_normalized_doc.document_id = doc_id
    mock_normalized_doc.user_id = user_id
    mock_normalized_doc.page_count = 1
    mock_normalized_doc.processing_metadata = {}
    mock_normalized_doc.blocks = []

    mock_adapter = MagicMock()
    mock_adapter.parse.return_value = mock_normalized_doc
    monkeypatch.setattr(
        "app.ai.processing_orchestrator.get_adapter",
        MagicMock(return_value=mock_adapter),
    )
    orchestrator.vision_service.enrich.return_value = mock_normalized_doc
    orchestrator.chunker.chunk.return_value = []

    orchestrator._run_sync(str(uuid.uuid4()), doc_id, user_id)

    mock_job_repo.fail_job.assert_called_once()
    mock_doc_repo.update_document_status.assert_any_call(doc_id, user_id, "failed")


def test_orchestrator_handles_qdrant_failure(
    orchestrator, mock_job_repo, mock_doc_repo, mock_chunk_repo, mock_storage, monkeypatch
):
    """Qdrant upsert failure must result in FAILED state."""
    doc_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    chunk = _make_chunk(doc_id, user_id)

    mock_doc_repo.get_document_by_id.return_value = {
        "file_path": "fake/path.pdf",
        "file_type": "application/pdf",
        "title": "fake.pdf",
    }

    mock_normalized_doc = MagicMock()
    mock_normalized_doc.document_id = doc_id
    mock_normalized_doc.user_id = user_id
    mock_normalized_doc.page_count = 1
    mock_normalized_doc.processing_metadata = {}
    mock_normalized_doc.blocks = []

    mock_adapter = MagicMock()
    mock_adapter.parse.return_value = mock_normalized_doc
    monkeypatch.setattr(
        "app.ai.processing_orchestrator.get_adapter",
        MagicMock(return_value=mock_adapter),
    )
    orchestrator.vision_service.enrich.return_value = mock_normalized_doc
    orchestrator.chunker.chunk.return_value = [chunk]
    orchestrator.embedding_service.embed.return_value = [(chunk, [0.1] * 768)]
    orchestrator.qdrant_service.upsert.side_effect = Exception("Qdrant connection refused")

    orchestrator._run_sync(str(uuid.uuid4()), doc_id, user_id)

    mock_job_repo.fail_job.assert_called_once()
    mock_doc_repo.update_document_status.assert_any_call(doc_id, user_id, "failed")
    mock_job_repo.complete_job.assert_not_called()


def test_run_as_background_task_calls_run_sync(
    orchestrator, mock_job_repo, mock_doc_repo, mock_chunk_repo, mock_storage, monkeypatch
):
    """run_as_background_task must call _run_sync and release the semaphore."""
    job_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    called = []

    def fake_run_sync(jid, did, uid):
        called.append((jid, did, uid))

    monkeypatch.setattr(orchestrator, "_run_sync", fake_run_sync)

    orchestrator.run_as_background_task(job_id, doc_id, user_id)

    assert called == [(job_id, doc_id, user_id)]


def test_run_as_background_task_still_releases_semaphore_on_exception(
    orchestrator, mock_job_repo, mock_doc_repo, mock_chunk_repo, mock_storage, monkeypatch
):
    """Even if _run_sync raises, the threading.Semaphore must be released."""
    import app.ai.processing_orchestrator as orch_module

    initial_value = orch_module._thread_semaphore._value  # type: ignore[attr-defined]

    def exploding_run_sync(jid, did, uid):
        raise RuntimeError("Simulated crash")

    monkeypatch.setattr(orchestrator, "_run_sync", exploding_run_sync)

    # Should not raise externally — the wrapper catches it.
    orchestrator.run_as_background_task("j", "d", "u")

    # Semaphore must be back to its original value.
    assert orch_module._thread_semaphore._value == initial_value  # type: ignore[attr-defined]
