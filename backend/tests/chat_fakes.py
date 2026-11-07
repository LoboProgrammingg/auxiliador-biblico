import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from app.application.chat.ports import AgentDone, AgentText, AgentTools, AgentToolStart


@dataclass
class FakeAgentRunner:
    """Roteiro: lista de itens str (texto), ("tool", nome, args) ou ("done", is_error, erro[, uso])."""

    script: list[Any]
    session_id: str = "sess-1"
    calls: list[dict[str, Any]] = field(default_factory=list)
    delay: float = 0.0

    async def run(
        self,
        prompt: str,
        session_id: str | None,
        tools: AgentTools,
        effort: str | None = None,
        model: str | None = None,
    ) -> AsyncIterator[Any]:
        self.calls.append(
            {"prompt": prompt, "session_id": session_id, "allowed": tools.allowed, "effort": effort, "model": model}
        )
        for item in self.script:
            if self.delay:
                await asyncio.sleep(self.delay)
            if isinstance(item, str):
                yield AgentText(item)
            elif item[0] == "tool":
                yield AgentToolStart(f"mcp__biblia__{item[1]}")
                await tools.invoke(item[1], item[2])
            elif item[0] == "done":
                yield AgentDone(self.session_id, item[1], item[2], *item[3:])
                return
        yield AgentDone(self.session_id, False, None)
