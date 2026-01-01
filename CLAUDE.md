# MCP Resource Server - Claude Context

This is an MCP (Model Context Protocol) server for blob storage operations. It provides a two-phase architecture: ingestion (storing file bytes into blob storage) and retrieval (accessing files from blob storage using blob:// URIs).

## Primary Use Case

This MCP Server will be used by Claude Desktop as part of a custom Claude Desktop "Project" that contains instructions to help guide its usage of this MCP server as well as other behavior.

## Debugging

The user's logs relating to usage of this MCP server can be found at /workspace/logs. More specifically the logs mcp-server-*resource*.log; you should ONLY look at these files in this directory as the other files will not contain any useful information.
You should consult these logs whenever a prompt refers to recent errors in Claude Desktop.

## Project Structure

Follow standard Python project conventions with a simple, focused architecture.

```
mcp_resource_server/
├── src/
│   └── mcp_resource_server/
│       ├── __init__.py         # Package initialization
│       ├── server.py           # Main MCP server entry point
│       └── resources.py        # All resource methods
├── tests/
│   └── ...                     # Test files
├── pyproject.toml              # Project configuration and dependencies
├── .env                        # Environment variables
├── README.md                   # User documentation
└── CLAUDE.md                   # This file - context for Claude
```

## Code Organization Guidelines

1. **Focused Architecture**: Single `resources.py` module contains all 7 resource tools
   - get_image, get_image_info, get_image_size_estimate
   - get_file, get_native_path
   - upload_image_resource, upload_file_resource

2. **Separation of Concerns**:
   - `resources.py` - Resource retrieval methods and blob storage
   - `server.py` - MCP server setup and tool registration

3. **Standard Python Conventions**:
   - Use `src/` layout for proper package isolation
   - Include `__init__.py` files in all packages
   - Follow PEP 8 naming conventions
   - Use type hints throughout
   - Keep modules focused and cohesive

## Design Documentation

### Core Features

1. **Two-Phase Architecture**:
   - Ingestion: Upload tools accept raw file bytes and store in blob storage
   - Retrieval: Get tools read from blob storage using blob:// URIs
2. **Image Processing**: Automatic resizing with PIL, format conversion, quality control
3. **Blob Storage**: Shared volume integration using mcp-mapped-resource-lib with blob:// URI abstraction

### Implementation Standards

- Always provide a 'returns' description in docstrings that fully describes the returned type
- Use strongly-typed return values (dataclasses)
- Provide appropriate examples in docstrings
- Use `ToolError` for client-facing errors

## Configuration

All configuration is done via environment variables. All variables are optional and have sensible defaults.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RESOURCE_SERVER_MASK_ERRORS` | `false` | Hide internal error details |
| `BLOB_STORAGE_ROOT` | `/mnt/blob-storage` | Shared storage path (container) |
| `HOST_BLOB_STORAGE_ROOT` | `""` | Host filesystem path (for Docker) |
| `BLOB_MAX_SIZE_MB` | `100` | Max file size |
| `BLOB_TTL_HOURS` | `24` | Blob expiration time |

## Blob Storage

The server uses `mcp-mapped-resource-lib` for shared file storage:

### Features
- **Deduplication**: Files with identical SHA256 hashes share storage
- **TTL Management**: Automatic cleanup of expired blobs
- **Two-Level Sharding**: Performance optimization for large file counts
- **Resource IDs**: Format `blob://TIMESTAMP-HASH.EXT`

### Usage Pattern
```python
# Store image in shared storage
storage = _get_blob_storage()
result = storage.upload_blob(
    data=image_bytes,
    filename="example.png",
    tags=["resource-server", "image", file_id],
    ttl_hours=24
)
# Returns: {"blob_id": str, "file_path": str, "sha256": str}

# Retrieve additional metadata
metadata = storage.get_metadata(result["blob_id"])
# metadata contains: filename, mime_type, size_bytes, expires_at, created_at, tags, etc.
```

## Error Handling

Use `ToolError` for client-facing errors in tool implementations:

```python
from fastmcp.exceptions import ToolError

def get_file(blob_id: str) -> bytes:
    if not blob_id:
        raise ToolError("blob_id is required")

    try:
        result = _get_blob_bytes(blob_id)
        return result
    except Exception as e:
        raise ToolError(f"Failed to read blob: {e}")
```

When `RESOURCE_SERVER_MASK_ERRORS=true`, only `ToolError` messages are exposed to clients.

## Testing

Test the server with:
```bash
uv run python -c "from mcp_resource_server import server; print('Server loads OK')"
```

Run full test suite:
```bash
uv run pytest
```

## Git Commit Guidelines

- Do NOT include "Generated with Claude Code" or similar AI attribution in commit messages
- Do NOT include "Co-Authored-By: Claude" or similar co-author tags
- Write commit messages as if authored solely by the developer

## Development Notes

- Uses FastMCP framework for MCP server implementation
- Uses `requests` library for HTTP downloads
- Uses `Pillow` for image processing
- Uses `mcp-mapped-resource-lib` for blob storage
- Environment variables loaded via `python-dotenv`
- Requires Python 3.10+

## Running the Server

```bash
uv sync
uv run mcp-resource-server
```

## Tools

This server exposes 7 MCP tools for blob storage operations:

### Blob Retrieval Tools (Read Operations - require blob:// URIs)
- **get_image**: Retrieve and resize images from blob storage
- **get_image_info**: Get blob image metadata (dimensions, format, size)
- **get_image_size_estimate**: Estimate resize outcome (dry run)
- **get_file**: Retrieve raw file bytes from blob storage
- **get_native_path**: Get native filesystem path to blob file (useful for Docker)

### Blob Upload Tools (Write Operations - store file bytes)
- **upload_image_resource**: Accept image bytes, optionally resize, store in blob storage → returns blob:// URI
- **upload_file_resource**: Accept file bytes, store in blob storage → returns blob:// URI

## Two-Phase Workflow

### Phase 1: Ingestion (File Bytes → Blob Storage)
Upload tools accept raw file bytes and filename:
```python
# Upload image bytes to blob storage
with open("photo.png", "rb") as f:
    data = f.read()
response = upload_image_resource(data, "photo.png")
blob_uri = response.resource_id  # "blob://1733437200-abc123.png"
```

### Phase 2: Retrieval (Blob Storage → Client)
Get tools accept ONLY blob:// URIs and read from shared storage:
```python
# Retrieve using blob URI
image = get_image(blob_uri)
info = get_image_info(blob_uri)
data = get_file(blob_uri)

# Get native filesystem path (useful for Docker or external tools)
path_info = get_native_path(blob_uri)
# path_info.native_path - primary path (host if configured, otherwise container)
# path_info.host_path - host filesystem path (if HOST_BLOB_STORAGE_ROOT is set)
# path_info.container_path - path inside container
```

## FastMCP Documentation

For detailed FastMCP implementation guidance, refer to:
- Official FastMCP documentation: https://gofastmcp.com
- FastMCP GitHub repository: https://github.com/jlowin/fastmcp
