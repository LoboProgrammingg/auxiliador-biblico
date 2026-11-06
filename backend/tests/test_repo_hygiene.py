import subprocess
from pathlib import Path

from app.core.config import Settings

REPO_ROOT = Path(__file__).resolve().parents[2]


def is_ignored(path: str) -> bool:
    result = subprocess.run(["git", "check-ignore", "-q", "--no-index", path], cwd=REPO_ROOT, check=False)
    return result.returncode == 0


def test_gitignore_blocks_secrets_and_data() -> None:
    for path in [".env", ".env.local", "data/x.json", "data/sources/pt_vfl.json"]:
        assert is_ignored(path), path
    assert not is_ignored(".env.example")


def test_env_example_lists_every_setting_without_secret_values() -> None:
    lines = (REPO_ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
    entries = dict(line.split("=", 1) for line in lines if line and not line.startswith("#"))
    for field in Settings.model_fields:
        assert field.upper() in entries, field
    for key in ("SERPER_API_KEY", "ANTHROPIC_API_KEY", "POSTGRES_PASSWORD"):
        assert entries.get(key, "") == "", key
