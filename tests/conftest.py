"""Test configuration for MCP Resource Server."""

import os
import pytest
from mcp_mapped_resource_lib import BlobStorage


@pytest.fixture
def sample_image_data():
    """Sample image data for testing."""
    # Simple 1x1 PNG image (67 bytes)
    return (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
        b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
        b'\x00\x0cIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-'
        b'\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )


@pytest.fixture
def sample_file_id():
    """Sample file identifier."""
    return "test_file_123"


@pytest.fixture
def blob_storage(tmp_path, monkeypatch):
    """Create temporary blob storage instance and set environment."""
    storage_root = str(tmp_path / "blob-storage")
    # Set environment variable before importing resources module
    monkeypatch.setenv("BLOB_STORAGE_ROOT", storage_root)

    # Create storage instance
    storage = BlobStorage(
        storage_root=storage_root,
        max_size_mb=10,
        default_ttl_hours=24,
        enable_deduplication=True
    )
    return storage


@pytest.fixture
def sample_blob(blob_storage, sample_image_data):
    """Create sample blob for testing."""
    result = blob_storage.upload_blob(
        data=sample_image_data,
        filename="test.png",
        tags=["test", "image"]
    )
    return result
