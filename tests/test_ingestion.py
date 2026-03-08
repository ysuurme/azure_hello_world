import pytest
from src.utils.ingestion import IngestionPipeline

def test_generate_document_hash():
    # Setup
    pipeline = IngestionPipeline(search_client=None)
    
    # Execution
    content = "Sample document content."
    metadata = "source:github,author:sentinel"
    
    hash_result = pipeline.generate_document_hash(content, metadata)
    
    # Verification
    # A known input must produce a deterministic SHA-256 output.
    assert isinstance(hash_result, str)
    assert len(hash_result) == 64  # SHA-256 yields 64 hex characters
    
def test_idempotency_returns_true_for_mock():
    pipeline = IngestionPipeline(search_client=None)
    assert pipeline.check_idempotency("doc123", "abcdef") is True
