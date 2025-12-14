"""Test configuration for MCP Resource Server."""

import pytest


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
