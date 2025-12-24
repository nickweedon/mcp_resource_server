# Quick Start Guide

Get the MCP Resource Server running with Claude Desktop using Docker in 5 minutes.

## 1. Build the Docker Image

```bash
cd /opt/src/mcp/mcp_resource_server
docker-compose build
```

## 2. Test the Server

```bash
docker-compose up
```

Press `Ctrl+C` to stop. If it starts without errors, you're ready to configure Claude Desktop.

## 3. Configure Claude Desktop

### Find your config file:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### Add this configuration:

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

## 4. Create Required Directories

The blob storage is handled automatically by Docker volumes, but you need to prepare your resources directory:

```bash
# Create resources directory (where files are stored)
mkdir -p /path/to/your/resources

# Make it accessible
chmod 755 /path/to/your/resources
```

## 5. Restart Claude Desktop

1. Fully quit Claude Desktop
2. Restart the application
3. The MCP Resource Server tools should now be available

## 6. Verify It Works

In Claude Desktop, try asking:

```
"Use get_image_info to check if there are any images in my resources"
```

If the server is working, Claude will attempt to use the tool.

## Available Tools

Once configured, Claude can use these 7 tools:

### Image Tools
- `get_image` - Download and resize images
- `get_image_info` - Get image metadata
- `get_image_size_estimate` - Estimate resize results
- `upload_image_resource` - Store image in blob storage

### File Tools
- `get_file` - Download file bytes
- `get_file_url` - Get file URL
- `upload_file_resource` - Store file in blob storage

## Common First Steps

### Add a test file

```bash
# Download a sample image
curl -o /path/to/your/resources/test.jpg https://picsum.photos/800/600

# Or copy an existing file
cp /path/to/your/image.jpg /path/to/your/resources/
```

### Test in Claude Desktop

```
"Show me the image 'test.jpg'"
"What are the dimensions of 'test.jpg'?"
"Create a 256x256 thumbnail of 'test.jpg'"
```

## Troubleshooting

### Can't find the tools?
- Check Docker logs: `docker logs mcp-resource-server`
- Verify the image was built: `docker images | grep mcp-resource-server`
- Test container directly: `docker run --rm -it mcp-resource-server:latest`

### File not found errors?
- Verify file exists: `ls -l /path/to/your/resources/your_file_id`
- Check volume mount path in docker args matches your resources location

### Permission denied?
```bash
chmod -R 755 /path/to/your/resources
```

## Next Steps

- Read [CLAUDE_DESKTOP_SETUP.md](./CLAUDE_DESKTOP_SETUP.md) for detailed configuration options
- Review [../README.md](../README.md) for tool documentation
- Check [../CLAUDE.md](../CLAUDE.md) for technical details

## Custom Configuration

To use environment variables or different resource location:

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
        "-v", "/your/custom/path:/mnt/resources:ro",
        "mcp-resource-server:latest"
      ],
      "env": {
        "BLOB_STORAGE_ROOT": "/mnt/blob-storage",
        "BLOB_MAX_SIZE_MB": "100",
        "BLOB_TTL_HOURS": "24"
      }
    }
  }
}
```

**URL Pattern Examples:**
- Local: `file:///mnt/resources/{file_id}`
- API: `https://api.example.com/files/{file_id}`
- S3: `https://bucket.s3.amazonaws.com/{file_id}`

## Support

Need help? Check:
1. Docker logs: `docker logs mcp-resource-server`
2. Test directly: `docker run --rm -it mcp-resource-server:latest`
3. Full guide: [CLAUDE_DESKTOP_SETUP.md](./CLAUDE_DESKTOP_SETUP.md)
