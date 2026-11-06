from claude_agent_sdk import ResultMessage, StreamEvent

from app.application.chat.ports import AgentDone, AgentText, AgentToolStart
from app.infrastructure.external.agent_sdk.runner import map_message, paid_key_blocked


def stream(event: dict) -> StreamEvent:  # type: ignore[type-arg]
    return StreamEvent(uuid="u", session_id="s", event=event)


def test_runner_maps_stream_events() -> None:
    assert map_message(stream({"type": "content_block_delta", "delta": {"type": "text_delta", "text": "Oi"}})) == [
        AgentText("Oi")
    ]
    start = stream({"type": "content_block_start", "content_block": {"type": "tool_use", "name": "mcp__biblia__x"}})
    assert map_message(start) == [AgentToolStart("mcp__biblia__x")]
    thinking = stream({"type": "content_block_delta", "delta": {"type": "thinking_delta", "thinking": "..."}})
    assert map_message(thinking) == []


def test_runner_maps_result() -> None:
    result = ResultMessage(
        subtype="success", duration_ms=1, duration_api_ms=1, is_error=False, num_turns=1, session_id="sess"
    )
    assert map_message(result) == [AgentDone("sess", False, None)]


def test_paid_key_blocked(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-x")
    assert paid_key_blocked(permitir=False) is True
    assert paid_key_blocked(permitir=True) is False
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    assert paid_key_blocked(permitir=False) is False


def _result(status: int | None) -> ResultMessage:
    return ResultMessage(
        subtype="success",
        duration_ms=1,
        duration_api_ms=1,
        is_error=True,
        num_turns=1,
        session_id="s",
        api_error_status=status,
    )


def test_runner_maps_api_errors_to_actionable_codes() -> None:
    assert map_message(_result(401)) == [AgentDone("s", True, "claude_code_login")]
    assert map_message(_result(403)) == [AgentDone("s", True, "claude_code_login")]
    assert map_message(_result(429)) == [AgentDone("s", True, "limite_claude")]
    assert map_message(_result(None)) == [AgentDone("s", True, "agente_erro")]


def test_error_messages_exist_for_new_codes() -> None:
    from app.application.chat.events import ERROR_MESSAGES

    assert "claude" in ERROR_MESSAGES["claude_code_login"] and "limite" in ERROR_MESSAGES["limite_claude"]


def test_runner_options_never_enable_webfetch(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from app.application.chat.ports import AgentTools
    from app.infrastructure.external.agent_sdk.runner import ClaudeAgentRunner

    options = ClaudeAgentRunner("m", "medium", tmp_path, False)._options(None, AgentTools({}, ["WebSearch"], None))  # type: ignore[arg-type]
    assert options.tools == ["WebSearch"] and "WebFetch" in options.disallowed_tools


def test_runner_effort_override(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from app.application.chat.ports import AgentTools
    from app.infrastructure.external.agent_sdk.runner import ClaudeAgentRunner

    runner = ClaudeAgentRunner("m", "medium", tmp_path, False)
    tools = AgentTools({}, ["WebSearch"], None)  # type: ignore[arg-type]
    assert runner._options(None, tools).effort == "medium"
    assert runner._options(None, tools, "high").effort == "high"
