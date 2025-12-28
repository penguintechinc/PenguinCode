"""Base agent class with tool access and permissions."""

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


class BaseAgent(ABC):
    """Base agent with tool access and permission management."""

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

        # Message history
        self.messages: List[Message] = []

        # Add system prompt if provided
        if config.system_prompt:
            self.messages.append(Message(role="system", content=config.system_prompt))

    def _init_tools(self) -> None:
        """Initialize tools based on agent permissions."""
        self.tools: Dict[str, Any] = {}

        if Permission.READ in self.config.permissions:
            self.tools["read"] = ReadFileTool()

        if Permission.SEARCH in self.config.permissions:
            self.tools["grep"] = GrepTool()
            self.tools["glob"] = GlobTool()

        if Permission.BASH in self.config.permissions:
            self.tools["bash"] = BashTool(working_dir=self.working_dir)

        if Permission.WRITE in self.config.permissions:
            self.tools["write"] = WriteFileTool()
            self.tools["edit"] = EditFileTool()

    def has_permission(self, permission: Permission) -> bool:
        """
        Check if agent has a specific permission.

        Args:
            permission: Permission to check

        Returns:
            True if agent has permission
        """
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

    async def chat(self, user_message: str) -> str:
        """
        Send a message to the agent and get response.

        Args:
            user_message: User message

        Returns:
            Agent response text
        """
        # Add user message
        self.messages.append(Message(role="user", content=user_message))

        # Generate response
        full_response = ""
        async for chunk in self.client.chat(
            model=self.config.model,
            messages=self.messages,
            stream=True,
        ):
            if chunk.message and chunk.message.content:
                full_response += chunk.message.content

        # Add assistant response to history
        if full_response:
            self.messages.append(Message(role="assistant", content=full_response))

        return full_response

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
        """Reset the conversation history, keeping only system prompt."""
        system_messages = [msg for msg in self.messages if msg.role == "system"]
        self.messages = system_messages

    def get_conversation_history(self) -> List[Message]:
        """Get the conversation history."""
        return self.messages.copy()
