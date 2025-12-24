"""
MCP Resource Server - Main Entry Point

This module sets up the FastMCP server and registers all resource tools.
"""

import os
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.utilities.types import Image

from mcp_resource_server import resources

# =============================================================================
# Server Setup
# =============================================================================

# Error masking disabled by default, can be enabled for production
mask_errors = os.getenv("RESOURCE_SERVER_MASK_ERRORS", "false").lower() in ("true", "1", "yes")

mcp = FastMCP(
    name="MCP Resource Server",
    instructions="""
    MCP Resource Server provides blob storage operations for files and images.

    ## Tools

    ### Blob Retrieval (Read Operations)
    - **get_file**: Retrieve raw file bytes from blob storage
    - **get_image**: Retrieve and resize images from blob storage
    - **get_image_info**: Get blob image metadata
    - **get_image_size_estimate**: Estimate resize dimensions (dry run)

    ### Blob Upload (Write Operations)
    - **upload_file_resource**: Store raw file bytes in blob storage
    - **upload_image_resource**: Store image bytes in blob storage with optional resizing

    ## Workflow

    1. **Upload Phase**: Provide file bytes and filename → receive blob:// URI
    2. **Retrieval Phase**: Use blob:// URI → receive file data

    ## Configuration

    Blob storage settings (environment variables):
    - BLOB_STORAGE_ROOT: Storage directory (default: /mnt/blob-storage)
    - BLOB_MAX_SIZE_MB: Maximum file size (default: 100)
    - BLOB_TTL_HOURS: Default expiration time (default: 24)
    """,
    mask_error_details=mask_errors,
    on_duplicate_tools="error",
)


# =============================================================================
# File Tools
# =============================================================================


@mcp.tool()
def get_file(
    blob_id: Annotated[str, "Blob URI (blob://TIMESTAMP-HASH.EXT)"],
) -> bytes:
    """
    Retrieve raw file bytes from blob storage.

    Returns binary content from the specified blob.
    """
    return resources.get_file(blob_id)


@mcp.tool()
def upload_file_resource(
    data: Annotated[bytes, "Raw file bytes to store"],
    filename: Annotated[str, "Filename for the stored file (e.g., 'document.pdf')"],
    ttl_hours: Annotated[int | None, "Time-to-live in hours (default: 24)"] = None,
) -> resources.ResourceResponse:
    """
    Store file bytes in shared blob storage.

    Stores raw file bytes in mapped Docker volume for access by other MCP servers.
    Returns resource identifier with metadata.
    """
    return resources.upload_file_resource(data, filename, ttl_hours)


# =============================================================================
# Image Tools
# =============================================================================


@mcp.tool()
def get_image(
    blob_id: Annotated[str, "Blob URI (blob://TIMESTAMP-HASH.EXT)"],
    max_width: Annotated[int | None, "Max width in pixels (default: 1920 if both omitted, else calculated from aspect ratio)"] = None,
    max_height: Annotated[int | None, "Max height in pixels (default: 1080 if both omitted, else calculated from aspect ratio)"] = None,
    quality: Annotated[int | None, "JPEG quality 1-100 (default: 85)"] = None,
) -> Image:
    """
    Retrieve and resize image from blob storage.

    Images are automatically resized to fit within 1920x1080 pixels by default
    (when both dimensions omitted) while preserving aspect ratio. If only one
    dimension is specified, the other is calculated to maintain aspect ratio.
    Set both max_width=0 and max_height=0 to disable resizing.
    """
    return resources.get_image(blob_id, max_width, max_height, quality)


@mcp.tool()
def get_image_info(
    blob_id: Annotated[str, "Blob URI (blob://TIMESTAMP-HASH.EXT)"],
) -> resources.ImageInfoResponse:
    """
    Get blob image metadata.

    Returns dimensions, format, and file size for the specified blob image.
    """
    return resources.get_image_info(blob_id)


@mcp.tool()
def get_image_size_estimate(
    blob_id: Annotated[str, "Blob URI (blob://TIMESTAMP-HASH.EXT)"],
    max_width: Annotated[int | None, "Max width in pixels (default: 1920 if both omitted, else calculated from aspect ratio)"] = None,
    max_height: Annotated[int | None, "Max height in pixels (default: 1080 if both omitted, else calculated from aspect ratio)"] = None,
    quality: Annotated[int | None, "JPEG quality 1-100 (default: 85)"] = None,
) -> resources.ImageSizeEstimate:
    """
    Estimate dimensions after resize (dry run).

    Predicts what get_image would return without actually resizing. Use this
    to decide if resize parameters need adjustment before retrieving.
    """
    return resources.get_image_size_estimate(blob_id, max_width, max_height, quality)


@mcp.tool()
def upload_image_resource(
    data: Annotated[bytes, "Raw image bytes to store"],
    filename: Annotated[str, "Filename for the stored image (e.g., 'photo.png')"],
    max_width: Annotated[int | None, "Max width in pixels (default: 1920 if both omitted, else calculated from aspect ratio)"] = None,
    max_height: Annotated[int | None, "Max height in pixels (default: 1080 if both omitted, else calculated from aspect ratio)"] = None,
    quality: Annotated[int | None, "JPEG quality 1-100 (default: 85)"] = None,
    ttl_hours: Annotated[int | None, "Time-to-live in hours (default: 24)"] = None,
) -> resources.ResourceResponse:
    """
    Store image bytes in shared blob storage with optional resizing.

    Resizes to 1920x1080 by default (when both dimensions omitted). If only one
    dimension is specified, the other is calculated to maintain aspect ratio.
    Stores image bytes in mapped Docker volume and returns resource identifier
    for access by other MCP servers.
    """
    return resources.upload_image_resource(data, filename, max_width, max_height, quality, ttl_hours)


# =============================================================================
# Main Entry Point
# =============================================================================


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
