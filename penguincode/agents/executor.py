"""Executor agent - handles code mutations, file writes, and bash execution."""

import time
from typing import Optional

from .base import AgentConfig, AgentResult, BaseAgent, Permission


class ExecutorAgent(BaseAgent):
    """Agent for code execution and file mutations."""

    def __init__(self, *args, **kwargs):
        """Initialize executor agent with full permissions."""
        if "config" not in kwargs:
            kwargs["config"] = AgentConfig(
                name="executor",
                model="qwen2.5-coder:7b",
                description="Code mutations, file writes, bash execution",
                permissions=[
                    Permission.READ,
                    Permission.SEARCH,
                    Permission.BASH,
                    Permission.WRITE,
                ],
                system_prompt=(
                    "You are an executor agent responsible for making code changes and running commands.\n"
                    "You can read files, write files, edit files, search code, and execute bash commands.\n"
                    "Always verify your changes and provide clear feedback about what was done.\n"
                    "When executing bash commands, explain what the command does and its expected outcome."
                ),
            )
        super().__init__(*args, **kwargs)

    async def run(self, task: str, **kwargs) -> AgentResult:
        """
        Execute a code mutation or bash task.

        Args:
            task: Task description (e.g., "Write a hello.py file")
            **kwargs: Additional arguments

        Returns:
            AgentResult with execution outcome
        """
        start_time = time.time()
        tool_calls = []

        try:
            # Chat with agent about the task
            response = await self.chat(
                f"Please complete the following task:\n\n{task}\n\n"
                "Explain what you're doing and use the available tools to complete the task."
            )

            # Parse response for tool calls (simplified - in real implementation,
            # this would parse structured tool calls from the LLM)
            # For now, just return the response
            duration_ms = (time.time() - start_time) * 1000

            return AgentResult(
                agent_name=self.config.name,
                success=True,
                output=response,
                tool_calls=tool_calls,
                tokens_used=0,  # TODO: Track from ollama response
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return AgentResult(
                agent_name=self.config.name,
                success=False,
                output="",
                error=str(e),
                tool_calls=tool_calls,
                duration_ms=duration_ms,
            )
