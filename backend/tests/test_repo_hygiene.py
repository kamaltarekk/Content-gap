from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKIP_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "legacy",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
}


def _source_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix in {
            ".py",
            ".ts",
            ".tsx",
            ".json",
            ".md",
            ".yml",
            ".yaml",
            ".toml",
            ".env",
            ".example",
            ".ini",
        } or path.name.startswith(".env"):
            files.append(path)
    return files


def test_no_real_anthropic_key_in_repo() -> None:
    # Build the needle at runtime so this file does not match itself.
    needle = "sk-" + "ant-"
    offenders = []
    for path in _source_files():
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if needle in text:
            offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, f"Possible real API keys committed: {offenders}"


def test_env_example_has_blank_secret() -> None:
    example = ROOT / ".env.example"
    assert example.exists(), ".env.example must exist"
    for line in example.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("ANTHROPIC_API_KEY"):
            assert line.strip() in ("ANTHROPIC_API_KEY=", "ANTHROPIC_API_KEY= "), (
                "API key must be blank in .env.example"
            )


def test_env_not_tracked_by_git() -> None:
    # The real .env must be gitignored, never committed.
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "\n.env\n" in gitignore or gitignore.startswith(".env\n") or "\n.env" in gitignore
