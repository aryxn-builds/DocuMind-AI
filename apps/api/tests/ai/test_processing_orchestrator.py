import pytest
import uuid
from unittest.mock import MagicMock, patch

from app.ai.processing_orchestrator import ProcessingOrchestrator
from app.repositories import document_repository, job_repository
from app.ai.models import Chunk

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
    monkeypatch.setattr("app.ai.processing_orchestrator.document_repository", mock)
    return mock

@pytest.fixture
def orchestrator(monkeypatch):
    orchestrator = ProcessingOrchestrator()
    orchestrator.vision_service = MagicMock()
    orchestrator.chunker = MagicMock()
    orchestrator.embedding_service = MagicMock()
    orchestrator.qdrant_service = MagicMock()
    return orchestrator

def test_orchestrator_successful_processing(orchestrator, mock_job_repo, mock_doc_repo, monkeypatch):
    # Setup mock behavior
    job_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    
    mock_chunk = Chunk(
        chunk_id=str(uuid.uuid4()),
        document_id=doc_id,
        user_id=user_id,
        chunk_index=0,
        chunk_type="text",
        content="Test content",
    )
    
    # Mock storage_service download
    mock_storage = MagicMock()
    mock_storage.download_document.return_value = b"fake pdf bytes"
    monkeypatch.setattr("app.ai.processing_orchestrator.storage_service", mock_storage)
    
    # Mock doc info return
    mock_doc_repo.get_document.return_value = {
        "file_path": "fake/path.pdf",
        "mime_type": "application/pdf",
        "title": "fake.pdf"
    }
    
    mock_normalized_doc = MagicMock()
    mock_normalized_doc.document_id = doc_id
    mock_normalized_doc.user_id = user_id
    mock_normalized_doc.page_count = 1
    mock_normalized_doc.processing_metadata = {}
    
    mock_adapter = MagicMock()
    mock_adapter.parse.return_value = mock_normalized_doc
    monkeypatch.setattr("app.ai.processing_orchestrator.get_adapter", MagicMock(return_value=mock_adapter))
    
    # Mock chunker returning chunks
    orchestrator.chunker.chunk.return_value = [mock_chunk]
    
    # Mock embedding returning vector
    orchestrator.embedding_service.embed.return_value = [(mock_chunk, [0.1, 0.2, 0.3])]
    
    # Mock db chunk insert
    mock_chunk_repo = MagicMock()
    monkeypatch.setattr("app.ai.processing_orchestrator.chunk_repository", mock_chunk_repo)
    
    # Execute
    orchestrator._run_sync(job_id, doc_id, user_id)
    
    # Assert state transitions
    mock_job_repo.claim_job.assert_called_once_with(job_id)
    mock_doc_repo.update_document_status.assert_any_call(doc_id, user_id, "processing")
    
    # Assert services called
    orchestrator.qdrant_service.upsert.assert_called_once()
    mock_chunk_repo.insert_chunks.assert_called_once()
    
    # Assert final success state
    mock_job_repo.complete_job.assert_called_once_with(job_id)
    # the exact status check might be "ready" in the orchestrator
    mock_doc_repo.update_document_status.assert_any_call(doc_id, user_id, "ready")

def test_orchestrator_handles_failure(orchestrator, mock_job_repo, mock_doc_repo, monkeypatch):
    job_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    
    # Mock storage_service download
    mock_storage = MagicMock()
    mock_storage.download_document.return_value = b"fake pdf bytes"
    monkeypatch.setattr("app.ai.processing_orchestrator.storage_service", mock_storage)
    
    # Mock doc info return
    mock_doc_repo.get_document.return_value = {
        "file_path": "fake/path.pdf",
        "mime_type": "application/pdf",
        "title": "fake.pdf"
    }
    
    mock_normalized_doc = MagicMock()
    mock_normalized_doc.document_id = doc_id
    mock_normalized_doc.user_id = user_id
    mock_normalized_doc.page_count = 1
    mock_normalized_doc.processing_metadata = {}
    
    mock_adapter = MagicMock()
    mock_adapter.parse.return_value = mock_normalized_doc
    monkeypatch.setattr("app.ai.processing_orchestrator.get_adapter", MagicMock(return_value=mock_adapter))
    
    orchestrator.chunker.chunk.return_value = []
    
    # Force failure in chunking to test fail states
    orchestrator.qdrant_service.upsert.side_effect = Exception("Qdrant error")
    
    # Execute
    orchestrator._run_sync(job_id, doc_id, user_id)
    
    # Assert failure states
    mock_job_repo.fail_job.assert_called_once()
    mock_doc_repo.update_document_status.assert_any_call(doc_id, user_id, "failed")
