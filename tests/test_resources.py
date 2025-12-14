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
