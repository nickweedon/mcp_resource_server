# MCP Resource Server

A Model Context Protocol (MCP) server for file and image operations with blob storage support using FastMCP. This server provides tools for downloading, resizing, and managing file resources with configurable source URLs.

## Overview

MCP Resource Server is a generic resource management server that provides 7 tools for:
- File downloads with configurable URL patterns
- Image resizing and format conversion
- Blob storage for sharing files between MCP servers
- Resource metadata retrieval

## Features

- **Configurable File Sources**: Support for HTTP, HTTPS, and file:// protocols
- **Image Processing**: Automatic resizing with PIL, aspect ratio preservation
- **Blob Storage**: Shared volume integration for multi-service workflows
- **File Deduplication**: SHA256-based deduplication to save storage
- **TTL Management**: Automatic cleanup of expired files
- **Local-First**: Defaults to local filesystem access

## Requirements

- Python 3.10+
- uv package manager
- Optional: Docker for containerized deployment

## Setup

### 1. Install dependencies
```bash
uv sync
```

### 2. Configure environment variables (optional)
The server works out-of-the-box with sensible defaults. To customize, create a `.env` file in the project root:
```bash
# File Source Configuration (default: file:///mnt/resources/{file_id})
RESOURCE_SERVER_URL_PATTERN=file:///mnt/resources/{file_id}

# MCP Server Configuration (defaults shown)
# RESOURCE_SERVER_DEBUG=true
# RESOURCE_SERVER_MASK_ERRORS=false

# Blob Storage Configuration (defaults shown)
# BLOB_STORAGE_ROOT=/mnt/blob-storage
# BLOB_MAX_SIZE_MB=100
# BLOB_TTL_HOURS=24
```

**Note**: All environment variables are optional and have sensible defaults.

### 3. Build and run with Docker
```bash
# Build the Docker image
docker-compose build

# Run the server
docker-compose up
```

## Configuration

### URL Pattern Examples

The `RESOURCE_SERVER_URL_PATTERN` environment variable controls where files are downloaded from. Use `{file_id}` as a placeholder:

```bash
# Local filesystem (default)
RESOURCE_SERVER_URL_PATTERN=file:///mnt/resources/{file_id}

# Custom API
RESOURCE_SERVER_URL_PATTERN=https://api.example.com/files/{file_id}

# S3-style URLs
RESOURCE_SERVER_URL_PATTERN=https://mybucket.s3.amazonaws.com/{file_id}

# Network share
RESOURCE_SERVER_URL_PATTERN=file:///mnt/network-storage/{file_id}
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RESOURCE_SERVER_URL_PATTERN` | `file:///mnt/resources/{file_id}` | URL pattern for file downloads |
| `RESOURCE_SERVER_DEBUG` | `true` | Enable timing/logging middleware |
| `RESOURCE_SERVER_MASK_ERRORS` | `false` | Hide internal error details from clients |
| `BLOB_STORAGE_ROOT` | `/mnt/blob-storage` | Path to shared storage directory |
| `BLOB_MAX_SIZE_MB` | `100` | Maximum file size in MB |
| `BLOB_TTL_HOURS` | `24` | Default time-to-live for blobs |

## Available Tools

### File Operations

| Tool | Description |
|------|-------------|
| `get_file` | Download raw file bytes |
| `get_file_url` | Get download URL without fetching |
| `upload_file_resource` | Store file in shared blob storage |

### Image Operations

| Tool | Description |
|------|-------------|
| `get_image` | Download and resize images for display |
| `get_image_info` | Get metadata (dimensions, format, size) |
| `get_image_size_estimate` | Estimate resize dimensions (dry run) |
| `upload_image_resource` | Store resized image in blob storage |

## Shared Blob Storage

The server provides resource-based file storage methods (`upload_image_resource` and `upload_file_resource`) that enable sharing files with other MCP servers through a mapped Docker volume.

### How It Works

1. Files are downloaded and stored in a shared blob storage directory
2. Each file gets a unique resource identifier (format: `blob://TIMESTAMP-HASH.EXT`)
3. Other MCP servers can access these files directly from the mapped volume
4. Files are automatically deduplicated using SHA256 hashing
5. Files expire after a configurable TTL (default: 24 hours)

### Docker Volume Setup

To enable resource sharing between MCP servers, mount a shared volume:

```yaml
# docker-compose.yml
services:
  mcp-resource-server:
    image: mcp-resource-server:latest
    volumes:
      - blob-storage:/mnt/blob-storage
    environment:
      - BLOB_STORAGE_ROOT=/mnt/blob-storage

  other-mcp-server:
    image: other-mcp:latest
    volumes:
      - blob-storage:/mnt/blob-storage

volumes:
  blob-storage:
```

### Usage Example

```python
# Store an image in shared storage
response = upload_image_resource("img_example")
# Returns: ResourceResponse(
#   success=True,
#   resource_id="blob://1733437200-a3f9d8c2b1e4f6a7.png",
#   filename="img_example.png",
#   mime_type="image/png",
#   size_bytes=65536,
#   sha256="a3f9d8c2...",
#   expires_at="2024-12-08T12:00:00Z"
# )

# Other MCP servers can now access the file at:
# /mnt/blob-storage/17/33/blob://1733437200-a3f9d8c2b1e4f6a7.png
```

## Usage Examples

### Download and resize an image
```python
# Get image with default sizing (max 1024px)
image = get_image("example_file_id")

# Get smaller thumbnail
image = get_image("example_file_id", max_width=256, max_height=256)

# Get original full-resolution image
image = get_image("example_file_id", max_width=0, max_height=0)

# Get image with high quality JPEG
image = get_image("example_file_id", quality=95)
```

### Get image metadata
```python
info = get_image_info("example_file_id")
# ImageInfoResponse(success=True, width=2048, height=1536,
#                   format='jpeg', file_size_bytes=524288)
```

### Estimate resize dimensions
```python
estimate = get_image_size_estimate("example_file_id", max_width=512)
# ImageSizeEstimate(success=True, original_width=2048, original_height=1536,
#                   estimated_width=512, estimated_height=384,
#                   original_size_bytes=524288, estimated_size_bytes=65536,
#                   would_resize=True, format='jpeg', quality=85)
```

### Download a file
```python
data = get_file("example_file_id")
# Returns raw bytes
```

### Get file URL
```python
response = get_file_url("example_file_id")
# FileUrlResponse(success=True, url="file:///mnt/resources/example_file_id")
```

## Docker Deployment

### Build the image
```bash
docker compose build
```

### Run the server
```bash
docker compose up
```

## Development

This project is designed to work with VS Code and the devcontainers plugin.

### Setup dev container
1. Open project in VS Code
2. Install the "Dev Containers" extension
3. Press `Ctrl+Shift+P` and select "Dev Containers: Reopen in Container"
4. The container will build and install all dependencies automatically

### Run tests
```bash
uv run pytest
```

## Important Notes

### File Protocols
- **HTTP/HTTPS**: Downloads via requests library
- **file://**: Reads from local filesystem (use absolute paths)

### Image Processing
- Images are resized to fit within specified dimensions while preserving aspect ratio
- Small images are never upscaled
- JPEG quality setting only affects JPEG images (ignored for PNG/GIF/WebP)
- RGBA images are converted to RGB when saving as JPEG

### Blob Storage
- Files are stored with two-level directory sharding for performance
- Deduplication saves storage by reusing identical files
- TTL-based cleanup removes expired files automatically
- Resource IDs are stable across duplicates (same SHA256 = same resource_id)

## Claude Desktop Integration

To use this MCP server with Claude Desktop:

- **Quick Start**: See [docs/QUICK_START.md](docs/QUICK_START.md) for a 5-minute setup guide
- **Full Setup Guide**: See [docs/CLAUDE_DESKTOP_SETUP.md](docs/CLAUDE_DESKTOP_SETUP.md) for detailed configuration, troubleshooting, and usage examples

## Related Resources

- [FastMCP Documentation](https://gofastmcp.com)
- [FastMCP GitHub](https://github.com/jlowin/fastmcp)
- [MCP Specification](https://modelcontextprotocol.io)
