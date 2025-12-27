# Penguin Code

**Penguin Code** is an AI-powered coding assistant suite using Ollama as the backend.

## Components

| Component | Description |
|-----------|-------------|
| `penguincode` | CLI tool (this package) |
| `penguincode-vsix` | VS Code extension |

## penguincode CLI

Claude Code-like CLI using Ollama backend with agentic-first design.

### Installation

```bash
./scripts/install.sh
```

Or manually:

```bash
pip install -e .
penguincode setup
```

### Usage

```bash
penguincode chat    # Start interactive session
penguincode setup   # Run setup wizard
penguincode serve   # Start server mode (for penguincode-vsix)
```

### Server Mode

The CLI can run in server mode to provide a backend for the VS Code extension:

```bash
penguincode serve --port 8420
```

The `penguincode-vsix` extension connects to this server for all AI operations.

## License

AGPL-3.0 - Penguin Tech Inc
