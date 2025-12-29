# Penguin Code Usage Guide

Complete guide to installing, configuring, and using Penguin Code.

## Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [CLI Usage](#cli-usage)
- [VS Code Extension](#vs-code-extension)
- [Search Engines](#search-engines)
- [Memory Layer](#memory-layer)
- [Agents](#agents)
- [Examples](#examples)
- [Logging](#logging)
- [Troubleshooting](#troubleshooting)

---

## Installation

### Prerequisites

**Required**:
- [Ollama](https://ollama.ai) - Local AI model runtime
- Python 3.12+ - For CLI tool
- 8GB+ VRAM recommended (optimized for RTX 4060 Ti)

**Optional**:
- Node.js 18+ - For VS Code extension development
- Docker - For containerized deployment

### Install CLI

```bash
# Clone repository
git clone https://github.com/penguintechinc/penguin-code.git
cd penguin-code

# Install with pip
pip install -e .

# Run setup wizard
penguincode setup
```

### Pull Ollama Models

**Recommended models for RTX 4060 Ti (8GB)**:

```bash
# Required models
ollama pull llama3.2:3b          # Research, orchestration (1.5GB)
ollama pull qwen2.5-coder:7b     # Code execution (4.7GB)
ollama pull deepseek-coder:6.7b  # Planning, debugging (3.8GB)

# Optional for memory features
ollama pull nomic-embed-text     # Embeddings (274MB)

# Optional additional models
ollama pull codellama:7b         # Code review (3.8GB)
ollama pull mistral:7b           # Documentation (4.1GB)
```

**Model selection by task**:
- **Chat/Research**: llama3.2:3b (fast, general purpose)
- **Code Generation**: qwen2.5-coder:7b (best code quality)
- **Planning**: deepseek-coder:6.7b (best architecture)
- **Review**: codellama:7b (code analysis)

### Install VS Code Extension

**Option 1: From Releases (Recommended)**

1. Download latest VSIX from [Releases](https://github.com/penguintechinc/penguin-code/releases)
2. In VS Code: **Extensions** → **···** → **Install from VSIX**
3. Select downloaded file
4. Restart VS Code

**Option 2: Build from Source**

```bash
cd vsix-extension
npm install
npm run compile
npx vsce package
code --install-extension penguin-code-*.vsix
```

---

## Configuration

### Config File Location

- **Linux/macOS**: `~/.config/penguincode/config.yaml` or `./config.yaml`
- **Windows**: `%APPDATA%\penguincode\config.yaml` or `.\config.yaml`

### Basic Configuration

```yaml
# Ollama connection
ollama:
  api_url: "http://localhost:11434"
  timeout: 120

# Model assignments
models:
  planning: "deepseek-coder:6.7b"
  orchestration: "llama3.2:3b"
  research: "llama3.2:3b"
  execution: "qwen2.5-coder:7b"

# Generation parameters
defaults:
  temperature: 0.7
  max_tokens: 4096
  context_window: 8192
```

### Research Configuration

```yaml
research:
  engine: "duckduckgo"  # Options: duckduckgo, google, sciraai, searxng, fireplexity
  use_mcp: true         # Use MCP protocol when available
  max_results: 5

  engines:
    duckduckgo:
      safesearch: "moderate"  # off, moderate, strict
      region: "wt-wt"         # Worldwide

    google:
      api_key: "${GOOGLE_API_KEY}"
      cx_id: "${GOOGLE_CX_ID}"

    sciraai:
      api_key: "${SCIRA_API_KEY}"
      endpoint: "https://api.scira.ai"

    searxng:
      url: "https://searx.be"
      categories: ["general"]

    fireplexity:
      firecrawl_api_key: "${FIRECRAWL_API_KEY}"
```

### Memory Configuration

```yaml
memory:
  enabled: true
  vector_store: "chroma"  # Options: chroma, qdrant, pgvector
  embedding_model: "nomic-embed-text"

  stores:
    chroma:
      path: "./.penguincode/memory"
      collection: "penguincode_memory"

    qdrant:
      url: "http://localhost:6333"
      collection: "penguincode_memory"

    pgvector:
      connection_string: "${PGVECTOR_URL}"
      table: "penguincode_memory"
```

### GPU Optimization

**RTX 4060 Ti (8GB) - Recommended Settings**:

```yaml
regulators:
  auto_detect: true
  gpu_type: "auto"
  vram_mb: 8192
  max_concurrent_requests: 2   # Prevent VRAM overflow
  max_models_loaded: 1         # One model at a time
  request_queue_size: 10
  min_request_interval_ms: 100
  cooldown_after_error_ms: 1000
```

**For larger GPUs (16GB+)**:

```yaml
regulators:
  vram_mb: 16384
  max_concurrent_requests: 4
  max_models_loaded: 2
```

### Environment Variables

Set API keys as environment variables:

```bash
# Linux/macOS
export GOOGLE_API_KEY="your-key-here"
export GOOGLE_CX_ID="your-cx-here"
export SCIRA_API_KEY="your-key-here"
export FIRECRAWL_API_KEY="your-key-here"
export PGVECTOR_URL="postgresql://localhost/penguincode"

# Windows PowerShell
$env:GOOGLE_API_KEY="your-key-here"
```

---

## CLI Usage

### Basic Commands

```bash
# Interactive chat
penguincode chat

# Run setup wizard
penguincode setup

# Show configuration
penguincode config show

# Start server mode (for VS Code extension)
penguincode serve --port 8420

# Get help
penguincode --help
```

### Chat Session

```bash
penguincode chat

# Example interaction:
> Search for best practices in Python async programming

# The ChatAgent will:
# 1. Delegate to Explorer agent for research
# 2. Inject relevant documentation context
# 3. Review agent output
# 4. Provide summarized response
```

### Debug Mode

```bash
# Enable verbose debug logging
penguincode chat --debug

# Debug output goes to /tmp/penguincode.log
```

### Documentation Commands

```bash
# In chat session:
> /docs status     # Show indexed documentation status
> /docs detect     # Re-detect project languages/libraries
> /docs index      # Index docs for all detected libraries
> /docs search     # Search indexed documentation
> /docs cleanup    # Remove expired/unused docs
```

See [DOCS_RAG.md](DOCS_RAG.md) for full documentation.

### Server Mode

Start server for VS Code extension:

```bash
# Default port
penguincode serve

# Custom port
penguincode serve --port 8421

# With verbose logging
penguincode serve --verbose
```

---

## VS Code Extension

### Features

- **Inline Suggestions** - AI-powered code completions
- **Chat Panel** - Interactive coding assistant
- **Code Actions** - Explain, fix, refactor selected code
- **Research** - Web search integrated into chat

### Configuration

In VS Code settings (`settings.json`):

```json
{
  "penguincode.server.url": "http://localhost:8420",
  "penguincode.server.autoStart": true,
  "penguincode.completions.enabled": true,
  "penguincode.chat.defaultModel": "qwen2.5-coder:7b"
}
```

### Keyboard Shortcuts

- `Ctrl+Shift+P` → "Penguin Code: Start Chat"
- `Ctrl+Shift+P` → "Penguin Code: Explain Code"
- `Ctrl+Shift+P` → "Penguin Code: Fix Code"
- `Ctrl+Shift+P` → "Penguin Code: Refactor Code"

---

## Search Engines

### Engine Comparison

| Engine | Setup | Speed | Quality | API Key | Safe Search |
|--------|-------|-------|---------|---------|-------------|
| **DuckDuckGo** | None | Fast | Good | No | Yes |
| **Google** | API Key | Fast | Excellent | Yes | Yes |
| **SciraAI** | API Key | Medium | Good | Yes | Yes |
| **SearXNG** | Self-host | Medium | Good | No | Yes |
| **Fireplexity** | Self-host | Slow | Excellent | No | Yes |

### DuckDuckGo (Default)

**Best for**: General research, privacy-focused

```yaml
research:
  engine: "duckduckgo"
  use_mcp: true
  engines:
    duckduckgo:
      safesearch: "moderate"
      region: "wt-wt"
```

**No setup required** - works out of the box.

### Google Custom Search

**Best for**: High-quality results, comprehensive coverage

```yaml
research:
  engine: "google"
  use_mcp: true
  engines:
    google:
      api_key: "${GOOGLE_API_KEY}"
      cx_id: "${GOOGLE_CX_ID}"
```

**Setup**:
1. Create [Google Cloud Project](https://console.cloud.google.com)
2. Enable Custom Search API
3. Create [Custom Search Engine](https://programmablesearchengine.google.com/)
4. Get API key and CX ID

### SciraAI

**Best for**: Academic/scientific research

```yaml
research:
  engine: "sciraai"
  engines:
    sciraai:
      api_key: "${SCIRA_API_KEY}"
      endpoint: "https://api.scira.ai"
```

**Setup**: Get API key from [SciraAI](https://scira.ai)

### SearXNG

**Best for**: Privacy, metasearch, self-hosted

```yaml
research:
  engine: "searxng"
  use_mcp: true
  engines:
    searxng:
      url: "https://searx.be"  # Or self-hosted
      categories: ["general"]
```

**Public instances**: [searx.be](https://searx.be), [searx.xyz](https://searx.xyz)

**Self-host**: See [SearXNG docs](https://docs.searxng.org/)

### MCP Protocol

**MCP-enabled engines**: DuckDuckGo, Google (limited), SearXNG

**Advantages**:
- Better context preservation
- Structured tool calling
- Enhanced error handling

**Setup**:
```bash
# DuckDuckGo MCP
npx -y @nickclyde/duckduckgo-mcp-server

# SearXNG MCP
uvx mcp-searxng
```

**Disable MCP** (use direct API):
```yaml
research:
  use_mcp: false
```

---

## Memory Layer

### How It Works

mem0 stores conversation context and learnings in a vector database for semantic search and retrieval.

**What gets stored**:
- User preferences
- Project-specific context
- Previous conversations
- Code patterns and decisions

### Vector Stores

**ChromaDB (Default)**:
```yaml
memory:
  vector_store: "chroma"
  stores:
    chroma:
      path: "./.penguincode/memory"
      collection: "penguincode_memory"
```

✅ No external services needed
✅ Simple file-based storage
❌ Single-machine only

**Qdrant**:
```yaml
memory:
  vector_store: "qdrant"
  stores:
    qdrant:
      url: "http://localhost:6333"
      collection: "penguincode_memory"
```

✅ High performance
✅ Scalable
❌ Requires Qdrant server

**PGVector**:
```yaml
memory:
  vector_store: "pgvector"
  stores:
    pgvector:
      connection_string: "${PGVECTOR_URL}"
      table: "penguincode_memory"
```

✅ Uses existing PostgreSQL
✅ ACID compliance
❌ Requires PostgreSQL with pgvector extension

### Programmatic Usage

```python
from penguincode.tools.memory import create_memory_manager
from penguincode.config.settings import load_settings

settings = load_settings("config.yaml")
manager = create_memory_manager(
    config=settings.memory,
    ollama_url=settings.ollama.api_url,
    llm_model=settings.models.research
)

# Add memory
await manager.add_memory(
    content="User prefers FastAPI over Flask",
    user_id="project_123",
    metadata={"category": "preferences", "topic": "frameworks"}
)

# Search memories
results = await manager.search_memories(
    query="web framework preferences",
    user_id="project_123",
    limit=5
)

# Get all memories
all_memories = await manager.get_all_memories("project_123")

# Delete memory
await manager.delete_memory(memory_id="mem_abc123")
```

---

## Agents

PenguinCode uses a ChatAgent orchestrator that delegates to specialized agents.

### Agent Roles

| Agent | Model | Purpose | When to Use |
|-------|-------|---------|-------------|
| **ChatAgent** | llama3.2:3b | Orchestration, knowledge base | Always (main interface) |
| **Explorer** | llama3.2:3b | Search, analyze code | Understanding codebase |
| **Executor** | qwen2.5-coder:7b | Write/modify code | Implementing features |
| **Planner** | deepseek-coder:6.7b | Break down complex tasks | Multi-step implementations |

### Resource-Smart Model Selection

Agents automatically select lite or full models based on task complexity:

| Complexity | Explorer | Executor |
|------------|----------|----------|
| Simple | llama3.2:1b | qwen2.5-coder:1.5b |
| Moderate/Complex | llama3.2:3b | qwen2.5-coder:7b |

### Agent Configuration

```yaml
models:
  orchestration: "llama3.2:3b"
  exploration: "llama3.2:3b"
  exploration_lite: "llama3.2:1b"
  execution: "qwen2.5-coder:7b"
  execution_lite: "qwen2.5-coder:1.5b"
  planning: "deepseek-coder:6.7b"

agents:
  max_concurrent: 5        # Max parallel agents
  timeout_seconds: 300     # Agent timeout
  max_rounds: 10          # Max supervision rounds
```

See [AGENTS.md](AGENTS.md) for detailed architecture documentation.

---

## Examples

### Example 1: Research and Summarize

```bash
penguincode chat
> Research Python async best practices and create a summary

# Agent flow:
# 1. Researcher searches DuckDuckGo
# 2. Fetches top 5 results
# 3. Analyzes content
# 4. Stores key findings in memory
# 5. Returns structured summary
```

### Example 2: Code Generation with Memory

```bash
> Generate a FastAPI endpoint for user registration

# Uses memory to recall:
# - You prefer FastAPI (from previous conversations)
# - Your code style preferences
# - Project-specific patterns
```

### Example 3: Multi-Engine Research

```yaml
# Try different engines for different needs
research:
  engine: "google"  # High-quality academic research

# Or
research:
  engine: "sciraai"  # Scientific papers

# Or
research:
  engine: "searxng"  # Privacy-focused general search
```

---

## Logging

PenguinCode uses Python's standard logging library. All logs go to `/tmp/penguincode.log`.

### Log Levels

| Level | Description | When Logged |
|-------|-------------|-------------|
| **ERROR** | Errors and exceptions | Always |
| **WARNING** | Unexpected behavior, timeouts | Always |
| **INFO** | Agent spawns, LLM requests/responses | Always |
| **DEBUG** | Full message content, tool args, output details | Only with `--debug` |

### Viewing Logs

```bash
# Watch logs in real-time
tail -f /tmp/penguincode.log

# Filter by level
grep "\[ERROR\]" /tmp/penguincode.log
grep "\[WARNING\]" /tmp/penguincode.log

# Clear logs
> /tmp/penguincode.log
```

### Debug Mode

Enable verbose debug logging with the `--debug` flag:

```bash
penguincode chat --debug
```

This adds detailed output including:
- Full message content sent to LLM
- Complete LLM response text
- Tool call arguments and results
- Agent task descriptions and outputs

### Example Log Output

```
2025-12-28 10:15:32 [INFO] penguincode: LLM REQUEST to model=llama3.2:3b
2025-12-28 10:15:35 [INFO] penguincode: LLM RESPONSE (523 chars)
2025-12-28 10:15:35 [INFO] penguincode:   Tool calls (1):
2025-12-28 10:15:35 [INFO] penguincode: AGENT SPAWN: executor (complexity=moderate)
2025-12-28 10:15:42 [INFO] penguincode: AGENT RESULT: executor - SUCCESS
```

---

## Troubleshooting

### Ollama Connection Issues

**Error**: `Connection refused to localhost:11434`

**Solution**:
```bash
# Check if Ollama is running
ollama list

# Start Ollama service (Linux)
systemctl start ollama

# Check connection
curl http://localhost:11434/api/tags
```

### VRAM Overflow

**Error**: `CUDA out of memory`

**Solution**:
```yaml
# Reduce concurrent requests
regulators:
  max_concurrent_requests: 1
  max_models_loaded: 1

# Use smaller models
models:
  execution: "llama3.2:3b"  # Instead of 7b
```

### Memory Issues

**Error**: `ChromaDB collection not found`

**Solution**:
```bash
# Reset memory
rm -rf .penguincode/memory

# Restart with fresh memory
penguincode chat
```

### Search Engine Failures

**DuckDuckGo rate limiting**:
```yaml
research:
  engine: "searxng"  # Use SearXNG as fallback
```

**Google API quota exceeded**:
```yaml
research:
  engine: "duckduckgo"  # Switch to DuckDuckGo
  use_mcp: true
```

### VS Code Extension Not Connecting

**Check server**:
```bash
# Verify server is running
curl http://localhost:8420/health

# Start server manually
penguincode serve
```

**Check VS Code settings**:
```json
{
  "penguincode.server.url": "http://localhost:8420",
  "penguincode.server.autoStart": true
}
```

---

## Performance Tips

### Model Loading

**Preload frequently used models**:
```bash
# Keep small models in VRAM
ollama run llama3.2:3b --keepalive 24h
```

### Memory Optimization

**Use smaller embeddings**:
```yaml
memory:
  embedding_model: "all-minilm:l6-v2"  # 80MB vs 274MB
```

### Search Optimization

**Reduce result count**:
```yaml
research:
  max_results: 3  # Faster processing
```

---

**Last Updated**: 2025-12-27
**See Also**: [WORKFLOWS.md](WORKFLOWS.md), [STANDARDS.md](STANDARDS.md)
