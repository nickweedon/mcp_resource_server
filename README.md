# MCP Resource Server

A Model Context Protocol (MCP) server for blob storage operations using FastMCP. This server provides a two-phase architecture: ingestion (downloading external resources into blob storage) and retrieval (accessing files via blob:// URIs).

## Overview

MCP Resource Server provides 6 tools for blob storage operations:
- Blob retrieval using blob:// URIs (get_image, get_file, etc.)
- Blob upload from external sources (upload_image_resource, upload_file_resource)
- Image resizing and format conversion
- Resource metadata retrieval

## Features

- **Two-Phase Architecture**: Separate ingestion (upload) and retrieval (get) operations
- **Blob:// URI Abstraction**: All files accessed via blob:// URIs, decoupled from filesystem
- **Image Processing**: Automatic resizing with PIL, aspect ratio preservation
- **Blob Storage**: Shared volume integration for multi-service workflows
- **File Deduplication**: SHA256-based deduplication to save storage
- **TTL Management**: Automatic cleanup of expired files

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
# Upload Ingestion Configuration (used by upload_* tools)
RESOURCE_SERVER_URL_PATTERN=file:///mnt/resources/{file_id}

# MCP Server Configuration (defaults shown)
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

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RESOURCE_SERVER_URL_PATTERN` | `file:///mnt/resources/{file_id}` | URL pattern for upload ingestion (used by upload_* tools) |
| `RESOURCE_SERVER_MASK_ERRORS` | `false` | Hide internal error details from clients |
| `BLOB_STORAGE_ROOT` | `/mnt/blob-storage` | Path to shared storage directory |
| `BLOB_MAX_SIZE_MB` | `100` | Maximum file size in MB |
| `BLOB_TTL_HOURS` | `24` | Default time-to-live for blobs |

## Available Tools

### Blob Retrieval Operations (require blob:// URIs)

| Tool | Description |
|------|-------------|
| `get_file` | Retrieve raw file bytes from blob storage |
| `get_image` | Retrieve and resize images from blob storage |
| `get_image_info` | Get blob image metadata |
| `get_image_size_estimate` | Estimate resize dimensions (dry run) |

### Blob Upload Operations (download from external sources)

| Tool | Description |
|------|-------------|
| `upload_file_resource` | Download external file and store in blob storage → returns blob:// URI |
| `upload_image_resource` | Download external image, resize, and store in blob storage → returns blob:// URI |

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

### Two-Phase Workflow

#### Phase 1: Upload external resource to blob storage
```python
# Upload an external image to blob storage
response = upload_image_resource("img_12345")
blob_uri = response.resource_id  # "blob://1733437200-abc123.png"

# Upload a file to blob storage
response = upload_file_resource("document_456")
blob_uri = response.resource_id  # "blob://1733437200-def456.pdf"
```

#### Phase 2: Retrieve from blob storage

```python
# Get image with default sizing (max 1024px)
image = get_image("blob://1733437200-abc123.png")

# Get smaller thumbnail
image = get_image("blob://1733437200-abc123.png", max_width=256, max_height=256)

# Get original full-resolution image
image = get_image("blob://1733437200-abc123.png", max_width=0, max_height=0)

# Get image with high quality JPEG
image = get_image("blob://1733437200-abc123.jpg", quality=95)
```

### Get image metadata
```python
info = get_image_info("blob://1733437200-abc123.png")
# ImageInfoResponse(success=True, width=2048, height=1536,
#                   format='png', file_size_bytes=524288)
```

### Estimate resize dimensions
```python
estimate = get_image_size_estimate("blob://1733437200-abc123.jpg", max_width=512)
# ImageSizeEstimate(success=True, original_width=2048, original_height=1536,
#                   estimated_width=512, estimated_height=384,
#                   original_size_bytes=524288, estimated_size_bytes=65536,
#                   would_resize=True, format='jpeg', quality=85)
```

### Download a file
```python
data = get_file("blob://1733437200-def456.pdf")
# Returns raw bytes
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
