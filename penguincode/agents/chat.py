"""Chat agent - the main orchestrating agent for PenguinCode.

This is the primary agent that users interact with. It serves two roles:

1. **Knowledge Base** - Answers general questions directly without spawning agents
2. **Foreman** - Delegates work to specialized agents, reviews their output,
   and can dispatch follow-up agents to fix issues if needed

For complex tasks, it uses the PlannerAgent to break down work and can
execute multiple agents in parallel (up to max_concurrent_agents).
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Tuple

from penguincode.ollama import Message, OllamaClient
from penguincode.config.settings import Settings
from penguincode.ui import console


CHAT_SYSTEM_PROMPT = """You are PenguinCode, an AI coding assistant.

You have two roles:

## Role 1: Knowledge Base
For general questions, greetings, or explaining concepts - respond directly without spawning agents.

## Role 2: Foreman (Job Supervisor)
For any code or file operations, you delegate to specialized agents and supervise their work.

**Available agents:**
- **spawn_explorer** - For reading, searching, or understanding code
- **spawn_executor** - For writing, editing, or running code
- **spawn_planner** - For complex tasks that need a structured plan first

**When to use the planner:**
Use spawn_planner when the request involves:
- Multiple files or components
- Multi-step implementations
- Refactoring across the codebase
- Features that require design decisions
- Tasks you estimate would take more than 2-3 simple steps

As foreman, you:
1. Assess task complexity - simple tasks go direct to explorer/executor
2. Complex tasks go to planner first for a structured approach
3. Review agent work and spawn follow-ups if needed
4. Provide a final summary to the user

**Rules:**
- NEVER read, write, or search files yourself - always delegate
- For questions about code -> spawn_explorer
- For requests to change/create/run code -> spawn_executor
- For complex multi-step tasks -> spawn_planner first
- For greetings or general questions -> respond directly

Project directory: {project_dir}
"""

REVIEW_PROMPT = """You are reviewing work done by a specialized agent.

Original user request: {user_request}

Agent type: {agent_type}
Agent output:
---
{agent_output}
---

As the foreman, evaluate this work:

1. Did the agent complete the task successfully?
2. Are there any errors or issues that need fixing?
3. Is any follow-up work needed?

Respond with one of:
- If work is complete and good: Summarize the results for the user
- If work has issues: Call spawn_executor or spawn_explorer to fix the problem
- If more exploration is needed: Call spawn_explorer for additional information

Be concise but thorough in your assessment.
"""

# Tool definitions for spawning agents
AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "spawn_explorer",
            "description": "Delegate to explorer agent for reading files, searching code, or understanding the codebase.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "Detailed task for the explorer"
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
            "description": "Delegate to executor agent for creating files, editing code, or running commands.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "Detailed task for the executor"
                    }
                },
                "required": ["task"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "spawn_planner",
            "description": "Delegate to planner agent to break down a complex task into steps. Use for multi-step tasks, refactoring, or features requiring design.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "The complex task to plan"
                    }
                },
                "required": ["task"]
            }
        }
    },
]


class AgentSemaphore:
    """Dynamic semaphore for controlling concurrent agent execution."""

    def __init__(self, max_concurrent: int = 5):
        self._max = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active_count = 0
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Acquire a slot for agent execution."""
        await self._semaphore.acquire()
        async with self._lock:
            self._active_count += 1

    def release(self):
        """Release a slot after agent completion."""
        self._semaphore.release()
        asyncio.create_task(self._decrement_count())

    async def _decrement_count(self):
        async with self._lock:
            self._active_count -= 1

    @property
    def active_agents(self) -> int:
        return self._active_count

    @property
    def available_slots(self) -> int:
        return self._max - self._active_count

    def adjust_max(self, new_max: int):
        """Dynamically adjust max concurrent agents (for resource regulation)."""
        # Note: This is a simplified version. Full implementation would
        # need to handle in-flight tasks carefully.
        self._max = max(1, new_max)


class ChatAgent:
    """Main chat agent - knowledge base and job foreman.

    This agent understands user requests and either:
    1. Answers directly (knowledge base role)
    2. Delegates to agents, reviews their work, and supervises fixes (foreman role)
    3. Uses planner for complex tasks, then executes the plan with parallel agents
    """

    def __init__(
        self,
        ollama_client: OllamaClient,
        settings: Settings,
        project_dir: str,
    ):
        self.client = ollama_client
        self.settings = settings
        self.project_dir = project_dir
        self.model = settings.models.orchestration

        # Conversation history
        self.conversation_history: List[Message] = []

        # Lazy-loaded specialized agents
        self._explorer_agent = None
        self._executor_agent = None
        self._planner_agent = None

        # System prompt
        self.system_prompt = CHAT_SYSTEM_PROMPT.format(project_dir=project_dir)

        # Max supervision iterations (prevent infinite loops)
        self.max_supervision_rounds = 3

        # Agent concurrency control
        max_agents = settings.regulators.max_concurrent_agents
        self.agent_semaphore = AgentSemaphore(max_concurrent=max_agents)
        self.agent_timeout = settings.regulators.agent_timeout_seconds

    def _get_explorer_agent(self, lite: bool = False):
        """
        Get explorer agent, optionally using lightweight model.

        Args:
            lite: If True, use lightweight model for simple searches
        """
        # For lite mode, always create fresh with lite model
        if lite:
            from .explorer import ExplorerAgent
            model = getattr(self.settings.models, 'exploration_lite', self.settings.models.orchestration)
            return ExplorerAgent(
                ollama_client=self.client,
                working_dir=self.project_dir,
                model=model,
            )

        # Standard explorer (cached)
        if self._explorer_agent is None:
            from .explorer import ExplorerAgent
            model = getattr(self.settings.models, 'exploration', self.settings.models.orchestration)
            self._explorer_agent = ExplorerAgent(
                ollama_client=self.client,
                working_dir=self.project_dir,
                model=model,
            )
        return self._explorer_agent

    def _get_executor_agent(self, lite: bool = False):
        """
        Get executor agent, optionally using lightweight model.

        Args:
            lite: If True, use lightweight model for simple edits
        """
        # For lite mode, always create fresh with lite model
        if lite:
            from .executor import ExecutorAgent
            model = getattr(self.settings.models, 'execution_lite', self.settings.models.execution)
            console.print(f"[dim](using lite model: {model})[/dim]")
            return ExecutorAgent(
                ollama_client=self.client,
                working_dir=self.project_dir,
                model=model,
            )

        # Standard executor (cached)
        if self._executor_agent is None:
            from .executor import ExecutorAgent
            self._executor_agent = ExecutorAgent(
                ollama_client=self.client,
                working_dir=self.project_dir,
                model=self.settings.models.execution,
            )
        return self._executor_agent

    def _get_planner_agent(self):
        """Lazy-load planner agent."""
        if self._planner_agent is None:
            from .planner import PlannerAgent
            self._planner_agent = PlannerAgent(
                ollama_client=self.client,
                model=self.settings.models.planning,
            )
        return self._planner_agent

    def _estimate_complexity(self, task: str) -> str:
        """
        Estimate task complexity to decide which model tier to use.

        Returns: "simple", "moderate", or "complex"
        """
        task_lower = task.lower()

        # Simple tasks - single file, basic operations
        simple_patterns = [
            "read ", "show ", "display ", "print ", "cat ",
            "find file", "list files", "what is", "where is",
            "add comment", "fix typo", "rename variable",
            "simple", "quick", "just ",
        ]
        if any(p in task_lower for p in simple_patterns):
            return "simple"

        # Complex tasks - multi-file, refactoring, features
        complex_patterns = [
            "refactor", "restructure", "redesign", "architect",
            "implement feature", "add feature", "create system",
            "multiple files", "across the codebase", "all files",
            "migrate", "upgrade", "overhaul",
        ]
        if any(p in task_lower for p in complex_patterns):
            return "complex"

        # Moderate - default for most tasks
        return "moderate"

    async def _spawn_agent(
        self,
        agent_type: str,
        task: str,
        force_lite: bool = False,
        force_full: bool = False,
    ) -> Tuple[bool, str]:
        """
        Spawn a specialized agent to handle a task.

        Automatically selects lite or full model based on task complexity,
        unless force_lite or force_full is specified.

        Args:
            agent_type: "explorer", "executor", or "planner"
            task: Task description
            force_lite: Force use of lightweight model
            force_full: Force use of full model

        Returns:
            Tuple of (success, output)
        """
        # Determine model tier based on complexity
        complexity = self._estimate_complexity(task)
        use_lite = force_lite or (complexity == "simple" and not force_full)

        if agent_type == "explorer":
            tier = "lite" if use_lite else "standard"
            console.print(f"[cyan]> Spawning explorer agent ({tier})...[/cyan]")
            agent = self._get_explorer_agent(lite=use_lite)
        elif agent_type == "executor":
            tier = "lite" if use_lite else "full"
            console.print(f"[cyan]> Spawning executor agent ({tier})...[/cyan]")
            agent = self._get_executor_agent(lite=use_lite)
        elif agent_type == "planner":
            console.print(f"[cyan]> Spawning planner agent...[/cyan]")
            agent = self._get_planner_agent()
        else:
            return False, f"Unknown agent type: {agent_type}"

        try:
            # Acquire semaphore slot
            await self.agent_semaphore.acquire()
            try:
                # Run with timeout
                result = await asyncio.wait_for(
                    agent.run(task),
                    timeout=self.agent_timeout
                )
                return result.success, result.output if result.success else (result.error or "Unknown error")
            finally:
                self.agent_semaphore.release()
        except asyncio.TimeoutError:
            return False, f"Agent timed out after {self.agent_timeout} seconds"
        except Exception as e:
            return False, f"Agent failed: {str(e)}"

    async def _spawn_agents_parallel(
        self,
        tasks: List[Tuple[str, str]]  # List of (agent_type, task)
    ) -> List[Tuple[bool, str]]:
        """
        Spawn multiple agents in parallel, respecting max_concurrent_agents.

        Args:
            tasks: List of (agent_type, task_description) tuples

        Returns:
            List of (success, output) tuples in same order as input
        """
        console.print(f"[cyan]> Spawning {len(tasks)} agents (max {self.agent_semaphore._max} concurrent)...[/cyan]")

        async def run_task(agent_type: str, task: str, index: int) -> Tuple[int, bool, str]:
            success, output = await self._spawn_agent(agent_type, task)
            return index, success, output

        # Create tasks
        coroutines = [
            run_task(agent_type, task, i)
            for i, (agent_type, task) in enumerate(tasks)
        ]

        # Run with concurrency control (semaphore is checked in _spawn_agent)
        results_unordered = await asyncio.gather(*coroutines, return_exceptions=True)

        # Sort back to original order and handle exceptions
        results = [None] * len(tasks)
        for result in results_unordered:
            if isinstance(result, Exception):
                # Find first empty slot for exception
                for i in range(len(results)):
                    if results[i] is None:
                        results[i] = (False, str(result))
                        break
            else:
                index, success, output = result
                results[index] = (success, output)

        return results

    async def _execute_plan(self, plan, user_request: str) -> str:
        """
        Execute a plan by running agents according to parallel groups.

        Args:
            plan: Plan object from PlannerAgent
            user_request: Original user request

        Returns:
            Combined results from all steps
        """
        from .planner import Plan

        console.print(f"\n[bold cyan]Executing plan ({len(plan.steps)} steps)...[/bold cyan]")

        step_results: Dict[int, Tuple[bool, str]] = {}
        all_outputs = []

        for group_num, group in enumerate(plan.parallel_groups, 1):
            # Get steps for this group
            group_steps = [s for s in plan.steps if s.step_num in group]

            if not group_steps:
                continue

            console.print(f"\n[cyan]> Group {group_num}: executing {len(group_steps)} step(s) in parallel[/cyan]")

            # Build tasks for parallel execution
            tasks = [(step.agent_type, step.description) for step in group_steps]

            # Execute in parallel
            results = await self._spawn_agents_parallel(tasks)

            # Store results
            for step, (success, output) in zip(group_steps, results):
                step_results[step.step_num] = (success, output)
                status = "[green]✓[/green]" if success else "[red]✗[/red]"
                console.print(f"  {status} Step {step.step_num}: {step.description[:50]}...")
                all_outputs.append(f"### Step {step.step_num}: {step.description}\n{output}")

        # Combine outputs
        combined = "\n\n".join(all_outputs)

        # Review the overall results
        return await self._review_plan_execution(user_request, plan, combined, step_results)

    async def _review_plan_execution(
        self,
        user_request: str,
        plan,
        combined_output: str,
        step_results: Dict[int, Tuple[bool, str]]
    ) -> str:
        """Review the results of plan execution."""
        failed_steps = [num for num, (success, _) in step_results.items() if not success]

        if failed_steps:
            console.print(f"[yellow]> {len(failed_steps)} step(s) failed, reviewing...[/yellow]")

        # Use foreman to review and potentially fix
        return await self._review_and_supervise(
            user_request,
            "plan_execution",
            combined_output,
            len(failed_steps) == 0,
            round_num=1
        )

    def _parse_tool_calls(self, response_text: str) -> List[Dict]:
        """Parse tool calls from response text."""
        tool_calls = []
        valid_tools = {"spawn_explorer", "spawn_executor", "spawn_planner"}

        try:
            if "{" in response_text and "}" in response_text:
                start = 0
                while True:
                    start = response_text.find("{", start)
                    if start == -1:
                        break

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
                            if "name" in data and data["name"] in valid_tools:
                                tool_calls.append(data)
                        except json.JSONDecodeError:
                            pass
                    start = end
        except Exception:
            pass

        return tool_calls

    async def _call_llm(self, messages: List[Message], use_tools: bool = True) -> Tuple[str, List[Dict]]:
        """Call the LLM and return response text and tool calls."""
        response_text = ""
        tool_calls = []

        async for chunk in self.client.chat(
            model=self.model,
            messages=messages,
            tools=AGENT_TOOLS if use_tools else None,
            stream=True,
        ):
            if chunk.message and chunk.message.content:
                response_text += chunk.message.content

            if chunk.done and hasattr(chunk, "message"):
                msg = chunk.message
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    tool_calls.extend(msg.tool_calls)

        # Try parsing tool calls from text if none structured
        if not tool_calls:
            tool_calls = self._parse_tool_calls(response_text)

        # Check for agent keywords in response
        if not tool_calls:
            response_lower = response_text.lower()
            if "spawn_planner" in response_lower:
                tool_calls = [{"name": "spawn_planner", "arguments": {"task": ""}}]
            elif "spawn_explorer" in response_lower:
                tool_calls = [{"name": "spawn_explorer", "arguments": {"task": ""}}]
            elif "spawn_executor" in response_lower:
                tool_calls = [{"name": "spawn_executor", "arguments": {"task": ""}}]

        return response_text, tool_calls

    async def _review_and_supervise(
        self,
        user_request: str,
        agent_type: str,
        agent_output: str,
        agent_success: bool,
        round_num: int,
    ) -> str:
        """
        Review agent work and decide if follow-up is needed.

        Returns final response for the user.
        """
        if round_num >= self.max_supervision_rounds:
            console.print("[yellow]> Max supervision rounds reached[/yellow]")
            return agent_output

        # Build review prompt
        review_content = REVIEW_PROMPT.format(
            user_request=user_request,
            agent_type=agent_type,
            agent_output=agent_output if agent_success else f"AGENT ERROR: {agent_output}",
        )

        messages = [
            Message(role="system", content=self.system_prompt),
            Message(role="user", content=review_content),
        ]

        console.print("[dim]Reviewing work...[/dim]", end="\r")

        try:
            response_text, tool_calls = await self._call_llm(messages)
            console.print("                  ", end="\r")

            # Extract tool call info
            if tool_calls:
                tc = tool_calls[0]
                name = tc.get("name") or tc.get("function", {}).get("name")
                args = tc.get("arguments") or tc.get("function", {}).get("arguments", {})

                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}

                task = args.get("task", "")
                if not task:
                    task = f"Follow up on: {user_request}"

                if name == "spawn_explorer":
                    console.print(f"[yellow]> Foreman requesting explorer follow-up[/yellow]")
                    success, output = await self._spawn_agent("explorer", task)
                    return await self._review_and_supervise(
                        user_request, "explorer", output, success, round_num + 1
                    )
                elif name == "spawn_executor":
                    console.print(f"[yellow]> Foreman requesting executor follow-up[/yellow]")
                    success, output = await self._spawn_agent("executor", task)
                    return await self._review_and_supervise(
                        user_request, "executor", output, success, round_num + 1
                    )

            # No follow-up needed - return the review summary or original output
            return response_text if response_text else agent_output

        except Exception as e:
            console.print("                  ", end="\r")
            return agent_output  # Fall back to original output on error

    async def process(self, user_message: str) -> str:
        """
        Process a user message.

        The chat agent will either:
        1. Respond directly (knowledge base role)
        2. Delegate to agents and supervise (foreman role)
        3. Use planner for complex tasks, then execute with parallel agents
        """
        messages = [
            Message(role="system", content=self.system_prompt),
        ]
        messages.extend(self.conversation_history[-10:])
        messages.append(Message(role="user", content=user_message))

        console.print("[dim]Thinking...[/dim]", end="\r")

        try:
            response_text, tool_calls = await self._call_llm(messages)
            console.print("            ", end="\r")

            # If tool calls, spawn agents and supervise
            if tool_calls:
                tc = tool_calls[0]
                name = tc.get("name") or tc.get("function", {}).get("name")
                args = tc.get("arguments") or tc.get("function", {}).get("arguments", {})

                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}

                task = args.get("task", user_message)

                if name == "spawn_planner":
                    # Get a plan first
                    success, plan_output = await self._spawn_agent("planner", task)

                    if success:
                        # Parse and execute the plan
                        planner = self._get_planner_agent()
                        plan = planner._parse_plan(plan_output)

                        if plan.steps:
                            console.print(f"\n[bold]Plan created ({plan.complexity} complexity, {len(plan.steps)} steps)[/bold]")
                            console.print(f"[dim]{plan.analysis}[/dim]\n")

                            final_response = await self._execute_plan(plan, user_message)
                        else:
                            final_response = f"Plan created but no executable steps found:\n{plan_output}"
                    else:
                        final_response = f"Planning failed: {plan_output}"

                elif name == "spawn_explorer":
                    success, output = await self._spawn_agent("explorer", task)
                    final_response = await self._review_and_supervise(
                        user_message, "explorer", output, success, round_num=1
                    )
                elif name == "spawn_executor":
                    success, output = await self._spawn_agent("executor", task)
                    final_response = await self._review_and_supervise(
                        user_message, "executor", output, success, round_num=1
                    )
                else:
                    final_response = response_text

                self.conversation_history.append(Message(role="user", content=user_message))
                self.conversation_history.append(Message(role="assistant", content=final_response))
                return final_response

            # No tool calls - direct response (knowledge base role)
            self.conversation_history.append(Message(role="user", content=user_message))
            self.conversation_history.append(Message(role="assistant", content=response_text))
            return response_text

        except Exception as e:
            console.print("            ", end="\r")
            return f"Error: {str(e)}"

    def reset_conversation(self) -> None:
        """Reset the conversation history."""
        self.conversation_history = []

    def get_agent_status(self) -> Dict:
        """Get current agent concurrency status."""
        return {
            "active_agents": self.agent_semaphore.active_agents,
            "available_slots": self.agent_semaphore.available_slots,
            "max_concurrent": self.agent_semaphore._max,
        }
