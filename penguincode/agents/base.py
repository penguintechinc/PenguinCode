"""Base agent class with tool access, permissions, and agentic loop."""

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from penguincode.ollama import Message, OllamaClient
from penguincode.tools import (
    BashTool,
    EditFileTool,
    GlobTool,
    GrepTool,
    ReadFileTool,
    ToolResult,
    WriteFileTool,
)
from penguincode.ui import console


class Permission(Enum):
    """Agent permissions."""

    READ = "read"
    SEARCH = "search"  # Grep/Glob
    BASH = "bash"
    WRITE = "write"  # Write/Edit
    WEB = "web"  # Web search


@dataclass
class AgentConfig:
    """Configuration for an agent."""

    name: str
    model: str
    description: str
    permissions: List[Permission] = field(default_factory=list)
    system_prompt: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    max_iterations: int = 10  # Max tool calling iterations


@dataclass
class AgentResult:
    """Result from agent execution."""

    agent_name: str
    success: bool
    output: str
    error: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tokens_used: int = 0
    duration_ms: float = 0.0


# Ollama tool definitions
TOOL_DEFINITIONS = {
    "read": {
        "type": "function",
        "function": {
            "name": "read",
            "description": "Read the contents of a file. Returns the file content with line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The path to the file to read (absolute or relative to working directory)"
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "Optional start line number (1-indexed)"
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "Optional end line number (1-indexed, inclusive)"
                    }
                },
                "required": ["path"]
            }
        }
    },
    "write": {
        "type": "function",
        "function": {
            "name": "write",
            "description": "Write content to a file. Creates the file if it doesn't exist, overwrites if it does.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The path to the file to write"
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write to the file"
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    "edit": {
        "type": "function",
        "function": {
            "name": "edit",
            "description": "Edit a file by replacing specific text. The old_text must match exactly.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The path to the file to edit"
                    },
                    "old_text": {
                        "type": "string",
                        "description": "The exact text to find and replace"
                    },
                    "new_text": {
                        "type": "string",
                        "description": "The new text to replace with"
                    },
                    "replace_all": {
                        "type": "boolean",
                        "description": "Whether to replace all occurrences (default: false, only first)"
                    }
                },
                "required": ["path", "old_text", "new_text"]
            }
        }
    },
    "grep": {
        "type": "function",
        "function": {
            "name": "grep",
            "description": "Search for a pattern in files. Returns matching lines with file paths and line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "The search pattern (supports regex)"
                    },
                    "path": {
                        "type": "string",
                        "description": "The file or directory to search in (default: current directory)"
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "Whether search is case-sensitive (default: true)"
                    }
                },
                "required": ["pattern"]
            }
        }
    },
    "glob": {
        "type": "function",
        "function": {
            "name": "glob",
            "description": "Find files matching a glob pattern. Returns list of matching file paths.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "The glob pattern (e.g., '**/*.py' for all Python files)"
                    },
                    "path": {
                        "type": "string",
                        "description": "The base directory to search in (default: current directory)"
                    }
                },
                "required": ["pattern"]
            }
        }
    },
    "bash": {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Execute a bash command. Returns command output (stdout and stderr).",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The bash command to execute"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Optional timeout in seconds (default: 30)"
                    }
                },
                "required": ["command"]
            }
        }
    },
}


class BaseAgent(ABC):
    """Base agent with tool access, permission management, and agentic loop."""

    def __init__(
        self,
        config: AgentConfig,
        ollama_client: OllamaClient,
        working_dir: Optional[str] = None,
    ):
        """
        Initialize agent.

        Args:
            config: Agent configuration
            ollama_client: Ollama client instance
            working_dir: Working directory for file operations
        """
        self.config = config
        self.client = ollama_client
        self.working_dir = working_dir or "."

        # Initialize tools based on permissions
        self._init_tools()

        # Message history for the agent
        self.messages: List[Message] = []

    def _init_tools(self) -> None:
        """Initialize tools based on agent permissions."""
        self.tools: Dict[str, Any] = {}
        self.tool_definitions: List[Dict] = []

        if Permission.READ in self.config.permissions:
            self.tools["read"] = ReadFileTool()
            self.tool_definitions.append(TOOL_DEFINITIONS["read"])

        if Permission.SEARCH in self.config.permissions:
            self.tools["grep"] = GrepTool()
            self.tools["glob"] = GlobTool()
            self.tool_definitions.append(TOOL_DEFINITIONS["grep"])
            self.tool_definitions.append(TOOL_DEFINITIONS["glob"])

        if Permission.BASH in self.config.permissions:
            self.tools["bash"] = BashTool(working_dir=self.working_dir)
            self.tool_definitions.append(TOOL_DEFINITIONS["bash"])

        if Permission.WRITE in self.config.permissions:
            self.tools["write"] = WriteFileTool()
            self.tools["edit"] = EditFileTool()
            self.tool_definitions.append(TOOL_DEFINITIONS["write"])
            self.tool_definitions.append(TOOL_DEFINITIONS["edit"])

    def has_permission(self, permission: Permission) -> bool:
        """Check if agent has a specific permission."""
        return permission in self.config.permissions

    async def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """
        Execute a tool if agent has permission.

        Args:
            tool_name: Name of tool to execute
            **kwargs: Tool arguments

        Returns:
            ToolResult from tool execution
        """
        if tool_name not in self.tools:
            return ToolResult(
                success=False,
                data=None,
                error=f"Tool '{tool_name}' not available for this agent",
            )

        tool = self.tools[tool_name]
        return await tool.execute(**kwargs)

    def _parse_tool_calls(self, response_text: str) -> List[Dict]:
        """
        Try to parse tool calls from response text.

        Some models return tool calls as JSON in the response instead of
        using the structured tool_calls field.
        """
        tool_calls = []

        try:
            # Look for JSON blocks that might be tool calls
            if "{" in response_text and "}" in response_text:
                # Try to find JSON objects
                start = 0
                while True:
                    start = response_text.find("{", start)
                    if start == -1:
                        break

                    # Find matching closing brace
                    brace_count = 0
                    end = start
                    for i, char in enumerate(response_text[start:], start):
                        if char == "{":
                            brace_count += 1
                        elif char == "}":
                            brace_count -= 1
                            if brace_count == 0:
                                end = i + 1
                                break

                    if end > start:
                        try:
                            json_str = response_text[start:end]
                            data = json.loads(json_str)

                            # Check if this looks like a tool call
                            if "name" in data and ("arguments" in data or "parameters" in data):
                                tool_calls.append(data)
                            elif isinstance(data, dict) and any(
                                key in self.tools for key in data.keys()
                            ):
                                # Handle {tool_name: {args}}
                                for name, args in data.items():
                                    if name in self.tools:
                                        tool_calls.append({
                                            "name": name,
                                            "arguments": args if isinstance(args, dict) else {}
                                        })
                        except json.JSONDecodeError:
                            pass

                    start = end

        except Exception:
            pass

        return tool_calls

    async def _execute_tool_call(self, tool_call: Dict) -> str:
        """
        Execute a single tool call and return the result.

        Args:
            tool_call: Tool call dictionary with name and arguments

        Returns:
            String result of tool execution
        """
        # Extract tool name and arguments
        if isinstance(tool_call, dict):
            name = tool_call.get("name") or tool_call.get("function", {}).get("name")
            args = tool_call.get("arguments") or tool_call.get("function", {}).get("arguments", {})

            # Parse arguments if string
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
        else:
            # Handle object-style tool calls
            name = getattr(tool_call, "name", None)
            args = getattr(tool_call, "arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}

        if not name or name not in self.tools:
            return f"Error: Tool '{name}' not available"

        # Execute the tool
        console.print(f"  [dim]> {name}({', '.join(f'{k}={repr(v)[:50]}' for k, v in args.items())})[/dim]")

        try:
            result = await self.execute_tool(name, **args)

            if result.success:
                # Truncate very long outputs
                data_str = str(result.data)
                if len(data_str) > 3000:
                    data_str = data_str[:3000] + f"\n... (truncated, {len(data_str)} chars total)"
                return data_str
            else:
                return f"Error: {result.error}"

        except Exception as e:
            return f"Error executing {name}: {str(e)}"

    async def agentic_loop(self, task: str) -> AgentResult:
        """
        Run the agentic loop: LLM decides tools to call, we execute them,
        repeat until LLM provides final answer.

        Args:
            task: The task to complete

        Returns:
            AgentResult with the final output
        """
        start_time = time.time()
        tool_calls_log: List[Dict] = []

        # Build initial messages
        messages = []

        # System prompt
        system_prompt = self.config.system_prompt or self._default_system_prompt()
        system_prompt += f"\n\nWorking directory: {self.working_dir}"
        messages.append(Message(role="system", content=system_prompt))

        # Add the task
        messages.append(Message(role="user", content=task))

        iteration = 0
        final_response = ""

        while iteration < self.config.max_iterations:
            iteration += 1

            # Call the LLM with tools
            try:
                response_text = ""
                tool_calls = []

                async for chunk in self.client.chat(
                    model=self.config.model,
                    messages=messages,
                    tools=self.tool_definitions if self.tool_definitions else None,
                    stream=True,
                ):
                    if chunk.message and chunk.message.content:
                        response_text += chunk.message.content

                    # Check for tool calls in response metadata
                    # Note: Ollama may include tool_calls in the final chunk
                    if chunk.done and hasattr(chunk, "message"):
                        msg = chunk.message
                        if hasattr(msg, "tool_calls") and msg.tool_calls:
                            tool_calls.extend(msg.tool_calls)

                # If no structured tool calls, try parsing from response text
                if not tool_calls:
                    tool_calls = self._parse_tool_calls(response_text)

                # If we have tool calls, execute them
                if tool_calls:
                    # Add assistant message with the response
                    messages.append(Message(role="assistant", content=response_text or "Executing tools..."))

                    # Execute each tool call
                    tool_results = []
                    for tc in tool_calls:
                        result = await self._execute_tool_call(tc)
                        tool_calls_log.append({
                            "tool": tc.get("name") or tc.get("function", {}).get("name"),
                            "arguments": tc.get("arguments") or tc.get("function", {}).get("arguments", {}),
                            "result": result[:500] if len(result) > 500 else result
                        })
                        tool_results.append(result)

                    # Add tool results as a user message (tool response)
                    tool_response = "\n\n".join(
                        f"[Tool: {tc.get('name', 'unknown')}]\n{result}"
                        for tc, result in zip(tool_calls, tool_results)
                    )
                    messages.append(Message(role="user", content=f"Tool results:\n{tool_response}"))

                    continue

                # No tool calls - this is the final response
                final_response = response_text
                break

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                return AgentResult(
                    agent_name=self.config.name,
                    success=False,
                    output="",
                    error=f"LLM error: {str(e)}",
                    tool_calls=tool_calls_log,
                    duration_ms=duration_ms,
                )

        duration_ms = (time.time() - start_time) * 1000

        # Check if we hit max iterations without finishing
        if iteration >= self.config.max_iterations and not final_response:
            return AgentResult(
                agent_name=self.config.name,
                success=False,
                output="",
                error=f"Agent reached max iterations ({self.config.max_iterations}) without completing",
                tool_calls=tool_calls_log,
                duration_ms=duration_ms,
            )

        return AgentResult(
            agent_name=self.config.name,
            success=True,
            output=final_response,
            tool_calls=tool_calls_log,
            duration_ms=duration_ms,
        )

    def _default_system_prompt(self) -> str:
        """Return default system prompt for this agent type."""
        tools_available = ", ".join(self.tools.keys()) if self.tools else "none"
        return f"""You are a {self.config.name} agent. Your task is to help complete coding tasks.

Available tools: {tools_available}

When you need to use a tool, respond with a JSON object containing:
- "name": the tool name
- "arguments": an object with the tool arguments

Example:
{{"name": "read", "arguments": {{"path": "file.py"}}}}

After using tools and gathering information, provide a clear, helpful response summarizing what you found or did.
Do not use markdown code blocks around tool calls - just output the raw JSON.
When you're done and have the final answer, just respond normally without any JSON tool calls."""

    @abstractmethod
    async def run(self, task: str, **kwargs) -> AgentResult:
        """
        Run the agent on a specific task.

        Args:
            task: Task description
            **kwargs: Additional task-specific arguments

        Returns:
            AgentResult with execution outcome
        """
        pass

    def reset_conversation(self) -> None:
        """Reset the conversation history."""
        self.messages = []

    def get_conversation_history(self) -> List[Message]:
        """Get the conversation history."""
        return self.messages.copy()
