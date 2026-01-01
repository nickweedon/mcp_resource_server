"""
Resources module.

Provides tool functions for blob storage operations:
- get_image: Retrieve and resize image from blob storage
- get_image_info: Get metadata about a blob image
- get_image_size_estimate: Estimate dimensions after resizing (dry run)
- get_file: Retrieve raw file bytes from blob storage
- get_file_info: Get filesystem path and metadata for a blob file
- upload_image_resource: Store image bytes in blob storage with optional resizing
- upload_file_resource: Store file bytes in blob storage
"""

import io
import os
from dataclasses import dataclass

from fastmcp.exceptions import ToolError
from fastmcp.utilities.types import Image
from mcp_mapped_resource_lib import BlobStorage, blob_id_to_path, BlobNotFoundError, InvalidBlobIdError
from PIL import Image as PILImage


# =============================================================================
# Constants
# =============================================================================

DEFAULT_MAX_DIMENSION = 1920  # Default max width in pixels
DEFAULT_MAX_HEIGHT = 1080  # Default max height in pixels
DEFAULT_JPEG_QUALITY = 85  # Default JPEG quality (1-100)
MIN_JPEG_QUALITY = 1
MAX_JPEG_QUALITY = 100

# Blob storage configuration
BLOB_STORAGE_ROOT = os.environ.get("BLOB_STORAGE_ROOT", "/mnt/blob-storage")
HOST_BLOB_STORAGE_ROOT = os.environ.get("HOST_BLOB_STORAGE_ROOT", "")
BLOB_STORAGE_MAX_SIZE_MB = int(os.environ.get("BLOB_MAX_SIZE_MB", "100"))
BLOB_STORAGE_TTL_HOURS = int(os.environ.get("BLOB_TTL_HOURS", "24"))

# Lazy initialization of blob storage
_blob_storage: BlobStorage | None = None


def _get_blob_storage() -> BlobStorage:
    """Get or create the blob storage instance."""
    global _blob_storage
    if _blob_storage is None:
        _blob_storage = BlobStorage(
            storage_root=BLOB_STORAGE_ROOT,
            max_size_mb=BLOB_STORAGE_MAX_SIZE_MB,
            default_ttl_hours=BLOB_STORAGE_TTL_HOURS,
            enable_deduplication=True,
        )
    return _blob_storage


def _get_blob_bytes(blob_id: str) -> tuple[bytes, str | None, str | None]:
    """
    Read blob bytes from shared storage volume.

    Args:
        blob_id: Blob URI (format: blob://TIMESTAMP-HASH.EXT)

    Returns:
        Tuple of (data, content_type, filename)

    Raises:
        ToolError: If blob_id is invalid or blob not found
    """
    if not blob_id:
        raise ToolError("blob_id is required")

    try:
        # Get filesystem path for the blob
        file_path = blob_id_to_path(blob_id, BLOB_STORAGE_ROOT)

        # Read file data
        with open(file_path, 'rb') as f:
            data = f.read()

        # Get metadata for content type and filename
        storage = _get_blob_storage()
        metadata = storage.get_metadata(blob_id)

        content_type = metadata.get("mime_type")
        filename = metadata.get("filename")

        return data, content_type, filename

    except InvalidBlobIdError as e:
        raise ToolError(f"Invalid blob:// URI format: {e}")
    except BlobNotFoundError as e:
        raise ToolError(f"Blob not found in storage: {e}")
    except FileNotFoundError:
        raise ToolError(f"Blob file missing from shared volume: {blob_id}")
    except Exception as e:
        raise ToolError(f"Failed to read blob: {e}")


# =============================================================================
# Response Types
# =============================================================================


@dataclass
class ImageInfoResponse:
    """Response containing image metadata without the image data."""

    success: bool
    width: int | None = None
    height: int | None = None
    format: str | None = None
    file_size_bytes: int | None = None
    host_path: str | None = None
    error: str | None = None


@dataclass
class ImageSizeEstimate:
    """Response containing estimated dimensions after resizing."""

    success: bool
    original_width: int | None = None
    original_height: int | None = None
    estimated_width: int | None = None
    estimated_height: int | None = None
    original_size_bytes: int | None = None
    estimated_size_bytes: int | None = None
    would_resize: bool = False
    format: str | None = None
    quality: int | None = None
    error: str | None = None


@dataclass
class ResourceResponse:
    """Response for resource-based file/image storage."""

    success: bool
    resource_id: str | None = None
    filename: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    sha256: str | None = None
    expires_at: str | None = None
    error: str | None = None


@dataclass
class FileInfoResponse:
    """Response containing filesystem path and metadata for a blob."""

    success: bool
    blob_id: str | None = None
    filename: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    host_path: str | None = None
    error: str | None = None


# =============================================================================
# Internal Helper Functions
# =============================================================================


def _calculate_resize_dimensions(
    original_width: int,
    original_height: int,
    max_width: int | None,
    max_height: int | None,
) -> tuple[int, int, bool]:
    """
    Calculate target dimensions preserving aspect ratio.

    Behavior based on parameter combinations:
    - Both None: Use defaults (1920x1080)
    - Only max_width None: Calculate width from height, maintaining aspect ratio
    - Only max_height None: Calculate height from width, maintaining aspect ratio
    - Both specified: Use both as constraints
    - Both 0: Disable resizing entirely
    - One 0: Ignore that dimension's constraint

    Args:
        original_width: Original image width in pixels
        original_height: Original image height in pixels
        max_width: Maximum width constraint (None for default/calculated, 0 to ignore)
        max_height: Maximum height constraint (None for default/calculated, 0 to ignore)

    Returns:
        Tuple of (new_width, new_height, would_resize)
    """
    # If both are 0, disable resizing
    if max_width == 0 and max_height == 0:
        return original_width, original_height, False

    # Determine effective constraints
    # If both are None, use defaults (1920x1080)
    # If only one is None, use no constraint on that axis (maintain aspect ratio)
    # If one is 0, use no constraint on that axis
    if max_width is None and max_height is None:
        # Both omitted - use defaults
        effective_max_width = DEFAULT_MAX_DIMENSION
        effective_max_height = DEFAULT_MAX_HEIGHT
    elif max_width is None:
        # Only width omitted - no width constraint, maintain aspect ratio from height
        effective_max_width = original_width
        effective_max_height = max_height if max_height != 0 else original_height
    elif max_height is None:
        # Only height omitted - no height constraint, maintain aspect ratio from width
        effective_max_width = max_width if max_width != 0 else original_width
        effective_max_height = original_height
    else:
        # Both specified - use them (handle 0 as no constraint)
        effective_max_width = original_width if max_width == 0 else max_width
        effective_max_height = original_height if max_height == 0 else max_height

    # Check if resize needed (never upscale)
    if original_width <= effective_max_width and original_height <= effective_max_height:
        return original_width, original_height, False

    # Calculate scale factor to fit in bounding box
    width_ratio = effective_max_width / original_width
    height_ratio = effective_max_height / original_height
    scale = min(width_ratio, height_ratio)

    new_width = max(1, int(original_width * scale))
    new_height = max(1, int(original_height * scale))

    return new_width, new_height, True


def _resize_image(
    image_data: bytes,
    image_format: str,
    max_width: int | None,
    max_height: int | None,
    quality: int | None,
) -> tuple[bytes, int, int]:
    """
    Resize image data, returning new bytes and dimensions.

    Args:
        image_data: Raw image bytes
        image_format: Format string (png, jpeg, etc.)
        max_width: Maximum width (0 to disable, None for default)
        max_height: Maximum height (0 to disable, None for default)
        quality: JPEG quality (ignored for non-JPEG)

    Returns:
        Tuple of (resized_bytes, new_width, new_height)
    """
    # Load image
    img = PILImage.open(io.BytesIO(image_data))
    original_width, original_height = img.size

    # Calculate new dimensions
    new_width, new_height, should_resize = _calculate_resize_dimensions(
        original_width, original_height, max_width, max_height
    )

    if not should_resize:
        return image_data, original_width, original_height

    # Resize using high-quality Lanczos filter
    img = img.resize((new_width, new_height), PILImage.Resampling.LANCZOS)

    # Save to bytes
    output = io.BytesIO()

    # Normalize format for PIL
    pil_format = image_format.upper()
    if pil_format == "JPG":
        pil_format = "JPEG"

    save_kwargs: dict = {}
    if pil_format == "JPEG":
        save_kwargs["quality"] = quality or DEFAULT_JPEG_QUALITY
        save_kwargs["optimize"] = True
        # Ensure RGB mode for JPEG (no alpha channel)
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")
    elif pil_format == "PNG":
        save_kwargs["optimize"] = True

    img.save(output, format=pil_format, **save_kwargs)
    return output.getvalue(), new_width, new_height


def _estimate_compressed_size(
    original_size: int,
    original_width: int,
    original_height: int,
    new_width: int,
    new_height: int,
    image_format: str,
    quality: int | None,
) -> int:
    """
    Estimate file size after resize (approximation).

    This uses a simple ratio-based calculation. Actual size depends
    on image content and compression efficiency.
    """
    # Calculate pixel ratio
    original_pixels = original_width * original_height
    new_pixels = new_width * new_height
    pixel_ratio = new_pixels / original_pixels if original_pixels > 0 else 1.0

    # Estimate based on pixel ratio
    estimated = int(original_size * pixel_ratio)

    # Apply quality factor for JPEG
    if image_format.lower() in ("jpeg", "jpg") and quality:
        # Quality affects size roughly linearly between 50-100
        quality_factor = quality / 100
        estimated = int(estimated * quality_factor)

    return max(estimated, 100)  # Minimum 100 bytes


def _validate_quality(quality: int | None) -> None:
    """Validate quality parameter if provided."""
    if quality is not None and (quality < MIN_JPEG_QUALITY or quality > MAX_JPEG_QUALITY):
        raise ToolError(f"quality must be between {MIN_JPEG_QUALITY} and {MAX_JPEG_QUALITY}")


# =============================================================================
# Tool Functions
# =============================================================================


def get_image(
    blob_id: str,
    max_width: int | None = None,
    max_height: int | None = None,
    quality: int | None = None,
) -> Image:
    """
    Retrieve and resize an image from blob storage.

    Images are automatically resized to fit within a 1920x1080 bounding box
    by default (when both max_width and max_height are omitted) to optimize
    for display. Aspect ratio is always preserved.

    Args:
        blob_id: Blob URI (format: blob://TIMESTAMP-HASH.EXT)
        max_width: Maximum width in pixels. If omitted while max_height is specified,
                   width will be calculated to maintain aspect ratio. If both are omitted,
                   defaults to 1920. Set to 0 with max_height=0 to disable resizing.
        max_height: Maximum height in pixels. If omitted while max_width is specified,
                    height will be calculated to maintain aspect ratio. If both are omitted,
                    defaults to 1080. Set to 0 with max_width=0 to disable resizing.
        quality: JPEG compression quality (1-100). Default: 85. Only applies to JPEG
                 images; ignored for PNG/GIF/WebP.

    Returns:
        Image object for rendering. The image is resized to fit
        within the specified constraints while preserving aspect ratio. Small
        images are never upscaled.

    Raises:
        ToolError: If the blob is not found, not an image, or quality is invalid

    Example:
        # Get image with default sizing (max 1920x1080)
        get_image("blob://1733437200-a3f9d8c2b1e4f6a7.png")

        # Get image with max width 800px, height calculated to maintain aspect ratio
        get_image("blob://1733437200-a3f9d8c2b1e4f6a7.png", max_width=800)

        # Get image with max height 600px, width calculated to maintain aspect ratio
        get_image("blob://1733437200-a3f9d8c2b1e4f6a7.png", max_height=600)

        # Get smaller thumbnail (square bounding box)
        get_image("blob://1733437200-a3f9d8c2b1e4f6a7.png", max_width=256, max_height=256)

        # Get original full-resolution image
        get_image("blob://1733437200-a3f9d8c2b1e4f6a7.png", max_width=0, max_height=0)

        # Get image with high quality JPEG
        get_image("blob://1733437200-a3f9d8c2b1e4f6a7.jpg", quality=95)
    """
    _validate_quality(quality)

    data, content_type, _ = _get_blob_bytes(blob_id)

    # Validate that this is an image
    if not content_type or not content_type.startswith("image/"):
        raise ToolError(f"Blob is not an image (content-type: {content_type})")

    # Extract format from content-type (e.g., "image/png" -> "png")
    image_format = content_type.split("/")[-1].split(";")[0]

    # Resize the image
    resized_data, _, _ = _resize_image(data, image_format, max_width, max_height, quality)

    return Image(data=resized_data, format=image_format)


def get_image_info(blob_id: str) -> ImageInfoResponse:
    """
    Get metadata about a blob image without resizing.

    Use this to check image dimensions and size before downloading.

    Args:
        blob_id: Blob URI (format: blob://TIMESTAMP-HASH.EXT)

    Returns:
        ImageInfoResponse with:
        - success: Whether the operation succeeded
        - width: Original image width in pixels
        - height: Original image height in pixels
        - format: Image format (png, jpeg, gif, webp)
        - file_size_bytes: Original file size in bytes
        - host_path: Path on the host filesystem (only included if HOST_BLOB_STORAGE_ROOT is set)
        - error: Error message if unsuccessful

    Raises:
        ToolError: If the blob is not found or not an image

    Example:
        # With HOST_BLOB_STORAGE_ROOT set
        info = get_image_info("blob://1733437200-a3f9d8c2b1e4f6a7.png")
        # ImageInfoResponse(success=True, width=2048, height=1536,
        #                   format='png', file_size_bytes=524288,
        #                   host_path='/workspace/blob-storage/a3/f9/1733437200-a3f9d8c2b1e4f6a7.png')

        # Without HOST_BLOB_STORAGE_ROOT set
        info = get_image_info("blob://1733437200-a3f9d8c2b1e4f6a7.png")
        # ImageInfoResponse(success=True, width=2048, height=1536,
        #                   format='png', file_size_bytes=524288)
    """
    data, content_type, _ = _get_blob_bytes(blob_id)

    # Validate that this is an image
    if not content_type or not content_type.startswith("image/"):
        raise ToolError(f"Blob is not an image (content-type: {content_type})")

    # Extract format from content-type (e.g., "image/png" -> "png")
    image_format = content_type.split("/")[-1].split(";")[0]

    # Get dimensions using PIL
    img = PILImage.open(io.BytesIO(data))
    width, height = img.size

    # Build response with conditional host_path
    response_data = {
        "success": True,
        "width": width,
        "height": height,
        "format": image_format,
        "file_size_bytes": len(data),
    }

    # Only include host_path if configured
    if HOST_BLOB_STORAGE_ROOT:
        container_path = blob_id_to_path(blob_id, BLOB_STORAGE_ROOT)
        relative_path = os.path.relpath(container_path, BLOB_STORAGE_ROOT)
        host_path = os.path.join(HOST_BLOB_STORAGE_ROOT, relative_path)
        response_data["host_path"] = host_path

    return ImageInfoResponse(**response_data)


def get_image_size_estimate(
    blob_id: str,
    max_width: int | None = None,
    max_height: int | None = None,
    quality: int | None = None,
) -> ImageSizeEstimate:
    """
    Estimate the dimensions and file size after resizing without returning the image.

    This is a "dry run" that predicts what get_image would return with the same
    parameters. Use this to decide if you need to adjust resize parameters before
    downloading the actual image.

    Args:
        blob_id: Blob URI (format: blob://TIMESTAMP-HASH.EXT)
        max_width: Maximum width in pixels. If omitted while max_height is specified,
                   width will be calculated to maintain aspect ratio. If both are omitted,
                   defaults to 1920.
        max_height: Maximum height in pixels. If omitted while max_width is specified,
                    height will be calculated to maintain aspect ratio. If both are omitted,
                    defaults to 1080.
        quality: JPEG compression quality (1-100). Default: 85.

    Returns:
        ImageSizeEstimate with:
        - success: Whether the operation succeeded
        - original_width: Original image width in pixels
        - original_height: Original image height in pixels
        - estimated_width: Width after resize
        - estimated_height: Height after resize
        - original_size_bytes: Original file size in bytes
        - estimated_size_bytes: Estimated file size after resize (approximate)
        - would_resize: Whether the image would be resized
        - format: Image format
        - quality: Quality setting that would be used for JPEG
        - error: Error message if unsuccessful

    Note:
        The estimated_size_bytes is an approximation. Actual size may vary by
        10-20% depending on image content and compression efficiency.

    Raises:
        ToolError: If the blob is not found, not an image, or quality is invalid

    Example:
        estimate = get_image_size_estimate("blob://1733437200-a3f9d8c2b1e4f6a7.jpg", max_width=512)
        # ImageSizeEstimate(success=True, original_width=2048, original_height=1536,
        #                   estimated_width=512, estimated_height=384,
        #                   original_size_bytes=524288, estimated_size_bytes=65536,
        #                   would_resize=True, format='jpeg', quality=85)
    """
    _validate_quality(quality)

    data, content_type, _ = _get_blob_bytes(blob_id)

    # Validate that this is an image
    if not content_type or not content_type.startswith("image/"):
        raise ToolError(f"File is not an image (content-type: {content_type})")

    # Extract format from content-type (e.g., "image/png" -> "png")
    image_format = content_type.split("/")[-1].split(";")[0]

    # Get original dimensions using PIL
    img = PILImage.open(io.BytesIO(data))
    original_width, original_height = img.size
    original_size = len(data)

    # Calculate estimated dimensions
    estimated_width, estimated_height, would_resize = _calculate_resize_dimensions(
        original_width, original_height, max_width, max_height
    )

    # Determine effective quality
    effective_quality = quality or DEFAULT_JPEG_QUALITY

    # Estimate compressed size
    estimated_size = _estimate_compressed_size(
        original_size,
        original_width,
        original_height,
        estimated_width,
        estimated_height,
        image_format,
        effective_quality if image_format.lower() in ("jpeg", "jpg") else None,
    )

    return ImageSizeEstimate(
        success=True,
        original_width=original_width,
        original_height=original_height,
        estimated_width=estimated_width,
        estimated_height=estimated_height,
        original_size_bytes=original_size,
        estimated_size_bytes=estimated_size,
        would_resize=would_resize,
        format=image_format,
        quality=effective_quality if image_format.lower() in ("jpeg", "jpg") else None,
    )


def get_file(blob_id: str) -> bytes:
    """
    Retrieve raw file bytes from blob storage.

    Use this to download files (PDFs, documents, etc.) that were previously
    uploaded to blob storage.

    Args:
        blob_id: Blob URI (format: blob://TIMESTAMP-HASH.EXT)

    Returns:
        Raw file bytes

    Raises:
        ToolError: If the blob is not found

    Example:
        data = get_file("blob://1733437200-b4e8d9c3a2f5e7b6.pdf")
    """
    data, _, _ = _get_blob_bytes(blob_id)
    return data


def upload_image_resource(
    data: bytes,
    filename: str,
    max_width: int | None = None,
    max_height: int | None = None,
    quality: int | None = None,
    ttl_hours: int | None = None,
) -> ResourceResponse:
    """
    Store raw image bytes in shared blob storage, optionally resizing, returning a resource identifier.

    This method enables other MCP servers to access the image file through a mapped
    docker volume. The image is stored in the shared storage location and a unique
    resource identifier is returned. Other services can use this identifier to directly
    access the file from the mapped volume.

    The image is automatically resized following the same rules as get_image().

    Args:
        data: Raw image bytes to store
        filename: Filename for the stored image (e.g., "photo.png")
        max_width: Maximum width in pixels. If omitted while max_height is specified,
                   width will be calculated to maintain aspect ratio. If both are omitted,
                   defaults to 1920. Set to 0 with max_height=0 to disable resizing.
        max_height: Maximum height in pixels. If omitted while max_width is specified,
                    height will be calculated to maintain aspect ratio. If both are omitted,
                    defaults to 1080. Set to 0 with max_width=0 to disable resizing.
        quality: JPEG compression quality (1-100). Default: 85. Only applies to JPEG
                 images; ignored for PNG/GIF/WebP.
        ttl_hours: Time-to-live in hours. Default: 24. After this time, the blob may
                   be cleaned up from storage.

    Returns:
        ResourceResponse with:
        - success: Whether the operation succeeded
        - resource_id: Unique identifier for the stored blob (format: blob://TIMESTAMP-HASH.EXT)
        - filename: Filename of the stored image (from metadata)
        - mime_type: MIME type of the stored image (from metadata)
        - size_bytes: Size of the stored image in bytes (from metadata)
        - sha256: SHA256 hash of the image data for deduplication (from upload result)
        - expires_at: ISO 8601 timestamp when the blob expires (from metadata)
        - error: Error message if unsuccessful

    Raises:
        ToolError: If the file is not an image, quality is invalid, or storage operation fails

    Example:
        # Store image with default settings
        with open("photo.png", "rb") as f:
            data = f.read()
        response = upload_image_resource(data, "photo.png")
        # ResourceResponse(success=True, resource_id="blob://1733437200-a3f9d8c2b1e4f6a7.png",
        #                  filename="photo.png", mime_type="image/png",
        #                  size_bytes=65536, sha256="a3f9d8c2...", expires_at="2024-12-07T12:00:00Z")

        # Store smaller thumbnail
        response = upload_image_resource(data, "photo.png", max_width=256, max_height=256)

        # Store with custom TTL
        response = upload_image_resource(data, "photo.png", ttl_hours=48)
    """
    try:
        _validate_quality(quality)

        if not data:
            raise ToolError("data is required and cannot be empty")
        if not filename:
            raise ToolError("filename is required")

        # Detect image format from the image data
        img = PILImage.open(io.BytesIO(data))
        image_format = img.format.lower() if img.format else "png"

        # Resize the image
        resized_data, _, _ = _resize_image(data, image_format, max_width, max_height, quality)

        # Store in blob storage
        storage = _get_blob_storage()
        result = storage.upload_blob(
            data=resized_data,
            filename=filename,
            tags=["resource-server", "image"],
            ttl_hours=ttl_hours,
        )

        # Get metadata to retrieve additional fields
        metadata = storage.get_metadata(result["blob_id"])

        return ResourceResponse(
            success=True,
            resource_id=result["blob_id"],
            filename=metadata["filename"],
            mime_type=metadata["mime_type"],
            size_bytes=metadata["size_bytes"],
            sha256=result["sha256"],
            expires_at=metadata["expires_at"],
        )

    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"Failed to create image resource: {e}")


def upload_file_resource(
    data: bytes,
    filename: str,
    ttl_hours: int | None = None,
) -> ResourceResponse:
    """
    Store raw file bytes in shared blob storage, returning a resource identifier.

    This method enables other MCP servers to access the file through a mapped docker
    volume. The file is stored in the shared storage location and a unique resource
    identifier is returned. Other services can use this identifier to directly access
    the file from the mapped volume.

    Args:
        data: Raw file bytes to store
        filename: Filename for the stored file (e.g., "document.pdf")
        ttl_hours: Time-to-live in hours. Default: 24. After this time, the blob may
                   be cleaned up from storage.

    Returns:
        ResourceResponse with:
        - success: Whether the operation succeeded
        - resource_id: Unique identifier for the stored blob (format: blob://TIMESTAMP-HASH.EXT)
        - filename: Filename of the stored file (from metadata)
        - mime_type: MIME type of the stored file (from metadata)
        - size_bytes: Size of the stored file in bytes (from metadata)
        - sha256: SHA256 hash of the file data for deduplication (from upload result)
        - expires_at: ISO 8601 timestamp when the blob expires (from metadata)
        - error: Error message if unsuccessful

    Raises:
        ToolError: If storage operation fails

    Example:
        # Store file with default settings
        with open("document.pdf", "rb") as f:
            data = f.read()
        response = upload_file_resource(data, "document.pdf")
        # ResourceResponse(success=True, resource_id="blob://1733437200-b4e8d9c3a2f5e7b6.pdf",
        #                  filename="document.pdf", mime_type="application/pdf",
        #                  size_bytes=524288, sha256="b4e8d9c3...", expires_at="2024-12-07T12:00:00Z")

        # Store with custom TTL
        response = upload_file_resource(data, "document.pdf", ttl_hours=72)
    """
    try:
        if not data:
            raise ToolError("data is required and cannot be empty")
        if not filename:
            raise ToolError("filename is required")

        # Store in blob storage
        storage = _get_blob_storage()
        result = storage.upload_blob(
            data=data,
            filename=filename,
            tags=["resource-server", "file"],
            ttl_hours=ttl_hours,
        )

        # Get metadata to retrieve additional fields
        metadata = storage.get_metadata(result["blob_id"])

        return ResourceResponse(
            success=True,
            resource_id=result["blob_id"],
            filename=metadata["filename"],
            mime_type=metadata["mime_type"],
            size_bytes=metadata["size_bytes"],
            sha256=result["sha256"],
            expires_at=metadata["expires_at"],
        )

    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"Failed to create file resource: {e}")


def get_file_info(blob_id: str) -> FileInfoResponse:
    """
    Get filesystem path and metadata for a blob file.

    This tool returns the filesystem path to the blob file along with its metadata,
    which is useful when you need to pass the file location to external tools or
    processes that need direct file access.

    Args:
        blob_id: Blob URI (format: blob://TIMESTAMP-HASH.EXT)

    Returns:
        FileInfoResponse with:
        - success: Whether the operation succeeded
        - blob_id: The blob URI that was queried
        - filename: Original filename
        - mime_type: MIME type of the file
        - size_bytes: File size in bytes
        - host_path: Path on the host filesystem (only included if HOST_BLOB_STORAGE_ROOT is set)
        - error: Error message if unsuccessful

    Raises:
        ToolError: If the blob_id is invalid or blob not found

    Example:
        # When running in Docker with HOST_BLOB_STORAGE_ROOT=/workspace/blob-storage
        info = get_file_info("blob://1733437200-a3f9d8c2b1e4f6a7.png")
        # FileInfoResponse(
        #     success=True,
        #     blob_id="blob://1733437200-a3f9d8c2b1e4f6a7.png",
        #     filename="photo.png",
        #     mime_type="image/png",
        #     size_bytes=65536,
        #     host_path="/workspace/blob-storage/a3/f9/1733437200-a3f9d8c2b1e4f6a7.png"
        # )

        # When running without Docker (HOST_BLOB_STORAGE_ROOT not set)
        info = get_file_info("blob://1733437200-a3f9d8c2b1e4f6a7.png")
        # FileInfoResponse(
        #     success=True,
        #     blob_id="blob://1733437200-a3f9d8c2b1e4f6a7.png",
        #     filename="photo.png",
        #     mime_type="image/png",
        #     size_bytes=65536
        # )
    """
    if not blob_id:
        raise ToolError("blob_id is required")

    try:
        # Get the container/process filesystem path
        container_path = blob_id_to_path(blob_id, BLOB_STORAGE_ROOT)

        # Verify the blob exists
        if not os.path.exists(container_path):
            raise ToolError(f"Blob file not found: {blob_id}")

        # Get metadata
        storage = _get_blob_storage()
        metadata = storage.get_metadata(blob_id)

        # Build response with conditional host_path
        response_data = {
            "success": True,
            "blob_id": blob_id,
            "filename": metadata.get("filename"),
            "mime_type": metadata.get("mime_type"),
            "size_bytes": metadata.get("size_bytes"),
        }

        # Only include host_path if configured
        if HOST_BLOB_STORAGE_ROOT:
            relative_path = os.path.relpath(container_path, BLOB_STORAGE_ROOT)
            host_path = os.path.join(HOST_BLOB_STORAGE_ROOT, relative_path)
            response_data["host_path"] = host_path

        return FileInfoResponse(**response_data)

    except InvalidBlobIdError as e:
        raise ToolError(f"Invalid blob:// URI format: {e}")
    except BlobNotFoundError as e:
        raise ToolError(f"Blob not found in storage: {e}")
    except ToolError:
        raise
    except Exception as e:
        raise ToolError(f"Failed to get file info: {e}")
