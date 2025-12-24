# Claude Desktop Setup Guide

This guide explains how to configure Claude Desktop to use the MCP Resource Server via Docker for file and image operations with blob storage support.

## Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Claude Project Setup](#claude-project-setup)
- [Troubleshooting](#troubleshooting)
- [Usage Examples](#usage-examples)

## Quick Start

1. Build the Docker image: `cd /opt/src/mcp/mcp_resource_server && docker-compose build`
2. Add configuration to Claude Desktop's `claude_desktop_config.json`
3. Create a Claude Desktop project with appropriate instructions
4. Restart Claude Desktop

## Installation

### Prerequisites

- Claude Desktop installed
- Docker and Docker Compose installed
- Access to file resources directory (default: `/mnt/resources`)
- Optional: Shared blob storage directory (default: `/mnt/blob-storage`)

### Build the Docker Image

```bash
cd /opt/src/mcp/mcp_resource_server
docker-compose build
```

### Test the Server

```bash
docker-compose up
```

If successful, you should see the server start without errors. Press `Ctrl+C` to stop.

## Configuration

### Claude Desktop Config File Location

The Claude Desktop configuration file is located at:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### Basic Configuration

Add the MCP Resource Server to the `mcpServers` section of your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mcp-resource-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "-v", "mcp-blob-storage:/mnt/blob-storage",
        "-v", "/path/to/your/resources:/mnt/resources:ro",
        "mcp-resource-server:latest"
      ]
    }
  }
}
```

**Important**: Replace `/path/to/your/resources` with the actual path to your resources directory.

### Advanced Configuration with Environment Variables

To customize the server behavior, add environment variables:

```json
{
  "mcpServers": {
    "mcp-resource-server": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "-v", "mcp-blob-storage:/mnt/blob-storage",
        "-v", "/path/to/your/resources:/mnt/resources:ro",
        "mcp-resource-server:latest"
      ],
      "env": {
        "RESOURCE_SERVER_DEBUG": "true",
        "RESOURCE_SERVER_MASK_ERRORS": "false",
        "BLOB_STORAGE_ROOT": "/mnt/blob-storage",
        "BLOB_MAX_SIZE_MB": "100",
        "BLOB_TTL_HOURS": "24"
      }
    }
  }
}
```

### Configuration Options

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `RESOURCE_SERVER_DEBUG` | `true` | Enable debug logging and timing information |
| `RESOURCE_SERVER_MASK_ERRORS` | `false` | Hide internal error details from Claude |
| `BLOB_STORAGE_ROOT` | `/mnt/blob-storage` | Directory for shared blob storage |
| `BLOB_MAX_SIZE_MB` | `100` | Maximum file size for blob storage |
| `BLOB_TTL_HOURS` | `24` | Time-to-live for stored blobs |

## Claude Project Setup

To get the most out of the MCP Resource Server, create a Claude Desktop Project with custom instructions.

### Creating the Project

1. Open Claude Desktop
2. Click "Projects" in the sidebar
3. Click "Create Project"
4. Name it (e.g., "Resource Manager" or "File Operations")
5. Add the custom instructions below

### Recommended Project Instructions

```markdown
# Resource Manager Project

You have access to the MCP Resource Server which provides tools for file and image operations.

## Available Tools

### Image Operations
- **get_image**: Download and resize images for display (default max 1024px)
- **get_image_info**: Get image metadata (dimensions, format, size)
- **get_image_size_estimate**: Estimate resize dimensions before downloading
- **upload_image_resource**: Store resized image in shared blob storage

### File Operations
- **get_file**: Download raw file bytes
- **get_file_url**: Get the download URL without fetching the file
- **upload_file_resource**: Store file in shared blob storage

## Usage Guidelines

1. **Image Display**: When displaying images, use `get_image` with appropriate sizing:
   - Thumbnails: `max_width=256, max_height=256`
   - Standard display: `max_width=1024, max_height=1024` (default)
   - Full resolution: `max_width=0, max_height=0`

2. **Metadata First**: Use `get_image_info` to check dimensions before downloading large images

3. **Size Estimation**: Use `get_image_size_estimate` to preview resize results

4. **Blob Storage**: Use `upload_image_resource` or `upload_file_resource` when:
   - Sharing files with other MCP servers
   - Caching processed files for reuse
   - Need a stable resource identifier

5. **Error Handling**: If a file_id fails, suggest checking:
   - File exists at the configured URL pattern
   - File permissions allow access
   - File format is supported (for image operations)

## File ID Format

Files are referenced by their `file_id`, which is substituted into the configured URL pattern:
- Pattern: `file:///mnt/resources/{file_id}`
- Example: file_id `image.jpg` → `file:///mnt/resources/image.jpg`

## Best Practices

- Always resize images for display to reduce bandwidth and improve performance
- Use `get_image_info` to understand image characteristics before processing
- Prefer `get_file_url` when you only need the URL, not the file content
- Store frequently accessed files in blob storage to avoid repeated downloads
```

### Adding Knowledge Base Files

You can also add files to the project's knowledge base:

1. In the project settings, click "Add files"
2. Add the following files from the MCP Resource Server repository:
   - `README.md` - Server overview and usage
   - `.env.example` - Configuration reference

## Troubleshooting

### Checking Logs

Claude Desktop logs are located at `/workspace/logs` (when using the devcontainer) or in your Claude Desktop application logs directory.

The MCP Resource Server logs specifically are in: `mcp-server-mcp-resource-server.log`

#### Viewing Logs from Docker Container

```bash
# Check recent logs from running container
docker logs mcp-resource-server

# Follow logs in real-time
docker logs -f mcp-resource-server
```

### Common Issues

#### Server Not Starting

**Symptoms**: Claude Desktop shows "MCP server failed to start" or tools are unavailable

**Solutions**:
1. Check the Docker image was built successfully:
   ```bash
   docker images | grep mcp-resource-server
   ```

2. Test the container directly:
   ```bash
   docker run --rm -it mcp-resource-server:latest
   ```

3. Check Docker logs for errors:
   ```bash
   docker logs mcp-resource-server
   ```

#### File Not Found Errors

**Symptoms**: `ToolError: Failed to download file` or 404 errors

**Solutions**:
1. Verify the file exists at the mapped path:
   ```bash
   # Check the volume mount
   docker run --rm -it -v /path/to/your/resources:/mnt/resources:ro \
     mcp-resource-server:latest ls -l /mnt/resources/your_file_id
   ```

2. Ensure the volume mount path in docker args matches your resources location

3. Test with a known-good file first

#### Image Processing Errors

**Symptoms**: `Failed to process image` or PIL errors

**Solutions**:
1. Verify the file is a valid image format (JPEG, PNG, GIF, WebP):
   ```bash
   file /path/to/your/image
   ```

2. Check the image isn't corrupted:
   ```bash
   docker run --rm -it -v /path/to/your/resources:/mnt/resources:ro \
     mcp-resource-server:latest uv run python -c \
     "from PIL import Image; Image.open('/mnt/resources/your_image').verify()"
   ```

3. Try getting image info first to diagnose issues:
   - Use `get_image_info` tool with the file_id

#### Blob Storage Issues

**Symptoms**: `Failed to store blob` or storage errors

**Solutions**:
1. Check blob storage volume exists:
   ```bash
   docker volume ls | grep mcp-blob-storage
   ```

2. Verify disk space is available:
   ```bash
   docker system df
   ```

3. Check the file size doesn't exceed `BLOB_MAX_SIZE_MB`

4. Inspect volume contents:
   ```bash
   docker run --rm -it -v mcp-blob-storage:/mnt/blob-storage \
     alpine ls -lah /mnt/blob-storage
   ```

### Permission Issues

If you encounter permission errors with mounted volumes:

```bash
# Make sure your resources directory is readable
chmod -R 755 /path/to/your/resources

# For blob storage (if using host path instead of volume)
mkdir -p /path/to/blob-storage
chmod 755 /path/to/blob-storage
```

### Restart Claude Desktop

After configuration changes:
1. Fully quit Claude Desktop (not just close the window)
2. Restart the application
3. Open your project
4. Verify the MCP server tools are available

## Usage Examples

Once configured, Claude can use these tools automatically. Here are example prompts:

### Image Operations

```
"Show me the image with file_id 'photo.jpg'"
→ Uses get_image to download and display

"What are the dimensions of 'landscape.png'?"
→ Uses get_image_info to get metadata

"Create a thumbnail of 'portrait.jpg' (256x256)"
→ Uses get_image with max_width=256, max_height=256

"Store 'diagram.png' in blob storage for sharing"
→ Uses upload_image_resource
```

### File Operations

```
"Download the file 'document.pdf'"
→ Uses get_file to retrieve bytes

"What's the URL for 'data.csv'?"
→ Uses get_file_url

"Store 'report.xlsx' in blob storage"
→ Uses upload_file_resource
```

### Advanced Usage

```
"Show me all images in /mnt/resources and create thumbnails"
→ Lists files, uses get_image for each with thumbnail sizing

"Compare the sizes of 'before.jpg' and 'after.jpg'"
→ Uses get_image_info for both, compares results

"Process 'large-image.jpg' and estimate the size if resized to 800px width"
→ Uses get_image_size_estimate
```

## Integration with Other MCP Servers

The blob storage feature allows sharing files with other MCP servers:

1. Configure all MCP servers to use the same `BLOB_STORAGE_ROOT` volume
2. Use `upload_image_resource` or `upload_file_resource` to store files
3. Share the returned `resource_id` (format: `blob://TIMESTAMP-HASH.EXT`)
4. Other servers can access the file directly from the blob storage volume

### Example Multi-Server Setup

```json
{
  "mcpServers": {
    "mcp-resource-server": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-v", "shared-blob-storage:/mnt/blob-storage",
        "-v", "/path/to/resources:/mnt/resources:ro",
        "mcp-resource-server:latest"
      ],
      "env": {
        "BLOB_STORAGE_ROOT": "/mnt/blob-storage"
      }
    },
    "other-mcp-server": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-v", "shared-blob-storage:/mnt/blob-storage",
        "other-server:latest"
      ],
      "env": {
        "BLOB_STORAGE_ROOT": "/mnt/blob-storage"
      }
    }
  }
}
```

## Support

For issues and questions:
- Check Docker container logs: `docker logs mcp-resource-server`
- Review configuration: `claude_desktop_config.json`
- Test server directly: `docker run --rm -it mcp-resource-server:latest`

## Related Documentation

- [MCP Resource Server README](../README.md)
- [FastMCP Documentation](https://gofastmcp.com)
- [Model Context Protocol](https://modelcontextprotocol.io)
