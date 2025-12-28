"""Executor agent - handles code mutations, file writes, and bash execution."""

from typing import Optional

from .base import AgentConfig, AgentResult, BaseAgent, Permission
from penguincode.ollama import OllamaClient


EXECUTOR_SYSTEM_PROMPT = """You are an Executor agent responsible for making code changes and running commands.

Your capabilities:
- Read files to understand current code
- Write new files or overwrite existing ones
- Edit files by finding and replacing specific text
- Search code with grep and glob
- Execute bash commands to run tests, install dependencies, or perform other tasks

When given a task:
1. First read and understand the relevant code (use read, grep, glob)
2. Plan your changes carefully
3. Make changes using write or edit
4. Verify your changes if needed (e.g., run tests with bash)
5. Summarize what you did

IMPORTANT:
- Always read a file before editing it to understand the current state
- Use edit for small, targeted changes (provides old_text and new_text)
- Use write for creating new files or completely rewriting existing ones
- Be careful with bash commands - explain what each command does
- When editing, make sure old_text matches EXACTLY (including whitespace)

Provide clear feedback about what was changed and any verification steps taken."""


class ExecutorAgent(BaseAgent):
    """Agent for code execution and file mutations."""

    def __init__(
        self,
        ollama_client: OllamaClient,
        working_dir: Optional[str] = None,
        model: str = "qwen2.5-coder:7b",
        config: Optional[AgentConfig] = None,
    ):
        """
        Initialize executor agent with full permissions.

        Args:
            ollama_client: Ollama client instance
            working_dir: Working directory for file operations
            model: Model to use (default: qwen2.5-coder:7b)
            config: Optional custom config
        """
        if config is None:
            config = AgentConfig(
                name="executor",
                model=model,
                description="Code mutations, file writes, bash execution",
                permissions=[
                    Permission.READ,
                    Permission.SEARCH,
                    Permission.BASH,
                    Permission.WRITE,
                ],
                system_prompt=EXECUTOR_SYSTEM_PROMPT,
                max_iterations=15,  # More iterations for complex tasks
            )

        super().__init__(
            config=config,
            ollama_client=ollama_client,
            working_dir=working_dir,
        )

    async def run(self, task: str, **kwargs) -> AgentResult:
        """
        Execute a code mutation or bash task using the agentic loop.

        Args:
            task: Task description (e.g., "Write a hello.py file")
            **kwargs: Additional arguments

        Returns:
            AgentResult with execution outcome
        """
        # Use the agentic loop from base class
        return await self.agentic_loop(task)
