"""Tests for resource module."""

import os
from unittest.mock import Mock, patch

import pytest
import responses
from fastmcp.exceptions import ToolError

from mcp_resource_server import resources


class TestImageProcessing:
    """Test image processing functionality."""

    def test_calculate_resize_dimensions_no_resize_needed(self):
        """Test when image is already smaller than max dimensions."""
        width, height, should_resize = resources._calculate_resize_dimensions(
            original_width=512,
            original_height=384,
            max_width=1024,
            max_height=1024,
        )
        assert width == 512
        assert height == 384
        assert should_resize is False

    def test_calculate_resize_dimensions_with_resize(self):
        """Test when image needs resizing."""
        width, height, should_resize = resources._calculate_resize_dimensions(
            original_width=2048,
            original_height=1536,
            max_width=1024,
            max_height=1024,
        )
        assert width == 1024
        assert height == 768
        assert should_resize is True

    def test_calculate_resize_dimensions_disable_resize(self):
        """Test disabling resize with both dimensions = 0."""
        width, height, should_resize = resources._calculate_resize_dimensions(
            original_width=2048,
            original_height=1536,
            max_width=0,
            max_height=0,
        )
        assert width == 2048
        assert height == 1536
        assert should_resize is False

    def test_validate_quality_valid(self):
        """Test quality validation with valid values."""
        resources._validate_quality(1)
        resources._validate_quality(50)
        resources._validate_quality(100)
        resources._validate_quality(None)

    def test_validate_quality_invalid(self):
        """Test quality validation with invalid values."""
        with pytest.raises(ToolError, match="quality must be between"):
            resources._validate_quality(0)
        with pytest.raises(ToolError, match="quality must be between"):
            resources._validate_quality(101)


class TestDataclasses:
    """Test response dataclasses."""

    def test_image_info_response(self):
        """Test ImageInfoResponse dataclass."""
        response = resources.ImageInfoResponse(
            success=True,
            width=1920,
            height=1080,
            format="jpeg",
            file_size_bytes=524288
        )
        assert response.success is True
        assert response.width == 1920
        assert response.height == 1080

    def test_resource_response(self):
        """Test ResourceResponse dataclass."""
        response = resources.ResourceResponse(
            success=True,
            resource_id="blob://123-abc.png",
            filename="test.png",
            mime_type="image/png",
            size_bytes=1024,
            sha256="abc123",
            expires_at="2024-12-31T23:59:59Z"
        )
        assert response.success is True
        assert response.resource_id.startswith("blob://")


class TestBlobStorageIntegration:
    """Test blob storage integration with upload_*_resource functions."""

    @patch('mcp_resource_server.resources._get_blob_storage')
    def test_upload_image_resource_success(self, mock_get_storage, sample_image_data):
        """Test upload_image_resource returns correct metadata from storage."""
        # Mock storage and its methods
        mock_storage = Mock()
        mock_get_storage.return_value = mock_storage

        # Mock upload_blob to return only blob_id, file_path, sha256 (per mcp_mapped_resource_lib)
        mock_storage.upload_blob.return_value = {
            "blob_id": "blob://1234567890-abcdef123456.png",
            "file_path": "/mnt/blob-storage/12/34/blob://1234567890-abcdef123456.png",
            "sha256": "abc123def456"
        }

        # Mock get_metadata to return full metadata (per mcp_mapped_resource_lib)
        mock_storage.get_metadata.return_value = {
            "blob_id": "blob://1234567890-abcdef123456.png",
            "filename": "test.png",
            "mime_type": "image/png",
            "size_bytes": 2048,
            "sha256": "abc123def456",
            "expires_at": "2024-12-31T23:59:59Z",
            "created_at": "2024-12-30T23:59:59Z",
            "tags": ["resource-server", "image"]
        }

        # Call the function with raw bytes
        response = resources.upload_image_resource(sample_image_data, "test.png", ttl_hours=24)

        # Verify the response uses metadata for mime_type, size_bytes, expires_at
        assert response.success is True
        assert response.resource_id == "blob://1234567890-abcdef123456.png"
        assert response.filename == "test.png"
        assert response.mime_type == "image/png"  # From metadata, not upload result
        assert response.size_bytes == 2048  # From metadata, not upload result
        assert response.sha256 == "abc123def456"  # From upload result
        assert response.expires_at == "2024-12-31T23:59:59Z"  # From metadata, not created_at

        # Verify get_metadata was called
        mock_storage.get_metadata.assert_called_once_with("blob://1234567890-abcdef123456.png")

    @patch('mcp_resource_server.resources._get_blob_storage')
    def test_upload_file_resource_success(self, mock_get_storage):
        """Test upload_file_resource returns correct metadata from storage."""
        test_data = b"test file content"

        # Mock storage and its methods
        mock_storage = Mock()
        mock_get_storage.return_value = mock_storage

        # Mock upload_blob to return only blob_id, file_path, sha256 (per mcp_mapped_resource_lib)
        mock_storage.upload_blob.return_value = {
            "blob_id": "blob://1234567890-fedcba654321.pdf",
            "file_path": "/mnt/blob-storage/12/34/blob://1234567890-fedcba654321.pdf",
            "sha256": "fed123cba456"
        }

        # Mock get_metadata to return full metadata (per mcp_mapped_resource_lib)
        mock_storage.get_metadata.return_value = {
            "blob_id": "blob://1234567890-fedcba654321.pdf",
            "filename": "datasheet.pdf",
            "mime_type": "application/pdf",
            "size_bytes": 4096,
            "sha256": "fed123cba456",
            "expires_at": "2024-12-31T12:00:00Z",
            "created_at": "2024-12-30T12:00:00Z",
            "tags": ["resource-server", "file"]
        }

        # Call the function with raw bytes
        response = resources.upload_file_resource(test_data, "datasheet.pdf", ttl_hours=48)

        # Verify the response uses metadata for mime_type, size_bytes, expires_at
        assert response.success is True
        assert response.resource_id == "blob://1234567890-fedcba654321.pdf"
        assert response.filename == "datasheet.pdf"
        assert response.mime_type == "application/pdf"  # From metadata, not upload result
        assert response.size_bytes == 4096  # From metadata, not upload result
        assert response.sha256 == "fed123cba456"  # From upload result
        assert response.expires_at == "2024-12-31T12:00:00Z"  # From metadata expires_at, NOT created_at

        # Verify get_metadata was called
        mock_storage.get_metadata.assert_called_once_with("blob://1234567890-fedcba654321.pdf")

    def test_upload_image_resource_not_an_image(self):
        """Test upload_image_resource fails when file is not an image."""
        # Should raise ToolError when trying to open non-image bytes
        with pytest.raises(ToolError, match="Failed to create image resource"):
            resources.upload_image_resource(b"not an image", "file.pdf")

    @patch('mcp_resource_server.resources._get_blob_storage')
    def test_upload_file_resource_storage_error(self, mock_get_storage):
        """Test upload_file_resource handles storage errors."""
        # Mock storage to raise exception
        mock_storage = Mock()
        mock_get_storage.return_value = mock_storage
        mock_storage.upload_blob.side_effect = Exception("Storage full")

        # Should raise ToolError with wrapped message
        with pytest.raises(ToolError, match="Failed to create file resource"):
            resources.upload_file_resource(b"test", "test.pdf")

    def test_upload_image_resource_invalid_quality(self, sample_image_data):
        """Test upload_image_resource validates quality parameter."""
        # Should raise ToolError for invalid quality
        with pytest.raises(ToolError, match="quality must be between"):
            resources.upload_image_resource(sample_image_data, "test.png", quality=101)

    def test_upload_file_resource_empty_data(self):
        """Test upload_file_resource rejects empty data."""
        with pytest.raises(ToolError, match="data is required"):
            resources.upload_file_resource(b"", "test.pdf")

    def test_upload_file_resource_missing_filename(self):
        """Test upload_file_resource rejects missing filename."""
        with pytest.raises(ToolError, match="filename is required"):
            resources.upload_file_resource(b"test", "")

