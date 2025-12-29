# Ollama Tool/Function Calling Support

PenguinCode uses Ollama's tool calling capability to route requests to specialized agents. This document explains which models support native tool calling and how PenguinCode handles models that don't.

## How Tool Calling Works

When you make a request to PenguinCode, the ChatAgent (orchestrator) decides which specialized agent to use:
- **spawn_executor** - For code writing, file operations, bash commands
- **spawn_explorer** - For reading files, searching code, understanding codebase
- **spawn_researcher** - For web research, documentation lookup
- **spawn_planner** - For complex multi-step tasks

The ChatAgent can receive this routing decision in two ways:
1. **Native tool calls** - Ollama returns structured tool_calls in the response
2. **JSON text parsing** - Model outputs JSON like `{"name": "spawn_executor", ...}` in text

## Models with Native Tool Support

Ollama maintains a list of models supporting native tool calling:
https://ollama.com/search?c=tools

### Tested Working (Native Tools)

These models reliably return structured tool_calls:

| Model | Notes |
|-------|-------|
| `llama3.1` | 8B, 70B, 405B - Full tool support |
| `llama3.3` | Full tool support |
| `llama4` | Full tool support |
| `mistral` | All variants |
| `mistral-nemo` | Recommended for orchestration |
| `mistral-small` | Good balance of speed/capability |
| `mistral-large` | Best quality, slower |
| `mixtral` | MoE variant |
| `command-r` | Cohere's model |
| `command-r-plus` | Larger variant |
| `command-r7b` | Smaller variant |
| `firefunction-v2` | Specifically designed for function calling |
| `qwen3` | Works well with tools |
| `hermes3` | Fine-tuned for function calling |

### Important: Streaming Tool Calls

When using streaming responses, Ollama sends tool_calls in the **first chunk** with `done: false`, not in the final chunk. PenguinCode handles this correctly by checking for tool_calls in every chunk.

```python
# Ollama sends tool_calls early in streaming
{"message": {"tool_calls": [...]}, "done": false}  # Tool calls here!
{"message": {"content": ""}, "done": true}          # No tool_calls here
```

### Models Without Native Tool Support

These models return errors when tools are passed:

| Model | Behavior |
|-------|----------|
| `codellama` | Returns 400 error with tools |
| `deepseek-coder` | Not tested with tools |

For these models, PenguinCode falls back to JSON text parsing from the response.

## Configuration Recommendations

### For Best Tool Support (if you have 16GB+ VRAM)

```yaml
models:
  orchestration: "mistral-nemo"  # Native tool support
  execution: "qwen2.5-coder:7b"  # Best code quality
  exploration: "llama3.1:8b"     # Native tool support
  planning: "llama3.1:8b"        # Native tool support
```

### For 8GB VRAM (Current Default)

```yaml
models:
  orchestration: "llama3.2:3b"   # Fast, JSON text parsing
  execution: "qwen2.5-coder:7b"  # Best code quality
  exploration: "llama3.2:3b"     # Fast exploration
  planning: "deepseek-coder:6.7b"
```

### For Minimal VRAM (4GB)

```yaml
models:
  orchestration: "llama3.2:1b"
  execution: "qwen2.5-coder:1.5b"
  exploration: "llama3.2:1b"
  planning: "llama3.2:3b"
```

## How PenguinCode Handles This

The ChatAgent automatically detects whether a model supports native tools:

```python
# Models that work with native tool calls
native_tool_models = {
    "llama3.1", "llama3.3", "llama4",
    "mistral", "mistral-nemo", "mistral-small", "mistral-large", "mixtral",
    "command-r", "command-r-plus", "command-r7b",
    "firefunction-v2", "qwen3", "hermes3",
}
```

For models NOT in this list:
1. Tools are NOT passed to the API (avoids empty responses)
2. The system prompt instructs the model to output JSON tool calls
3. PenguinCode parses JSON from the text response
4. Falls back to intent detection from the user message if JSON parsing fails

## Troubleshooting

### Empty Responses

If you see `LLM RESPONSE (0 chars)` in logs:
- The model doesn't support native tools but is receiving them
- Solution: Check if model is in the `native_tool_models` list
- Or switch to a model that supports native tools

### Tool Calls Not Detected

If the agent isn't spawning correctly:
1. Check logs for the LLM response text
2. Verify the response contains valid JSON with `name` and `arguments`
3. Ensure the system prompt is being included

### Model Not Found (404)

If you see `404 Not Found` errors:
- The configured model isn't installed
- Run `ollama list` to see available models
- Run `ollama pull <model>` to install

## Adding Support for New Models

To test if a model supports native tools:

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "MODEL_NAME",
  "messages": [{"role": "user", "content": "Say hello"}],
  "tools": [{
    "type": "function",
    "function": {
      "name": "greet",
      "description": "Greet someone",
      "parameters": {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"]
      }
    }
  }]
}'
```

If response contains `"tool_calls"` with structured data, it supports native tools.
If response is empty or contains JSON text in `"content"`, use JSON parsing.

---

**See Also**:
- [Ollama Tools Models](https://ollama.com/search?c=tools)
- [Ollama Tool Support Blog](https://ollama.com/blog/tool-support)
- [USAGE.md](USAGE.md) for full configuration guide
