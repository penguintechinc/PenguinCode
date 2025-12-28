# Documentation RAG System

Project-aware documentation retrieval for intelligent code assistance.

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Supported Languages](#supported-languages)
- [Configuration](#configuration)
- [REPL Commands](#repl-commands)
- [Architecture](#architecture)
- [Adding New Languages](#adding-new-languages)

---

## Overview

The Documentation RAG (Retrieval-Augmented Generation) system automatically detects your project's languages and libraries, fetches relevant documentation, and injects it into prompts for more accurate code assistance.

**Key Features**:
- **Project-aware** - Only indexes docs for languages/libraries you actually use
- **TTL-based caching** - Documentation expires after 7 days (configurable)
- **Automatic cleanup** - Removes docs for libraries no longer in your project
- **Token-aware** - Respects context limits when injecting documentation

---

## How It Works

### 1. Project Detection

On startup, PenguinCode scans your project for dependency files:

```
pyproject.toml  →  Python + libraries (pydantic, fastapi, etc.)
package.json    →  JavaScript/TypeScript + npm packages
go.mod          →  Go + modules
Cargo.toml      →  Rust + crates
*.tf / *.tofu   →  OpenTofu/Terraform + providers
ansible.cfg     →  Ansible + collections
```

### 2. Documentation Fetching

For detected libraries, docs are fetched from official sources:

```
FastAPI     →  https://fastapi.tiangolo.com/
React       →  https://react.dev/
AWS Provider →  https://registry.terraform.io/providers/hashicorp/aws/
community.docker →  https://docs.ansible.com/ansible/latest/collections/community/docker/
```

### 3. Indexing & Embedding

Documentation is:
1. Converted from HTML to markdown
2. Chunked into ~1000 character segments with overlap
3. Embedded using Ollama (nomic-embed-text)
4. Stored in ChromaDB for vector search

### 4. Context Injection

When you ask a question:
1. Query is analyzed for relevance
2. Matching documentation chunks are retrieved
3. Most relevant chunks are injected into the prompt
4. AI responds with documentation-informed answers

---

## Supported Languages

### Python

**Detection files**: `pyproject.toml`, `requirements.txt`, `setup.py`, `Pipfile`

**Supported libraries**:
- Web: FastAPI, Django, Flask, aiohttp
- Data: SQLAlchemy, Pydantic, Pandas, NumPy
- CLI: Typer, Click, Rich
- Testing: pytest
- AWS: boto3
- HTTP: requests, httpx
- Tasks: Celery, Redis

### JavaScript / TypeScript

**Detection files**: `package.json`, `tsconfig.json`

**Supported libraries**:
- Frameworks: React, Vue, Next.js, Express
- Utilities: Axios, Zod, Prisma
- Styling: Tailwind CSS
- Build: Vite, Vitest

### Go

**Detection files**: `go.mod`, `go.sum`

**Supported libraries**:
- Web: Gin, Echo, Fiber
- ORM: GORM

### Rust

**Detection files**: `Cargo.toml`

**Supported libraries**:
- Async: Tokio
- Serialization: Serde
- Web: Actix-web, Reqwest
- Database: Diesel

### OpenTofu / Terraform (HCL)

**Detection files**: `*.tf`, `*.tofu`, `.terraform.lock.hcl`

**Supported providers**:
- Cloud: AWS, Azure, Google Cloud, DigitalOcean, Cloudflare
- Containers: Kubernetes, Helm, Docker
- Utilities: Random, Null, Local, TLS

### Ansible

**Detection files**: `ansible.cfg`, `playbook.yml`, `site.yml`, `requirements.yml`, `galaxy.yml`

**Detection directories**: `roles/`, `inventory/`

**Supported collections**:
- Core: ansible.builtin, ansible.posix, ansible.netcommon
- Community: community.general, community.docker, community.kubernetes
- Cloud: amazon.aws, azure.azcollection, google.cloud
- Database: community.postgresql, community.mysql
- Containers: kubernetes.core

---

## Configuration

### config.yaml

```yaml
docs_rag:
  # Enable/disable the entire system
  enabled: true

  # Cache settings
  cache_dir: "./.penguincode/docs"
  cache_max_age_days: 7

  # Indexing limits
  max_pages_per_library: 50
  max_libraries_to_index: 20

  # Context injection
  max_context_tokens: 2000
  max_chunks_per_query: 5

  # Automatic behavior
  auto_detect_on_start: true
  auto_index_on_detect: false

  # ChromaDB collection name
  collection: "penguincode_docs"

  # Chunking parameters
  chunk_size: 1000
  chunk_overlap: 200
```

### Environment Variables

```bash
# Override cache directory
export PENGUINCODE_DOCS_CACHE="/path/to/docs/cache"
```

---

## REPL Commands

### `/docs status`

Show current documentation index status:

```
> /docs status

Documentation RAG Status
========================
Languages detected: python, hcl
Libraries indexed: 5

Library          Chunks  Indexed       Expires       Status
─────────────────────────────────────────────────────────────
fastapi          45      2025-12-28    2026-01-04    Valid
pydantic         32      2025-12-28    2026-01-04    Valid
aws              128     2025-12-27    2026-01-03    Valid
kubernetes       67      2025-12-25    2026-01-01    Expired
sqlalchemy       41      2025-12-28    2026-01-04    Valid

Total chunks: 313
Cache size: 2.4 MB
```

### `/docs detect`

Re-detect project languages and libraries:

```
> /docs detect

Scanning project...
Found: Python (pyproject.toml)
Found: HCL (main.tf, variables.tf)

Languages: python, hcl
Libraries: fastapi, pydantic, sqlalchemy, aws, kubernetes
```

### `/docs index [library]`

Index documentation for a specific library or all detected:

```
> /docs index fastapi
Fetching FastAPI documentation...
Indexed 45 chunks from 3 pages

> /docs index
Indexing all detected libraries...
fastapi: 45 chunks
pydantic: 32 chunks
sqlalchemy: 41 chunks
Done! Indexed 118 chunks
```

### `/docs search <query>`

Search indexed documentation:

```
> /docs search "FastAPI dependency injection"

Results:
─────────────────────────────────────────────────────
[fastapi] Dependency Injection (0.92)
FastAPI has a very powerful but intuitive Dependency Injection
system. It is designed to be very simple to use...

[fastapi] Dependencies with yield (0.85)
FastAPI supports dependencies that do some extra steps after
finishing. To do this, use yield instead of return...
```

### `/docs clear [library]`

Clear indexed documentation:

```
> /docs clear fastapi
Cleared 45 chunks for fastapi

> /docs clear
Cleared all documentation (313 chunks)
```

### `/docs cleanup`

Remove docs for libraries no longer in project:

```
> /docs cleanup
Removed docs for: old-library (23 chunks)
Removed expired docs: kubernetes (67 chunks)
Cleaned up 90 chunks total
```

---

## Architecture

### Components

```
docs_rag/
├── models.py      # Data models (Language, Library, DocChunk, etc.)
├── detector.py    # Project detection from dependency files
├── sources.py     # Documentation URL mappings
├── fetcher.py     # HTTP fetching with TTL cache
├── indexer.py     # ChromaDB vector storage
└── injector.py    # Context injection for prompts
```

### Data Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Detector   │────▶│   Fetcher   │────▶│   Indexer   │
│             │     │             │     │             │
│ Scans deps  │     │ Downloads   │     │ Chunks &    │
│ files       │     │ & caches    │     │ embeds      │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                                              ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  ChatAgent  │◀────│  Injector   │◀────│  ChromaDB   │
│             │     │             │     │             │
│ Augmented   │     │ Formats &   │     │ Vector      │
│ prompts     │     │ injects     │     │ search      │
└─────────────┘     └─────────────┘     └─────────────┘
```

### Storage Structure

```
.penguincode/
├── docs/                      # Documentation cache
│   ├── cache_index.json       # URL -> metadata mapping
│   ├── a1b2c3d4.md           # Cached doc content
│   └── ...
└── docs_index/               # ChromaDB vectors
    ├── index_metadata.json   # Library indexing metadata
    └── chroma.sqlite3        # Vector database
```

---

## Adding New Languages

### 1. Add to Language enum

```python
# docs_rag/models.py
class Language(Enum):
    PYTHON = "python"
    # ... existing
    NEW_LANG = "new_lang"
```

### 2. Add detection patterns

```python
# docs_rag/detector.py
LANGUAGE_INDICATORS: Dict[Language, List[str]] = {
    Language.NEW_LANG: ["*.newext", "newlang.config"],
}

DEPENDENCY_FILES: Dict[str, Language] = {
    "newlang.lock": Language.NEW_LANG,
}
```

### 3. Add file extension detection

```python
# docs_rag/detector.py (in _detect_languages_from_files)
extension_to_language = {
    ".newext": Language.NEW_LANG,
}
```

### 4. Add dependency parser

```python
# docs_rag/detector.py
def _parse_newlang_deps(self, content: str) -> List[Library]:
    """Parse newlang.lock for dependencies."""
    libraries = []
    # ... parsing logic
    return libraries
```

### 5. Add documentation sources

```python
# docs_rag/sources.py
LANGUAGE_DOCS: Dict[Language, DocSource] = {
    Language.NEW_LANG: DocSource(
        base_url="https://newlang.dev/docs/",
        api_docs_path="reference/",
    ),
}

LIBRARY_DOCS: Dict[str, DocSource] = {
    "popular-newlang-lib": DocSource(
        base_url="https://popular-lib.newlang.dev/",
    ),
}
```

---

## Troubleshooting

### Documentation not being indexed

**Check detection**:
```
> /docs detect
```

If your library isn't detected, ensure dependency files are in the project root.

### ChromaDB errors

**Reset the index**:
```bash
rm -rf .penguincode/docs_index
penguincode chat
```

### Embedding failures

**Check Ollama**:
```bash
ollama list | grep nomic-embed-text
# If missing:
ollama pull nomic-embed-text
```

### Cache taking too much space

**Clear old docs**:
```
> /docs cleanup
```

Or reduce cache age:
```yaml
docs_rag:
  cache_max_age_days: 3
```

---

**Last Updated**: 2025-12-28
**See Also**: [USAGE.md](USAGE.md), [AGENTS.md](AGENTS.md)
