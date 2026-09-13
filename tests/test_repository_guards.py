"""Repository guard tests.

These assert the rules that a human reviewer forgets: no secret or data file in
version control, no upstream provider name anywhere in the tracked tree, and no
advice language in anything an end user reads.

They read the tracked file list from git rather than walking the filesystem, so
an untracked scratch file cannot fail the build and a committed violation
cannot hide behind .gitignore.

These tests refuse to check anything that is not tracked, and refuse to pass
silently when their configuration is missing. A check that cannot fail is
decoration.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# Only text we could plausibly read. Binary and lock files are skipped.
TEXT_SUFFIXES = {
    ".py", ".md", ".mdc", ".txt", ".json", ".yml", ".yaml",
    ".html", ".css", ".js", ".sql", ".toml", ".cfg", ".example",
}

# Paths whose whole purpose is to state the rules, so they are allowed to
# quote the words the rules forbid.
RULE_DOCUMENTS = {
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "STATUS.md",
    ".cursor/rules/woong.mdc",
    ".github/pull_request_template.md",
    "tests/test_repository_guards.py",
}


def tracked_files() -> list[Path]:
    """Every file git knows about, as repository-relative paths."""
    out = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [Path(name) for name in out.split("\0") if name]


def readable_text_files() -> list[Path]:
    return [
        path
        for path in tracked_files()
        if path.suffix in TEXT_SUFFIXES or path.name.startswith(".env")
    ]


def read(path: Path) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Secrets and data
# ---------------------------------------------------------------------------

NEVER_TRACKED = (
    re.compile(r"^\.env$"),
    re.compile(r"^\.env\.local$"),
    re.compile(r".*\.token$"),
    re.compile(r"^data/"),
    re.compile(r".*\.log$"),
    re.compile(r".*\.duckdb$"),
    # Committing the forbidden term list would be the violation it guards
    # against.
    re.compile(r"^\.forbidden-terms$"),
)


def test_no_secret_or_data_file_is_tracked() -> None:
    offenders = [
        str(path)
        for path in tracked_files()
        if any(pattern.match(str(path)) for pattern in NEVER_TRACKED)
    ]
    assert not offenders, (
        "These must never be in version control: " + ", ".join(offenders)
    )


def test_env_example_carries_keys_without_values() -> None:
    """The template teaches which keys exist. It must never carry a real value."""
    example = REPO_ROOT / ".env.example"
    assert example.exists(), ".env.example is the only documentation of required keys"

    filled = [
        line.strip()
        for line in example.read_text(encoding="utf-8").splitlines()
        if "=" in line
        and not line.lstrip().startswith("#")
        and line.split("=", 1)[1].strip() not in ("", "data")
    ]
    assert not filled, f"A value leaked into .env.example: {filled}"


# ---------------------------------------------------------------------------
# Provider names
# ---------------------------------------------------------------------------


def forbidden_terms() -> list[str]:
    """Terms that must not appear in the tracked tree.

    Supplied as configuration, never committed, because a committed list of
    provider names would be the very thing the rule forbids. Either the
    WOONG_FORBIDDEN_TERMS environment variable, comma separated, or a
    gitignored .forbidden-terms file with one term per line.
    """
    from_env = os.environ.get("WOONG_FORBIDDEN_TERMS", "")
    if from_env.strip():
        return [term.strip().lower() for term in from_env.split(",") if term.strip()]

    local = REPO_ROOT / ".forbidden-terms"
    if local.exists():
        return [
            line.strip().lower()
            for line in local.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]
    return []


def test_no_provider_name_in_tracked_tree() -> None:
    terms = forbidden_terms()
    if not terms:
        pytest.skip(
            "No forbidden term list configured. Set WOONG_FORBIDDEN_TERMS or add "
            "a gitignored .forbidden-terms file to arm this guard."
        )

    offenders: list[str] = []
    for path in readable_text_files():
        lowered = read(path).lower()
        for term in terms:
            if term in lowered:
                # The term itself is deliberately not echoed into the failure
                # message, because continuous integration logs are also text we
                # do not want it in.
                offenders.append(str(path))
                break

    assert not offenders, (
        "A configured forbidden term appears in: " + ", ".join(sorted(set(offenders)))
    )


def test_only_generic_source_tags_are_used() -> None:
    """A source tag outside the agreed set means a provider leaked into the schema."""
    allowed = {"primary", "broker", "exchange", "fundamentals", "manual"}
    pattern = re.compile(r"""source\s*[=:]\s*["']([a-z_]+)["']""")

    offenders: list[str] = []
    for path in readable_text_files():
        if str(path) in RULE_DOCUMENTS:
            continue
        for tag in pattern.findall(read(path)):
            if tag not in allowed:
                offenders.append(f"{path}: {tag}")

    assert not offenders, (
        "Source tags must be one of "
        f"{sorted(allowed)}. Found: {offenders}"
    )


# ---------------------------------------------------------------------------
# Advice language
# ---------------------------------------------------------------------------

# Scoped to what an end user reads, plus the labels that reach the screen.
USER_FACING_PREFIXES = ("woong/web/", "woong/api/", "woong/metrics/", "woong/studies/")

ADVICE_PATTERNS = (
    re.compile(r"\bbuy\b", re.I),
    re.compile(r"\bsell\b", re.I),
    re.compile(r"\bhold\b", re.I),
    re.compile(r"\btarget price\b", re.I),
    re.compile(r"\btop pick", re.I),
    re.compile(r"\brecommend", re.I),
    re.compile(r"\bmust[- ]buy\b", re.I),
)

# The one sentence allowed to contain those words, because its job is to deny
# them. Any line stating the denial is permitted.
DENIAL = re.compile(r"not a buy or sell recommendation|no buy or sell recommendation", re.I)


def test_no_advice_language_in_user_facing_files() -> None:
    offenders: list[str] = []
    for path in readable_text_files():
        if not str(path).startswith(USER_FACING_PREFIXES):
            continue
        for number, line in enumerate(read(path).splitlines(), start=1):
            if DENIAL.search(line):
                continue
            for pattern in ADVICE_PATTERNS:
                if pattern.search(line):
                    offenders.append(f"{path}:{number}: {line.strip()}")
                    break

    assert not offenders, (
        "Woong never advises. Remove this language:\n" + "\n".join(offenders)
    )
