from functools import cache
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parents[3] / "agente-plugin" / "skills"


@cache
def skill_body(name: str) -> str:
    """Corpo da skill sem o cabeçalho: vai inteiro no pedido quando o botão do modo está ligado."""
    text = (SKILLS_DIR / name / "SKILL.md").read_text(encoding="utf-8")
    if text.startswith("---\n"):
        text = text.split("\n---\n", 1)[1]
    return text.strip()
