# Penguin Code

```
    ____                        _          ______          __
   / __ \___  ____  ____ ___  _(_)___     / ____/___  ____/ /__
  / /_/ / _ \/ __ \/ __ `/ / / / / __ \   / /   / __ \/ __  / _ \
 / ____/  __/ / / / /_/ / /_/ / / / / /  / /___/ /_/ / /_/ /  __/
/_/    \___/_/ /_/\__, /\__,_/_/_/ /_/   \____/\____/\__,_/\___/
                 /____/
```

**AI-powered coding assistant CLI and VS Code extension using Ollama**

[![CI](https://github.com/penguintechinc/penguin-code/workflows/CI/badge.svg)](https://github.com/penguintechinc/penguin-code/actions)
[![License](https://img.shields.io/badge/License-AGPL%203.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/downloads/)

*Penguin Tech Inc © 2025*

## Features

- 🤖 **Multi-Agent System** - Specialized agents for different coding tasks
- 🔍 **Multi-Engine Research** - 5 search engines with MCP protocol support
- 🧠 **Persistent Memory** - mem0 integration for context across sessions
- ⚡ **GPU Optimized** - Smart model switching for RTX 4060 Ti (8GB VRAM)
- 🐧 **Cross-Platform** - Works on Linux, macOS, and Windows

## Quick Start

```bash
# Install
pip install -e .
penguincode setup

# Pull models
ollama pull llama3.2:3b qwen2.5-coder:7b deepseek-coder:6.7b

# Run
penguincode chat
```

**VS Code Extension**: Download VSIX from [Releases](https://github.com/penguintechinc/penguin-code/releases)

## Documentation

- **[Usage Guide](docs/USAGE.md)** - Installation, configuration, and usage
- **[Workflows](docs/WORKFLOWS.md)** - GitHub Actions and release process
- **[Standards](docs/STANDARDS.md)** - Development standards
- **[Contributing](docs/CONTRIBUTING.md)** - How to contribute

## License

AGPL-3.0 - See [LICENSE](LICENSE) for details

**Support**: [support.penguintech.io](https://support.penguintech.io) | **Homepage**: [www.penguintech.io](https://www.penguintech.io)
