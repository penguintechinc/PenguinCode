"""Agent implementations for PenguinCode."""

from .base import AgentConfig, AgentResult, BaseAgent, Permission
from .executor import ExecutorAgent
from .explorer import ExplorerAgent

__all__ = [
    "BaseAgent",
    "AgentConfig",
    "AgentResult",
    "Permission",
    "ExecutorAgent",
    "ExplorerAgent",
]
