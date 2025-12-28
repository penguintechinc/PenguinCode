# Agent Architecture

PenguinCode uses a multi-agent system where a central ChatAgent orchestrates specialized agents to complete tasks.

## Table of Contents

- [Overview](#overview)
- [ChatAgent (Orchestrator)](#chatagent-orchestrator)
- [ExplorerAgent](#exploreragent)
- [ExecutorAgent](#executoragent)
- [PlannerAgent](#planneragent)
- [Agent Communication](#agent-communication)
- [Resource Management](#resource-management)
- [Configuration](#configuration)

---

## Overview

### Agent Hierarchy

```
┌─────────────────────────────────────────────────────────┐
│                      ChatAgent                          │
│                  (Knowledge Base + Foreman)             │
└─────────────────────────┬───────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
   │   Planner   │ │  Explorer   │ │  Executor   │
   │             │ │             │ │             │
   │ Breaks down │ │ Searches &  │ │ Writes &    │
   │ complex     │ │ analyzes    │ │ modifies    │
   │ tasks       │ │ code        │ │ code        │
   └─────────────┘ └─────────────┘ └─────────────┘
```

### Design Principles

1. **ChatAgent never does work directly** - Always delegates to specialized agents
2. **Foreman supervision** - Reviews agent outputs, dispatches follow-ups if needed
3. **Resource-smart** - Uses lite models for simple tasks, full models for complex
4. **Parallel execution** - Multiple agents can run concurrently (configurable max)

---

## ChatAgent (Orchestrator)

The ChatAgent serves two roles:

### Knowledge Base Role

Answers general questions directly without delegation:
- "What is a Python decorator?"
- "Explain async/await"
- "What's the difference between REST and GraphQL?"

### Foreman Role

For actionable requests, acts as job supervisor:

1. **Analyzes request** - Determines complexity and required agents
2. **Plans if needed** - Uses PlannerAgent for complex multi-step tasks
3. **Delegates work** - Dispatches to Explorer/Executor agents
4. **Reviews results** - Checks agent output for completeness
5. **Follows up** - Dispatches additional agents if work is incomplete

### Example Flow

```
User: "Add input validation to the login form"

ChatAgent:
├── Estimates complexity: "moderate"
├── Delegates to Explorer: "Find login form implementation"
├── Reviews Explorer output: Found src/components/LoginForm.tsx
├── Delegates to Executor: "Add validation using zod schema"
├── Reviews Executor output: Validation added
└── Returns summary to user
```

### Supervision Logic

```python
async def _review_and_supervise(self, request, agent_type, output, success, round):
    """
    Reviews agent work and decides next steps.

    Returns:
        "done" - Work complete, return to user
        "retry" - Same agent should try again
        "executor" - Hand off to executor
        "explorer" - Need more exploration
    """
```

---

## ExplorerAgent

**Purpose**: Search and analyze codebases without making changes

**Model**: `llama3.2:3b` (fast, good at comprehension) or `llama3.2:1b` (lite)

### Capabilities

- Search for files by pattern
- Read and analyze code
- Find function/class definitions
- Understand code structure
- Research external documentation

### Tools Available

```python
tools = [
    "glob",      # Find files by pattern
    "grep",      # Search file contents
    "read",      # Read file contents
    "ls",        # List directories
    "web_search" # Search documentation
]
```

### Example Tasks

```
"Find where user authentication is handled"
"What database models exist in this project?"
"How is the API router structured?"
"Search for usages of the UserService class"
```

---

## ExecutorAgent

**Purpose**: Make changes to code, create files, run commands

**Model**: `qwen2.5-coder:7b` (best code quality) or `qwen2.5-coder:1.5b` (lite)

### Capabilities

- Write new files
- Edit existing code
- Run shell commands
- Execute tests
- Apply refactoring

### Tools Available

```python
tools = [
    "read",     # Read before editing
    "write",    # Create new files
    "edit",     # Modify existing files
    "bash",     # Run commands
    "glob",     # Find files
    "grep"      # Search content
]
```

### Example Tasks

```
"Create a new API endpoint for user profiles"
"Fix the null pointer exception in PaymentService"
"Add unit tests for the validation module"
"Refactor the database queries to use async"
```

---

## PlannerAgent

**Purpose**: Break down complex tasks into structured, executable plans

**Model**: `deepseek-coder:6.7b` (best architecture reasoning)

### When Used

ChatAgent invokes PlannerAgent when:
- Task requires multiple steps
- Multiple files need changes
- Architectural decisions needed
- Task estimated as "complex"

### Plan Structure

```python
@dataclass
class PlanStep:
    step_num: int
    agent_type: str      # "explorer" or "executor"
    description: str
    depends_on: List[int]  # Step dependencies

@dataclass
class Plan:
    analysis: str              # Task breakdown
    steps: List[PlanStep]      # Ordered steps
    parallel_groups: List[List[int]]  # Steps that can run together
    complexity: str            # "simple", "moderate", "complex"
```

### Example Plan

```
Task: "Add user profile feature with avatar upload"

Analysis: This requires database changes, new API endpoints,
file storage integration, and frontend components.

Steps:
1. [explorer] Analyze existing user model and API structure
2. [executor] Add avatar_url field to User model
3. [executor] Create file upload endpoint
4. [executor] Add profile API endpoints
5. [explorer] Find frontend user components
6. [executor] Create ProfilePage component
7. [executor] Add avatar upload UI

Parallel Groups:
- [2, 3, 4] can run together (backend changes)
- [6, 7] can run together (frontend changes)
```

---

## Agent Communication

### Message Format

Agents communicate through structured prompts:

```python
{
    "role": "system",
    "content": """You are an Explorer agent for PenguinCode.
    Your task: {task_description}

    Available tools: glob, grep, read, ls

    Guidelines:
    - Search thoroughly before concluding
    - Report findings in structured format
    - Note any assumptions made
    """
}
```

### Result Format

Agents return structured results:

```python
{
    "success": True,
    "summary": "Found login form in src/components/LoginForm.tsx",
    "details": {
        "files_found": ["src/components/LoginForm.tsx"],
        "analysis": "Form uses useState for validation...",
        "recommendations": ["Consider using react-hook-form"]
    },
    "actions_taken": ["Read 3 files", "Searched for 'login'"]
}
```

---

## Resource Management

### Concurrency Control

```python
class AgentSemaphore:
    """Controls concurrent agent execution."""

    def __init__(self, max_concurrent: int = 5):
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def acquire(self):
        await self._semaphore.acquire()

    def release(self):
        self._semaphore.release()
```

### Model Selection

ChatAgent selects models based on task complexity:

```python
def _estimate_complexity(self, task: str) -> str:
    """Estimate task complexity for model selection."""

    # Simple patterns → lite models
    simple_patterns = [
        "what is", "explain", "find", "search",
        "list", "show", "where is"
    ]

    # Complex patterns → full models
    complex_patterns = [
        "refactor", "implement", "create feature",
        "redesign", "migrate", "optimize"
    ]

    # Returns: "simple", "moderate", or "complex"
```

### Model Mapping

| Complexity | Explorer Model | Executor Model |
|------------|---------------|----------------|
| Simple | llama3.2:1b | qwen2.5-coder:1.5b |
| Moderate | llama3.2:3b | qwen2.5-coder:7b |
| Complex | llama3.2:3b | qwen2.5-coder:7b |

---

## Configuration

### config.yaml

```yaml
# Agent model assignments
models:
  orchestration: "llama3.2:3b"
  exploration: "llama3.2:3b"
  exploration_lite: "llama3.2:1b"
  execution: "qwen2.5-coder:7b"
  execution_lite: "qwen2.5-coder:1.5b"
  planning: "deepseek-coder:6.7b"

# Concurrency settings
agents:
  max_concurrent: 5
  timeout_seconds: 300
  max_rounds: 10          # Max delegation rounds before giving up

# Parallel execution
parallel:
  enabled: true
  max_parallel_agents: 5
```

### Environment Overrides

```bash
# Override max concurrent agents
export PENGUINCODE_MAX_AGENTS=3

# Override agent timeout
export PENGUINCODE_AGENT_TIMEOUT=600
```

---

## Extending Agents

### Creating a Custom Agent

```python
from penguincode.agents.base import BaseAgent, AgentConfig

class CustomAgent(BaseAgent):
    """Custom agent for specialized tasks."""

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.tools = ["read", "write", "custom_tool"]

    async def execute(self, task: str, context: dict) -> AgentResult:
        """Execute the agent's task."""
        # Build prompt
        prompt = self._build_prompt(task, context)

        # Run agentic loop
        result = await self._run_loop(prompt)

        return AgentResult(
            success=result.success,
            summary=result.summary,
            details=result.details
        )
```

### Registering with ChatAgent

```python
# In ChatAgent.__init__
self.agents["custom"] = CustomAgent(
    config=AgentConfig(
        model=settings.models.custom,
        tools=["read", "write", "custom_tool"]
    )
)
```

---

**Last Updated**: 2025-12-28
**See Also**: [USAGE.md](USAGE.md), [DOCS_RAG.md](DOCS_RAG.md)
