# MCP (Model Context Protocol) Integration

PenguinCode supports MCP servers, allowing you to extend its capabilities with additional tools and integrations. MCP is an open protocol that enables AI assistants to interact with external services.

## What is MCP?

[Model Context Protocol](https://modelcontextprotocol.io/) is an open standard for connecting AI assistants to external data sources and tools. It allows:

- Adding custom tools to your AI assistant
- Connecting to external APIs and services
- Integrating with workflow automation platforms
- Extending functionality without modifying core code

## Supported Transport Types

PenguinCode supports two MCP transport types:

### 1. stdio (Standard I/O)

The server runs as a subprocess and communicates via stdin/stdout.

```yaml
mcp:
  servers:
    - name: "duckduckgo"
      transport: "stdio"
      command: "npx"
      args: ["-y", "@nickclyde/duckduckgo-mcp-server"]
```

**Use when:**
- Running official MCP server packages (npm, pip)
- Local development
- No persistent server needed

### 2. HTTP

Connects to an HTTP endpoint that implements the MCP protocol.

```yaml
mcp:
  servers:
    - name: "my-server"
      transport: "http"
      url: "http://localhost:8080"
      headers:
        Authorization: "Bearer ${API_TOKEN}"
```

**Use when:**
- Connecting to hosted services
- Authentication is required
- Server needs to persist across sessions

## Configuration

Add MCP servers in your `config.yaml`:

```yaml
mcp:
  enabled: true
  servers:
    - name: "server-name"        # Unique identifier
      enabled: true              # Toggle server on/off
      transport: "stdio"         # "stdio" or "http"

      # For stdio transport:
      command: "npx"             # Command to run
      args: ["-y", "package"]    # Command arguments
      env:                       # Environment variables
        API_KEY: "${MY_API_KEY}"
      startup_timeout: 10        # Seconds to wait for startup

      # For HTTP transport:
      url: "http://localhost:8080"
      headers:                   # HTTP headers
        Authorization: "Bearer ${TOKEN}"

      timeout: 30                # Request timeout (seconds)
```

## Example Configurations

### DuckDuckGo Search

```yaml
mcp:
  servers:
    - name: "duckduckgo"
      transport: "stdio"
      command: "npx"
      args: ["-y", "@nickclyde/duckduckgo-mcp-server"]
      timeout: 30
```

**Install:** Requires Node.js

### SearXNG Meta-Search

```yaml
mcp:
  servers:
    - name: "searxng"
      transport: "stdio"
      command: "uvx"
      args: ["mcp-searxng"]
      env:
        SEARXNG_URL: "https://searx.be"
      timeout: 30
```

**Install:** Requires Python and `uvx` (from `uv`)

### N8N Workflow Automation

[N8N](https://n8n.io/) is a workflow automation tool. When configured with MCP support:

```yaml
mcp:
  servers:
    - name: "n8n"
      transport: "http"
      url: "http://localhost:5678/mcp"
      headers:
        X-N8N-API-KEY: "${N8N_API_KEY}"
      timeout: 60
```

**Use cases:**
- Trigger automated workflows from PenguinCode
- Connect to external APIs through N8N nodes
- Execute complex multi-step automations

### Flowise AI

[Flowise](https://flowiseai.com/) is a visual AI workflow builder:

```yaml
mcp:
  servers:
    - name: "flowise"
      transport: "http"
      url: "http://localhost:3000/api/v1/mcp"
      headers:
        Authorization: "Bearer ${FLOWISE_API_KEY}"
      timeout: 60
```

**Use cases:**
- Call pre-built AI chains from PenguinCode
- Use specialized embedding or retrieval flows
- Integrate with LangChain-based tools

### Custom MCP Server

Build your own MCP server:

```yaml
mcp:
  servers:
    - name: "custom"
      transport: "http"
      url: "http://localhost:8000"
      headers:
        Authorization: "Bearer ${CUSTOM_API_KEY}"
        X-Custom-Header: "value"
      timeout: 30
```

## Environment Variables

All configuration values support environment variable substitution:

```yaml
mcp:
  servers:
    - name: "secure-server"
      url: "${MCP_SERVER_URL}"        # From environment
      headers:
        Authorization: "Bearer ${MCP_TOKEN}"
```

Set environment variables:

```bash
# Linux/macOS
export MCP_SERVER_URL="https://api.example.com/mcp"
export MCP_TOKEN="your-secret-token"

# Windows PowerShell
$env:MCP_SERVER_URL="https://api.example.com/mcp"
$env:MCP_TOKEN="your-secret-token"
```

## Authentication Methods

### Bearer Token (HTTP)

```yaml
headers:
  Authorization: "Bearer ${API_TOKEN}"
```

### API Key Header (HTTP)

```yaml
headers:
  X-API-Key: "${API_KEY}"
```

### Environment Variable (stdio)

```yaml
env:
  API_KEY: "${MY_API_KEY}"
  SECRET: "${MY_SECRET}"
```

### Basic Auth (HTTP)

```yaml
headers:
  Authorization: "Basic ${BASE64_CREDENTIALS}"
```

## Troubleshooting

### Server Not Starting (stdio)

1. Check command is installed: `which npx` or `which uvx`
2. Increase `startup_timeout` if server is slow to start
3. Check environment variables are set

### Connection Refused (HTTP)

1. Verify server is running: `curl http://localhost:8080/health`
2. Check URL and port configuration
3. Verify network/firewall settings

### Authentication Errors

1. Verify environment variables are set
2. Check token/API key is valid
3. Ensure headers are properly formatted

### Timeout Errors

1. Increase `timeout` value
2. Check server is responding
3. Verify network connectivity

## Building MCP Servers

To build your own MCP server:

1. **Python**: Use the `mcp` package
   ```bash
   pip install mcp
   ```

2. **JavaScript/TypeScript**: Use `@modelcontextprotocol/sdk`
   ```bash
   npm install @modelcontextprotocol/sdk
   ```

See the [MCP Documentation](https://modelcontextprotocol.io/docs) for implementation guides.

## Security Considerations

- **Never commit secrets**: Use environment variables for API keys
- **Use HTTPS**: For HTTP transport in production
- **Limit permissions**: Only grant MCP servers necessary access
- **Review server code**: Before running third-party MCP servers

---

**See Also:**
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [MCP Server Registry](https://github.com/modelcontextprotocol/servers)
- [USAGE.md](USAGE.md) for full configuration guide
