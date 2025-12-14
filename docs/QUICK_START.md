# Quick Start Guide

Get the MCP Resource Server running with Claude Desktop in 5 minutes.

## 1. Install Dependencies

```bash
cd /opt/src/mcp/mcp_resource_server
uv sync
```

## 2. Test the Server

```bash
uv run mcp-resource-server
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
      "command": "uv",
      "args": [
        "--directory",
        "/opt/src/mcp/mcp_resource_server",
        "run",
        "mcp-resource-server"
      ]
    }
  }
}
```

**Important**: Update the path `/opt/src/mcp/mcp_resource_server` to match your actual installation location.

## 4. Create Required Directories

```bash
# Create resources directory (where files are stored)
mkdir -p /mnt/resources

# Create blob storage directory (for shared files)
mkdir -p /mnt/blob-storage

# Make them accessible
chmod 755 /mnt/resources /mnt/blob-storage
```

## 5. Restart Claude Desktop

1. Fully quit Claude Desktop
2. Restart the application
3. The MCP Resource Server tools should now be available

## 6. Verify It Works

In Claude Desktop, try asking:

```
"Use get_image_info to check if there are any images in /mnt/resources"
```

If the server is working, Claude will attempt to use the tool.

## Available Tools

Once configured, Claude can use these 7 tools:

### Image Tools
- `get_image` - Download and resize images
- `get_image_info` - Get image metadata
- `get_image_size_estimate` - Estimate resize results
- `get_image_resource` - Store image in blob storage

### File Tools
- `get_file` - Download file bytes
- `get_file_url` - Get file URL
- `get_file_resource` - Store file in blob storage

## Common First Steps

### Add a test file

```bash
# Download a sample image
curl -o /mnt/resources/test.jpg https://picsum.photos/800/600

# Or copy an existing file
cp /path/to/your/image.jpg /mnt/resources/
```

### Test in Claude Desktop

```
"Show me the image 'test.jpg'"
"What are the dimensions of 'test.jpg'?"
"Create a 256x256 thumbnail of 'test.jpg'"
```

## Troubleshooting

### Can't find the tools?
- Check Claude Desktop logs: `/workspace/claude-desktop-logs/mcp-server-mcp-resource-server.log`
- Verify the server starts: `uv run mcp-resource-server`
- Ensure the path in config is correct

### File not found errors?
- Verify file exists: `ls -l /mnt/resources/your_file_id`
- Check permissions: `chmod 644 /mnt/resources/your_file_id`

### Permission denied?
```bash
sudo chown -R $USER:$USER /mnt/resources /mnt/blob-storage
chmod 755 /mnt/resources /mnt/blob-storage
```

## Next Steps

- Read [CLAUDE_DESKTOP_SETUP.md](./CLAUDE_DESKTOP_SETUP.md) for detailed configuration options
- Review [../README.md](../README.md) for tool documentation
- Check [../CLAUDE.md](../CLAUDE.md) for technical details

## Custom Configuration

To use a different resource location or API endpoint:

```json
{
  "mcpServers": {
    "mcp-resource-server": {
      "command": "uv",
      "args": [
        "--directory",
        "/opt/src/mcp/mcp_resource_server",
        "run",
        "mcp-resource-server"
      ],
      "env": {
        "RESOURCE_SERVER_URL_PATTERN": "file:///your/custom/path/{file_id}"
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
1. Logs: `/workspace/claude-desktop-logs/mcp-server-mcp-resource-server.log`
2. Test standalone: `uv run mcp-resource-server`
3. Full guide: [CLAUDE_DESKTOP_SETUP.md](./CLAUDE_DESKTOP_SETUP.md)
