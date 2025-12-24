"""Tests for blob storage operations."""

import pytest
from fastmcp.exceptions import ToolError
from mcp_resource_server import resources


class TestBlobRetrieval:
    """Test blob retrieval from storage."""

    def test_get_blob_bytes_valid(self, blob_storage, sample_blob):
        """Test reading valid blob."""
        blob_id = sample_blob['blob_id']

        # Need to reinitialize resources with correct storage
        import importlib
        importlib.reload(resources)

        data, content_type, filename = resources._get_blob_bytes(blob_id)

        assert data is not None
        assert content_type == "image/png"
        assert filename == "test.png"

    def test_get_blob_bytes_invalid_id(self):
        """Test with invalid blob ID format."""
        import importlib
        importlib.reload(resources)

        with pytest.raises(ToolError, match="Invalid blob"):
            resources._get_blob_bytes("not-a-blob-id")

    def test_get_blob_bytes_not_found(self):
        """Test with non-existent blob (valid format but doesn't exist)."""
        import importlib
        importlib.reload(resources)

        # Use a valid blob ID format that doesn't exist
        with pytest.raises(ToolError, match="(not found|missing)"):
            resources._get_blob_bytes("blob://1234567890-abcdef0123456789.txt")


class TestGetImage:
    """Test get_image tool."""

    def test_get_image_success(self, blob_storage, sample_blob):
        """Test successful image retrieval."""
        import importlib
        importlib.reload(resources)

        blob_id = sample_blob['blob_id']
        image = resources.get_image(blob_id)

        assert image is not None
        assert hasattr(image, 'data')

    def test_get_image_with_resize(self, blob_storage, sample_blob):
        """Test image retrieval with resize parameters."""
        import importlib
        importlib.reload(resources)

        blob_id = sample_blob['blob_id']
        image = resources.get_image(blob_id, max_width=50, max_height=50)

        assert image is not None

    def test_get_image_invalid_blob(self):
        """Test get_image with invalid blob ID."""
        import importlib
        importlib.reload(resources)

        with pytest.raises(ToolError):
            resources.get_image("invalid-blob-id")


class TestGetImageInfo:
    """Test get_image_info tool."""

    def test_get_image_info_success(self, blob_storage, sample_blob):
        """Test successful image info retrieval."""
        import importlib
        importlib.reload(resources)

        blob_id = sample_blob['blob_id']
        info = resources.get_image_info(blob_id)

        assert info.success is True
        assert info.width == 1
        assert info.height == 1
        assert info.format == "png"
        assert info.file_size_bytes > 0


class TestGetFile:
    """Test get_file tool."""

    def test_get_file_success(self, blob_storage, sample_blob):
        """Test successful file retrieval."""
        import importlib
        importlib.reload(resources)

        blob_id = sample_blob['blob_id']
        data = resources.get_file(blob_id)

        assert data is not None
        assert isinstance(data, bytes)
        assert len(data) > 0

    def test_get_file_invalid_blob(self):
        """Test get_file with invalid blob ID."""
        import importlib
        importlib.reload(resources)

        with pytest.raises(ToolError):
            resources.get_file("invalid-blob-id")


class TestImageSizeEstimate:
    """Test get_image_size_estimate tool."""

    def test_get_image_size_estimate_success(self, blob_storage, sample_blob):
        """Test successful size estimation."""
        import importlib
        importlib.reload(resources)

        blob_id = sample_blob['blob_id']
        estimate = resources.get_image_size_estimate(blob_id, max_width=512)

        assert estimate.success is True
        assert estimate.original_width == 1
        assert estimate.original_height == 1
        assert estimate.format == "png"
