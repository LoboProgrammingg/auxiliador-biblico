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


def test_runner_maps_token_usage() -> None:
    from app.application.chat.ports import TokenUsage

    usage = {
        "input_tokens": 10,
        "cache_creation_input_tokens": 200,
        "cache_read_input_tokens": 3000,
        "output_tokens": 45,
    }
    result = ResultMessage(
        subtype="success", duration_ms=1, duration_api_ms=1, is_error=False, num_turns=3, session_id="s", usage=usage
    )
    assert map_message(result) == [AgentDone("s", False, None, TokenUsage(total=3255, output=45, cached=3000))]


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


def test_runner_model_override(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from app.application.chat.ports import AgentTools
    from app.infrastructure.external.agent_sdk.runner import ClaudeAgentRunner

    runner = ClaudeAgentRunner("m", "medium", tmp_path, False)
    tools = AgentTools({}, ["WebSearch"], None)  # type: ignore[arg-type]
    assert runner._options(None, tools).model == "m"
    assert runner._options(None, tools, None, "claude-opus-5-5").model == "claude-opus-5-5"


def test_runner_loads_only_the_bundled_skills(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from pathlib import Path

    from app.application.chat.ports import AgentTools
    from app.infrastructure.external.agent_sdk.runner import PLUGIN_DIR, SKILLS, ClaudeAgentRunner

    options = ClaudeAgentRunner("m", "medium", tmp_path, False)._options(None, AgentTools({}, ["WebSearch"], None))  # type: ignore[arg-type]
    assert options.setting_sources == []
    assert options.plugins == [{"type": "local", "path": str(PLUGIN_DIR)}]
    assert options.skills == SKILLS == ["auxiliador-biblico:ilustracoes", "auxiliador-biblico:pensadores"]
    skill = Path(PLUGIN_DIR) / "skills" / "ilustracoes" / "SKILL.md"
    body = skill.read_text(encoding="utf-8")
    assert body.startswith("---\nname: ilustracoes\n")
    for marker in ("[[linha:", "[[mapa:", "[[rota:", "[[quiasmo:", "[[fio:"):
        assert marker in body
    thinkers = (Path(PLUGIN_DIR) / "skills" / "pensadores" / "SKILL.md").read_text(encoding="utf-8")
    assert thinkers.startswith("---\nname: pensadores\n") and "[[pensador:" in thinkers
    video = (Path(PLUGIN_DIR) / "skills" / "video-viral" / "SKILL.md").read_text(encoding="utf-8")
    assert video.startswith("---\nname: video-viral\n")
    for needed in ("Victor Power", "Single continuous shot", "[[", "Rosto de Jesus"):
        assert needed in video
    deep = (Path(PLUGIN_DIR) / "skills" / "estudo-complexo" / "SKILL.md").read_text(encoding="utf-8")
    assert deep.startswith("---\nname: estudo-complexo\n")
    for needed in ("concordancia_original", "referencias_cruzadas", "ilustracoes", "pensadores", "Fontes consultadas"):
        assert needed in deep


def test_system_prompt_points_to_the_skill_instead_of_carrying_it() -> None:
    from app.application.chat.prompts import SYSTEM_PROMPT

    assert "ilustracoes" in SYSTEM_PROMPT
    for marker in ("[[linha:", "[[mapa:", "[[quiasmo:", "[[rota:"):
        assert marker not in SYSTEM_PROMPT


def test_runner_has_room_for_reading_and_eight_web_searches(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from app.application.chat.ports import AgentTools
    from app.infrastructure.external.agent_sdk.runner import ClaudeAgentRunner

    options = ClaudeAgentRunner("m", "medium", tmp_path, False)._options(None, AgentTools({}, ["WebSearch"], None))  # type: ignore[arg-type]
    assert options.max_turns == 24


def test_prompt_asks_for_interpretations_with_verses_first() -> None:
    from app.application.chat.prompts import SYSTEM_PROMPT

    assert "no mínimo 4 fontes" in SYSTEM_PROMPT and "no máximo 8 pesquisas" in SYSTEM_PROMPT
    assert "Fontes consultadas" in SYSTEM_PROMPT


def test_system_prompt_speaks_with_its_own_voice() -> None:
    from app.application.chat.prompts import SYSTEM_PROMPT

    assert "## Sua voz" in SYSTEM_PROMPT and "conclusões próprias" in SYSTEM_PROMPT
    assert "## Quando pedirem resposta breve" in SYSTEM_PROMPT
    assert "sem tomar partido" not in SYSTEM_PROMPT
    assert "pensamento crítico" in SYSTEM_PROMPT


def test_system_prompt_batches_tools_and_reads_memory_from_the_prompt() -> None:
    from app.application.chat.prompts import SYSTEM_PROMPT

    assert "## Como usar as ferramentas" in SYSTEM_PROMPT and "no máximo 2 rodadas" in SYSTEM_PROMPT
    assert "[Memória da pessoa]" in SYSTEM_PROMPT
    assert "No começo de cada conversa, chame memoria_listar" not in SYSTEM_PROMPT


def test_prompt_guides_study_plans_and_septuagint_lookups() -> None:
    from app.application.chat.prompts import SYSTEM_PROMPT

    assert "## Plano de estudo" in SYSTEM_PROMPT and "ordem cronológica" in SYSTEM_PROMPT
    assert "### Curiosidades" in SYSTEM_PROMPT and "fale sobre o tópico 1" in SYSTEM_PROMPT
    assert "Septuaginta" in SYSTEM_PROMPT
