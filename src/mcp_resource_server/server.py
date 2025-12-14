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
    MCP Resource Server provides tools for file and image operations with blob storage support.

    ## Tools

    ### File Operations
    - **get_file**: Download raw file bytes
    - **get_file_url**: Get download URL without fetching
    - **get_file_resource**: Store file in shared blob storage

    ### Image Operations
    - **get_image**: Download and resize images for display
    - **get_image_info**: Get metadata (dimensions, format, size)
    - **get_image_size_estimate**: Estimate resize dimensions (dry run)
    - **get_image_resource**: Store resized image in blob storage

    ## Configuration

    Set RESOURCE_SERVER_URL_PATTERN to configure file source:
    - Default: file:///mnt/resources/{file_id}
    - Custom API: https://api.example.com/files/{file_id}
    - Network share: file:///mnt/network-storage/{file_id}

    ## Blob Storage

    Methods with _resource suffix store files in shared Docker volumes
    for inter-service communication. Files are deduplicated via SHA256
    and expire after configurable TTL.
    """,
    mask_error_details=mask_errors,
    on_duplicate_tools="error",
)


# =============================================================================
# File Tools
# =============================================================================


@mcp.tool()
def get_file(
    file_id: Annotated[str, "File identifier"],
) -> bytes:
    """
    Download raw file bytes.

    Returns binary content suitable for saving to disk or further processing.
    """
    return resources.get_file(file_id)


@mcp.tool()
def get_file_url(
    file_id: Annotated[str, "File identifier"],
) -> resources.FileUrlResponse:
    """
    Get download URL without fetching file.

    Returns the constructed URL based on RESOURCE_SERVER_URL_PATTERN.
    """
    return resources.get_file_url(file_id)


@mcp.tool()
def get_file_resource(
    file_id: Annotated[str, "File identifier"],
    ttl_hours: Annotated[int | None, "Time-to-live in hours (default: 24)"] = None,
) -> resources.ResourceResponse:
    """
    Store file in shared blob storage.

    Downloads file and stores in mapped Docker volume for access by other MCP servers.
    Returns resource identifier with metadata.
    """
    return resources.get_file_resource(file_id, ttl_hours)


# =============================================================================
# Image Tools
# =============================================================================


@mcp.tool()
def get_image(
    file_id: Annotated[str, "File identifier"],
    max_width: Annotated[int | None, "Max width in pixels (default: 1024, 0 to disable)"] = None,
    max_height: Annotated[int | None, "Max height in pixels (default: 1024, 0 to disable)"] = None,
    quality: Annotated[int | None, "JPEG quality 1-100 (default: 85)"] = None,
) -> Image:
    """
    Download and resize image for display.

    Images are automatically resized to fit within 1024x1024 pixels by default
    while preserving aspect ratio. Set both max_width=0 and max_height=0 to
    disable resizing.
    """
    return resources.get_image(file_id, max_width, max_height, quality)


@mcp.tool()
def get_image_info(
    file_id: Annotated[str, "File identifier"],
) -> resources.ImageInfoResponse:
    """
    Get image metadata without downloading.

    Returns dimensions, format, and file size. The image is cached briefly
    to optimize subsequent calls to get_image.
    """
    return resources.get_image_info(file_id)


@mcp.tool()
def get_image_size_estimate(
    file_id: Annotated[str, "File identifier"],
    max_width: Annotated[int | None, "Max width in pixels (default: 1024)"] = None,
    max_height: Annotated[int | None, "Max height in pixels (default: 1024)"] = None,
    quality: Annotated[int | None, "JPEG quality 1-100 (default: 85)"] = None,
) -> resources.ImageSizeEstimate:
    """
    Estimate dimensions after resize (dry run).

    Predicts what get_image would return without actually resizing. Use this
    to decide if resize parameters need adjustment before downloading.
    """
    return resources.get_image_size_estimate(file_id, max_width, max_height, quality)


@mcp.tool()
def get_image_resource(
    file_id: Annotated[str, "File identifier"],
    max_width: Annotated[int | None, "Max width in pixels (default: 1024)"] = None,
    max_height: Annotated[int | None, "Max height in pixels (default: 1024)"] = None,
    quality: Annotated[int | None, "JPEG quality 1-100 (default: 85)"] = None,
    ttl_hours: Annotated[int | None, "Time-to-live in hours (default: 24)"] = None,
) -> resources.ResourceResponse:
    """
    Store resized image in shared blob storage.

    Downloads, optionally resizes, and stores image in mapped Docker volume.
    Returns resource identifier for access by other MCP servers.
    """
    return resources.get_image_resource(file_id, max_width, max_height, quality, ttl_hours)


# =============================================================================
# Main Entry Point
# =============================================================================


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
