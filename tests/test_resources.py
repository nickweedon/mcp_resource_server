"""Tests for resource module."""

import os
from unittest.mock import Mock, patch

import pytest
import responses
from fastmcp.exceptions import ToolError

from mcp_resource_server import resources


class TestURLConfiguration:
    """Test URL pattern configuration."""

    def test_default_url_pattern(self):
        """Test default URL pattern."""
        # Default should be local filesystem
        assert resources.URL_PATTERN.startswith("file:///")

    def test_get_file_url_formatting(self):
        """Test URL formatting with file_id."""
        file_id = "test123"
        url = resources._get_file_url(file_id)
        assert file_id in url
        assert url.startswith(("http://", "https://", "file://"))


class TestFileDownload:
    """Test file download functionality."""

    @responses.activate
    def test_download_file_bytes_http(self, sample_file_id, monkeypatch):
        """Test HTTP file download."""
        # Override URL pattern to use HTTP for this test
        test_url_pattern = "https://example.com/files/{file_id}"
        monkeypatch.setattr(resources, "URL_PATTERN", test_url_pattern)

        test_content = b"test file content"
        url = resources._get_file_url(sample_file_id)

        responses.add(
            responses.GET,
            url,
            body=test_content,
            content_type="application/octet-stream",
            status=200,
        )

        data, content_type, filename = resources._download_file_bytes(sample_file_id)
        assert data == test_content
        assert content_type == "application/octet-stream"

    def test_download_file_bytes_missing_id(self):
        """Test error when file_id is missing."""
        with pytest.raises(ToolError, match="file_id is required"):
            resources._download_file_bytes("")


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

    def test_file_url_response(self):
        """Test FileUrlResponse dataclass."""
        response = resources.FileUrlResponse(
            success=True,
            url="https://example.com/file.pdf"
        )
        assert response.success is True
        assert response.url == "https://example.com/file.pdf"
        assert response.error is None

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


class TestToolFunctions:
    """Test public tool functions."""

    def test_get_file_url_success(self, sample_file_id):
        """Test get_file_url tool."""
        response = resources.get_file_url(sample_file_id)
        assert response.success is True
        assert response.url is not None
        assert sample_file_id in response.url

    def test_get_file_url_missing_id(self):
        """Test get_file_url with missing file_id."""
        response = resources.get_file_url("")
        assert response.success is False
        assert response.error == "file_id is required"


class TestBlobStorageIntegration:
    """Test blob storage integration with upload_*_resource functions."""

    @patch('mcp_resource_server.resources._download_image_cached')
    @patch('mcp_resource_server.resources._get_blob_storage')
    def test_upload_image_resource_success(self, mock_get_storage, mock_download, sample_image_data):
        """Test upload_image_resource returns correct metadata from storage."""
        # Mock download
        mock_download.return_value = (sample_image_data, "image/png", "test.png")

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
            "tags": ["resource-server", "image", "test123"]
        }

        # Call the function
        response = resources.upload_image_resource("test123", ttl_hours=24)

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

    @patch('mcp_resource_server.resources._download_file_bytes')
    @patch('mcp_resource_server.resources._get_blob_storage')
    def test_upload_file_resource_success(self, mock_get_storage, mock_download):
        """Test upload_file_resource returns correct metadata from storage."""
        # Mock download
        test_data = b"test file content"
        mock_download.return_value = (test_data, "application/pdf", "datasheet.pdf")

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
            "tags": ["resource-server", "file", "file456"]
        }

        # Call the function
        response = resources.upload_file_resource("file456", ttl_hours=48)

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

    @patch('mcp_resource_server.resources._download_image_cached')
    @patch('mcp_resource_server.resources._get_blob_storage')
    def test_upload_image_resource_not_an_image(self, mock_get_storage, mock_download):
        """Test upload_image_resource fails when file is not an image."""
        # Mock download returning non-image content
        mock_download.return_value = (b"not an image", "application/pdf", "file.pdf")

        # Should raise ToolError
        with pytest.raises(ToolError, match="File is not an image"):
            resources.upload_image_resource("bad_file")

    @patch('mcp_resource_server.resources._download_file_bytes')
    @patch('mcp_resource_server.resources._get_blob_storage')
    def test_upload_file_resource_storage_error(self, mock_get_storage, mock_download):
        """Test upload_file_resource handles storage errors."""
        # Mock download
        mock_download.return_value = (b"test", "application/pdf", "test.pdf")

        # Mock storage to raise exception
        mock_storage = Mock()
        mock_get_storage.return_value = mock_storage
        mock_storage.upload_blob.side_effect = Exception("Storage full")

        # Should raise ToolError with wrapped message
        with pytest.raises(ToolError, match="Failed to create file resource"):
            resources.upload_file_resource("test")

    @patch('mcp_resource_server.resources._download_image_cached')
    @patch('mcp_resource_server.resources._get_blob_storage')
    def test_upload_image_resource_invalid_quality(self, mock_get_storage, mock_download, sample_image_data):
        """Test upload_image_resource validates quality parameter."""
        # Mock download
        mock_download.return_value = (sample_image_data, "image/png", "test.png")

        # Should raise ToolError for invalid quality
        with pytest.raises(ToolError, match="quality must be between"):
            resources.upload_image_resource("test", quality=101)


class TestImageTools:
    """Test image tool functions with actual image data."""

    @responses.activate
    def test_get_image_info(self, sample_image_data, monkeypatch):
        """Test get_image_info returns correct metadata."""
        # Setup HTTP endpoint
        test_url_pattern = "https://example.com/files/{file_id}"
        monkeypatch.setattr(resources, "URL_PATTERN", test_url_pattern)

        responses.add(
            responses.GET,
            "https://example.com/files/test123",
            body=sample_image_data,
            content_type="image/png",
            status=200,
        )

        # Call get_image_info
        info = resources.get_image_info("test123")

        assert info.success is True
        assert info.width == 1
        assert info.height == 1
        assert info.format == "png"
        assert info.file_size_bytes == len(sample_image_data)

    @responses.activate
    def test_get_image_info_not_an_image(self, monkeypatch):
        """Test get_image_info fails for non-image files."""
        # Clear cache before test to avoid interference
        resources._image_cache.clear()

        test_url_pattern = "https://example.com/files/{file_id}"
        monkeypatch.setattr(resources, "URL_PATTERN", test_url_pattern)

        responses.add(
            responses.GET,
            "https://example.com/files/test_not_image",
            body=b"not an image",
            content_type="application/pdf",
            status=200,
        )

        # The function checks content-type first, so it will raise before trying to parse
        with pytest.raises(ToolError, match="File is not an image"):
            resources.get_image_info("test_not_image")

    @responses.activate
    def test_get_image_size_estimate(self, sample_image_data, monkeypatch):
        """Test get_image_size_estimate provides resize estimates."""
        test_url_pattern = "https://example.com/files/{file_id}"
        monkeypatch.setattr(resources, "URL_PATTERN", test_url_pattern)

        responses.add(
            responses.GET,
            "https://example.com/files/test123",
            body=sample_image_data,
            content_type="image/png",
            status=200,
        )

        # Image is 1x1, so no resize should occur with default max 1024
        estimate = resources.get_image_size_estimate("test123")

        assert estimate.success is True
        assert estimate.original_width == 1
        assert estimate.original_height == 1
        assert estimate.estimated_width == 1
        assert estimate.estimated_height == 1
        assert estimate.would_resize is False
        assert estimate.format == "png"

    @responses.activate
    def test_get_image(self, sample_image_data, monkeypatch):
        """Test get_image returns Image object."""
        test_url_pattern = "https://example.com/files/{file_id}"
        monkeypatch.setattr(resources, "URL_PATTERN", test_url_pattern)

        responses.add(
            responses.GET,
            "https://example.com/files/test123",
            body=sample_image_data,
            content_type="image/png",
            status=200,
        )

        # Get image
        from fastmcp.utilities.types import Image
        image = resources.get_image("test123")

        assert isinstance(image, Image)
        assert image._format == "png"
        assert len(image.data) > 0

    @responses.activate
    def test_get_file(self, monkeypatch):
        """Test get_file returns raw bytes."""
        test_url_pattern = "https://example.com/files/{file_id}"
        monkeypatch.setattr(resources, "URL_PATTERN", test_url_pattern)

        test_data = b"test file content"
        responses.add(
            responses.GET,
            "https://example.com/files/test456",
            body=test_data,
            content_type="application/pdf",
            status=200,
        )

        # Get file
        data = resources.get_file("test456")

        assert data == test_data


class TestImageCaching:
    """Test image caching functionality."""

    def test_cache_image_and_retrieve(self):
        """Test caching and retrieving images."""
        test_data = b"test image data"
        file_id = "cache_test"

        # Clear cache first
        resources._image_cache.clear()

        # Cache the image
        resources._cache_image(file_id, test_data, "image/png", "test.png")

        # Retrieve from cache
        cached = resources._get_cached_image(file_id)
        assert cached is not None
        data, content_type, filename = cached
        assert data == test_data
        assert content_type == "image/png"
        assert filename == "test.png"

    def test_cache_expiration(self):
        """Test that expired cache entries are not returned."""
        import time

        test_data = b"test image data"
        file_id = "expire_test"

        # Clear cache first
        resources._image_cache.clear()

        # Manually add expired entry
        resources._image_cache[file_id] = (
            test_data,
            "image/png",
            "test.png",
            time.time() - 400  # 400 seconds ago (TTL is 300 seconds)
        )

        # Should return None for expired entry
        cached = resources._get_cached_image(file_id)
        assert cached is None
        # And should be removed from cache
        assert file_id not in resources._image_cache


class TestFilenameExtraction:
    """Test filename extraction from headers."""

    def test_extract_filename_from_content_disposition(self):
        """Test extracting filename from Content-Disposition header."""
        headers = {"Content-Disposition": 'attachment; filename="document.pdf"'}
        filename = resources._extract_filename(headers, "test123", "application/pdf")
        assert filename == "document.pdf"

    def test_extract_filename_generated(self):
        """Test filename generation when header is missing."""
        headers = {}
        filename = resources._extract_filename(headers, "test123", "image/jpeg")
        assert filename == "test123.jpeg"

    def test_extract_filename_no_content_type(self):
        """Test filename extraction when content type is missing."""
        headers = {}
        filename = resources._extract_filename(headers, "test123", None)
        assert filename is None
