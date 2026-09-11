"""
Multi-step agent loop:

User → Local AI → Plan → Tool → Observe → Evaluate → Next tool or finish
"""
from __future__ import annotations

import re
from typing import Callable

from jarvis.ai.tools import parse_tools, strip_tool_tags


PLAN_HINT = (
    "You are an agent. For multi-step tasks, call tools one step at a time using:\n"
    "[TOOL:name|arg=value]\n"
    "After each tool result you will see OBSERVATION. Then either call another tool "
    "or give the final answer to Ty with no tool tags.\n"
    "Never invent observation results. Prefer at most a few tool steps."
)


class AgentLoop:
    def __init__(
        self,
        engine,
        tools,
        system_prompt_fn: Callable[[], str],
        max_steps: int = 6,
        audit=None,
    ):
        self.engine = engine
        self.tools = tools
        self.system_prompt_fn = system_prompt_fn
        self.max_steps = max_steps
        self.audit = audit

    def run(self, user_message: str, history: list[dict]) -> str:
        if not self.engine.ready:
            raise RuntimeError("Local model not loaded")

        system = self.system_prompt_fn() + "\n" + PLAN_HINT
        work_history = list(history[-12:])
        observations: list[str] = []
        last_text = ""

        for step in range(self.max_steps):
            prompt_user = user_message
            if observations:
                prompt_user = (
                    f"Original request: {user_message}\n\n"
                    + "\n".join(observations)
                    + "\n\nContinue: use another [TOOL:...] if needed, otherwise answer Ty finally."
                )

            text = self.engine.chat(system, work_history, prompt_user)
            last_text = text or ""
            calls = parse_tools(last_text)

            if not calls:
                # Final natural language answer
                return strip_tool_tags(last_text) or last_text

            # Execute tools in this step (allow multiple in one model output)
            step_results = []
            for name, args in calls:
                if self.audit:
                    self.audit.log(f"Agent tool step {step + 1}: {name}")
                result = self.tools.execute(name, args)
                step_results.append(f"{name} → {result}")

            obs = f"OBSERVATION (step {step + 1}): " + " | ".join(step_results)
            observations.append(obs)
            work_history = work_history + [
                {"role": "user", "content": prompt_user},
                {"role": "assistant", "content": last_text},
                {"role": "user", "content": obs},
            ]

        # Max steps reached — summarize
        summary = strip_tool_tags(last_text)
        trail = "\n".join(observations)
        if summary:
            return f"{summary}\n\n(Completed {len(observations)} tool step(s).)\n{trail}"
        return f"Reached step limit. Results so far:\n{trail}"
