import logging
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ClaudeSDKError,
    ResultMessage,
    StreamEvent,
)

from app.application.chat.ports import AgentDone, AgentEvent, AgentText, AgentTools, AgentToolStart, TokenUsage
from app.application.chat.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)
PLUGIN_DIR = Path(__file__).resolve().parents[4] / "agente-plugin"
SKILLS = ["auxiliador-biblico:ilustracoes", "auxiliador-biblico:pensadores"]
BLOCKED_BUILTINS = ["Bash", "Read", "Write", "Edit", "Glob", "Grep", "NotebookEdit", "Task", "TodoWrite", "WebFetch"]


def paid_key_blocked(permitir: bool) -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip()) and not permitir


def _error_code(message: ResultMessage) -> str:
    status = getattr(message, "api_error_status", None)
    if status in (401, 403):
        return "claude_code_login"
    if status == 429:
        return "limite_claude"
    return "agente_erro"


_INPUT_KEYS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")


def _token_usage(usage: dict[str, Any] | None) -> TokenUsage | None:
    if not usage:
        return None
    output = int(usage.get("output_tokens") or 0)
    total = sum(int(usage.get(key) or 0) for key in _INPUT_KEYS) + output
    return TokenUsage(total=total, output=output, cached=int(usage.get("cache_read_input_tokens") or 0))


def map_message(message: Any) -> list[AgentEvent]:
    if isinstance(message, StreamEvent):
        event = message.event
        if event.get("type") == "content_block_delta" and event.get("delta", {}).get("type") == "text_delta":
            return [AgentText(event["delta"]["text"])]
        block = event.get("content_block", {})
        if event.get("type") == "content_block_start" and block.get("type") in ("tool_use", "server_tool_use"):
            return [AgentToolStart(block.get("name", ""))]
        return []
    if isinstance(message, ResultMessage):
        error = _error_code(message) if message.is_error else None
        return [AgentDone(message.session_id, message.is_error, error, _token_usage(message.usage))]
    return []


class ClaudeAgentRunner:
    def __init__(self, model: str, effort: str, workdir: Path, permitir_api_paga: bool) -> None:
        self._model, self._effort, self._workdir, self._permitir = model, effort, workdir, permitir_api_paga

    def _options(
        self, session_id: str | None, tools: AgentTools, effort: str | None = None, model: str | None = None
    ) -> ClaudeAgentOptions:
        self._workdir.mkdir(parents=True, exist_ok=True)
        return ClaudeAgentOptions(
            model=model or self._model,
            effort=effort or self._effort,  # type: ignore[arg-type]
            system_prompt=SYSTEM_PROMPT,
            setting_sources=[],
            plugins=[{"type": "local", "path": str(PLUGIN_DIR)}],
            skills=SKILLS,
            cwd=str(self._workdir),
            mcp_servers={"biblia": tools.server},
            strict_mcp_config=True,
            tools=["WebSearch"],
            allowed_tools=tools.allowed,
            disallowed_tools=BLOCKED_BUILTINS,
            permission_mode="dontAsk",
            include_partial_messages=True,
            max_turns=24,
            resume=session_id,
        )

    async def run(
        self,
        prompt: str,
        session_id: str | None,
        tools: AgentTools,
        effort: str | None = None,
        model: str | None = None,
    ) -> AsyncIterator[AgentEvent]:
        if paid_key_blocked(self._permitir):
            yield AgentDone(session_id or "", True, "chave_paga_detectada")
            return
        try:
            async with ClaudeSDKClient(options=self._options(session_id, tools, effort, model)) as client:
                await client.query(prompt)
                async for message in client.receive_response():
                    for event in map_message(message):
                        yield event
        except ClaudeSDKError as exc:
            logger.warning("agente indisponível: %s", type(exc).__name__)
            yield AgentDone(session_id or "", True, "claude_code_indisponivel")
