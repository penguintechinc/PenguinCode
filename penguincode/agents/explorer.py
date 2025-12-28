"""Explorer agent - handles codebase navigation and exploration."""

import time

from .base import AgentConfig, AgentResult, BaseAgent, Permission


class ExplorerAgent(BaseAgent):
    """Agent for read-only codebase exploration."""

    def __init__(self, *args, **kwargs):
        """Initialize explorer agent with read-only permissions."""
        if "config" not in kwargs:
            kwargs["config"] = AgentConfig(
                name="explorer",
                model="llama3.2:3b",
                description="Codebase navigation, file reading, search",
                permissions=[Permission.READ, Permission.SEARCH],
                system_prompt=(
                    "You are an explorer agent responsible for navigating and understanding codebases.\n"
                    "You can read files, search code with grep/glob, and summarize findings.\n"
                    "You cannot modify files or execute commands.\n"
                    "Provide clear, concise summaries of what you find."
                ),
            )
        super().__init__(*args, **kwargs)

    async def run(self, task: str, **kwargs) -> AgentResult:
        """
        Explore codebase based on task.

        Args:
            task: Exploration task (e.g., "Find all Python files")
            **kwargs: Additional arguments

        Returns:
            AgentResult with exploration findings
        """
        start_time = time.time()
        tool_calls = []

        try:
            response = await self.chat(
                f"Please explore the codebase to complete this task:\n\n{task}\n\n"
                "Use grep and glob to search, and read files as needed. "
                "Provide a summary of your findings."
            )

            duration_ms = (time.time() - start_time) * 1000

            return AgentResult(
                agent_name=self.config.name,
                success=True,
                output=response,
                tool_calls=tool_calls,
                tokens_used=0,
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
