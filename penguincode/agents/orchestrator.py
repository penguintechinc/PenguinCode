"""Orchestrator - delegates tasks to specialized agents."""

import json
import re
from typing import Dict, Optional

from penguincode.ollama import Message, OllamaClient
from penguincode.config.settings import Settings
from penguincode.ui import console


# Tool definitions for the orchestrator to decide which agent to spawn
ORCHESTRATOR_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "spawn_explorer",
            "description": "Spawn explorer agent to search and read files in the codebase. Use for: finding files, reading code, searching for patterns, understanding codebase structure, answering questions about code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "The exploration task to perform (e.g., 'find all Python files', 'read main.py', 'search for function foo')"
                    }
                },
                "required": ["task"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "spawn_executor",
            "description": "Spawn executor agent to make code changes, write files, or run bash commands. Use for: editing files, creating files, running tests, executing commands, fixing bugs, implementing features.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "The execution task to perform (e.g., 'create hello.py', 'fix the bug in auth.py', 'run pytest')"
                    }
                },
                "required": ["task"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "respond_directly",
            "description": "Respond directly to the user without spawning an agent. Use only for: answering general questions, explaining concepts, greeting, or when no code/file operations are needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "response": {
                        "type": "string",
                        "description": "The response to send to the user"
                    }
                },
                "required": ["response"]
            }
        }
    }
]

ORCHESTRATOR_SYSTEM_PROMPT = """You are PenguinCode, an AI coding assistant orchestrator. Your job is to understand user requests and delegate to the appropriate agent.

Available agents:
- Explorer: For reading files, searching code, finding patterns (read-only). Use this for ANY question about the codebase, finding code, or understanding what exists.
- Executor: For writing/editing files, running commands, making changes. Use this for any request to create, modify, or fix code.

Rules:
1. For questions about code or the codebase -> spawn_explorer
2. For requests to change/create/fix/write code -> spawn_executor
3. For running commands or tests -> spawn_executor
4. For general greetings or non-code questions -> respond_directly
5. When in doubt about code, use spawn_explorer first

You MUST call one of these functions for every request. Never just respond with text alone.
The task description should be clear and specific, including the user's full context.

Project directory: {project_dir}
"""


class Orchestrator:
    """Orchestrates task delegation to specialized agents."""

    def __init__(
        self,
        ollama_client: OllamaClient,
        settings: Settings,
        project_dir: str,
        agents: Dict,
    ):
        """
        Initialize orchestrator.

        Args:
            ollama_client: Ollama client for LLM calls
            settings: Application settings
            project_dir: Project directory path
            agents: Dictionary of available agents
        """
        self.client = ollama_client
        self.settings = settings
        self.project_dir = project_dir
        self.agents = agents
        self.conversation_history: list[Message] = []

    def _classify_request(self, user_message: str) -> tuple[str, str]:
        """
        Classify user request to determine which agent to use.

        Returns:
            Tuple of (agent_name, task_description)
        """
        msg_lower = user_message.lower().strip()

        # Patterns for executor (changes, commands)
        executor_patterns = [
            r"^(create|write|make|add|implement|build)\b",
            r"^(edit|modify|change|update|fix|patch|refactor)\b",
            r"^(run|execute|test|install|build|compile)\b",
            r"^(delete|remove|rename)\b",
            r"\b(create|write|make)\s+(a\s+)?(new\s+)?(file|script|program|function|class)\b",
            r"\b(fix|patch|update|change|modify|edit)\s+(the|this|my)?\s*(code|bug|error|file)\b",
            r"\brun\s+(the\s+)?(tests?|pytest|unittest)\b",
        ]

        for pattern in executor_patterns:
            if re.search(pattern, msg_lower):
                return "executor", user_message

        # Patterns for explorer (reading, searching)
        explorer_patterns = [
            r"^(find|search|look|locate|where|show)\b",
            r"^(read|display|print|cat|view)\b",
            r"^(what|which|how|why|explain|describe)\b",
            r"^(list|ls)\b",
            r"\b(find|search|look for|locate)\s+(the|a|any)?\s*(file|function|class|variable|code)\b",
            r"\bwhat\s+(is|are|does)\b",
            r"\bhow\s+(does|do|is|are|to)\b",
            r"\bshow\s+me\b",
            r"\bread\s+(the\s+)?(file|code)\b",
        ]

        for pattern in explorer_patterns:
            if re.search(pattern, msg_lower):
                return "explorer", user_message

        # Greetings and simple questions - respond directly
        greeting_patterns = [
            r"^(hi|hello|hey|greetings|good\s+(morning|afternoon|evening))[\s!.,]*$",
            r"^(thanks|thank\s+you|thx)[\s!.,]*$",
            r"^(bye|goodbye|exit|quit)[\s!.,]*$",
            r"^(who|what)\s+are\s+you\b",
            r"^help[\s!.,]*$",
        ]

        for pattern in greeting_patterns:
            if re.search(pattern, msg_lower):
                return "direct", user_message

        # Default: if it mentions files, code, or project - explore first
        code_words = ["file", "code", "function", "class", "method", "variable",
                      "import", "module", "package", "directory", "folder"]
        if any(word in msg_lower for word in code_words):
            return "explorer", user_message

        # For other requests, let the LLM decide
        return "llm_decide", user_message

    def _parse_tool_call_from_text(self, text: str) -> Optional[Dict]:
        """Parse tool call from text response."""
        try:
            # Look for JSON in the response
            if "{" in text and "}" in text:
                start = text.find("{")
                end = text.rfind("}") + 1
                json_str = text[start:end]
                data = json.loads(json_str)

                # Check if it's a tool call
                if "name" in data:
                    return data
                if "function" in data:
                    return data
        except (json.JSONDecodeError, KeyError):
            pass
        return None

    async def process(self, user_message: str) -> str:
        """
        Process a user message and delegate to appropriate agent.

        Args:
            user_message: The user's message

        Returns:
            Final response string
        """
        # First, try to classify the request heuristically
        classification, task = self._classify_request(user_message)

        if classification == "direct":
            # Handle direct responses for greetings
            response = self._handle_direct_response(user_message)
            self.conversation_history.append(Message(role="user", content=user_message))
            self.conversation_history.append(Message(role="assistant", content=response))
            return response

        if classification == "explorer":
            return await self._spawn_agent("explorer", task)

        if classification == "executor":
            return await self._spawn_agent("executor", task)

        # For ambiguous cases, use LLM to decide
        return await self._llm_orchestrate(user_message)

    def _handle_direct_response(self, user_message: str) -> str:
        """Handle direct responses for simple queries."""
        msg_lower = user_message.lower().strip()

        if any(g in msg_lower for g in ["hi", "hello", "hey", "greetings"]):
            return "Hello! I'm PenguinCode, your AI coding assistant. How can I help you with your project today?"

        if any(t in msg_lower for t in ["thanks", "thank you", "thx"]):
            return "You're welcome! Let me know if you need anything else."

        if "help" in msg_lower:
            return """I can help you with:
- **Exploring code**: "Find all Python files", "What does main.py do?", "Search for function X"
- **Making changes**: "Create a new file", "Fix the bug in X", "Add a function that does Y"
- **Running commands**: "Run the tests", "Install dependencies"

Just tell me what you'd like to do!"""

        if any(w in msg_lower for w in ["who are you", "what are you"]):
            return "I'm PenguinCode, an AI coding assistant powered by local LLMs through Ollama. I can help you explore, understand, and modify your codebase."

        return "I'm here to help with coding tasks. What would you like me to do?"

    async def _llm_orchestrate(self, user_message: str) -> str:
        """Use LLM to decide which agent to spawn."""
        # Build messages with system prompt
        messages = [
            Message(
                role="system",
                content=ORCHESTRATOR_SYSTEM_PROMPT.format(project_dir=self.project_dir),
            )
        ]

        # Add conversation history (last 4 messages for context)
        messages.extend(self.conversation_history[-4:])

        # Add current user message
        messages.append(Message(role="user", content=user_message))

        console.print("[dim]Thinking...[/dim]", end="\r")

        try:
            full_response = ""
            tool_calls = []

            async for chunk in self.client.chat(
                model=self.settings.models.orchestration,
                messages=messages,
                tools=ORCHESTRATOR_TOOLS,
                stream=True,
            ):
                if chunk.message:
                    if chunk.message.content:
                        full_response += chunk.message.content

                    # Check for tool calls in the message
                    if hasattr(chunk.message, 'tool_calls') and chunk.message.tool_calls:
                        tool_calls.extend(chunk.message.tool_calls)

            # Clear the "Thinking..." message
            console.print("              ", end="\r")

            # If there are tool calls, process them
            if tool_calls:
                return await self._handle_tool_calls(tool_calls, user_message)

            # Try to parse tool call from response content
            if full_response:
                tool_result = self._parse_tool_call_from_text(full_response)
                if tool_result:
                    return await self._handle_tool_calls([tool_result], user_message)

                # Check for specific patterns in response
                if "spawn_explorer" in full_response.lower():
                    return await self._spawn_agent("explorer", user_message)
                if "spawn_executor" in full_response.lower():
                    return await self._spawn_agent("executor", user_message)

            # If we got a text response without tool calls, return it
            if full_response:
                self.conversation_history.append(Message(role="user", content=user_message))
                self.conversation_history.append(Message(role="assistant", content=full_response))
                return full_response

            # Fallback: use explorer agent
            return await self._spawn_agent("explorer", user_message)

        except Exception as e:
            console.print("              ", end="\r")
            return f"Error: {str(e)}"

    async def _handle_tool_calls(self, tool_calls: list, user_message: str) -> str:
        """Handle tool calls from the orchestrator."""
        results = []

        for tool_call in tool_calls:
            # Extract function name and arguments
            if isinstance(tool_call, dict):
                func_name = tool_call.get("name") or tool_call.get("function", {}).get("name")
                args = tool_call.get("arguments") or tool_call.get("function", {}).get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {"task": args}
            else:
                # Handle object-style tool calls
                func_name = getattr(tool_call, "name", None) or getattr(getattr(tool_call, "function", None), "name", None)
                args = getattr(tool_call, "arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {"task": args}

            if not func_name:
                continue

            # Process the tool call
            if func_name == "spawn_explorer":
                task = args.get("task", user_message)
                result = await self._spawn_agent("explorer", task)
                results.append(result)

            elif func_name == "spawn_executor":
                task = args.get("task", user_message)
                result = await self._spawn_agent("executor", task)
                results.append(result)

            elif func_name == "respond_directly":
                response = args.get("response", "")
                results.append(response)

        # Combine results
        final_response = "\n\n".join(results) if results else "I couldn't process that request."

        # Update conversation history
        self.conversation_history.append(Message(role="user", content=user_message))
        self.conversation_history.append(Message(role="assistant", content=final_response))

        return final_response

    async def _spawn_agent(self, agent_name: str, task: str) -> str:
        """
        Spawn an agent to handle a task.

        Args:
            agent_name: Name of agent to spawn
            task: Task description

        Returns:
            Agent result as string
        """
        agent = self.agents.get(agent_name)
        if not agent:
            return f"Agent '{agent_name}' not available."

        console.print(f"[cyan]> Spawning {agent_name} agent...[/cyan]")

        try:
            result = await agent.run(task)

            # Update conversation history
            self.conversation_history.append(Message(role="user", content=task))
            self.conversation_history.append(Message(role="assistant", content=result.output if result.success else (result.error or "Unknown error")))

            if result.success:
                return result.output
            else:
                return f"Agent error: {result.error or 'Unknown error'}"

        except Exception as e:
            return f"Agent failed: {str(e)}"

    def reset_conversation(self) -> None:
        """Reset the conversation history."""
        self.conversation_history = []
