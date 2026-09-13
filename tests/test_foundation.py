"""Tests for the repository's own working agreement.

The board and the locked decisions are read by every session. If they drift out
of shape, a session reads the wrong thing and builds the wrong item. These
tests refuse to let that happen quietly.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def load_board() -> dict:
    return json.loads((REPO_ROOT / "mvp" / "tasks.json").read_text(encoding="utf-8"))


def test_board_is_valid_and_ordered() -> None:
    board = load_board()
    ids = [task["id"] for task in board["tasks"]]
    assert ids == sorted(ids), f"Work items must stay in order: {ids}"
    assert len(ids) == len(set(ids)), f"Duplicate work item identifier: {ids}"


def test_exactly_one_item_is_in_progress() -> None:
    """One thing at a time. No parallel builds."""
    doing = [task["id"] for task in load_board()["tasks"] if task["status"] == "doing"]
    assert len(doing) == 1, f"Exactly one item may be in progress, found {doing}"


def test_every_item_states_what_and_why() -> None:
    for task in load_board()["tasks"]:
        assert task["what"].strip(), f"{task['id']} has no scope"
        assert task["why"].strip(), f"{task['id']} has no reason to exist"
        assert task["issue"], f"{task['id']} has no issue. No issue, no branch."


def test_board_states_what_a_user_gets() -> None:
    """The board is builder-facing, so it has to keep naming the user's outcome."""
    board = load_board()
    for key in ("user_gets_today", "user_gets_when_ready", "one_thing", "why"):
        assert board[key].strip(), f"The board must answer {key}"


def test_documents_every_session_reads_exist() -> None:
    required = [
        "AGENTS.md",
        "CLAUDE.md",
        "STATUS.md",
        "mvp/tasks.json",
        "docs/PRODUCT.md",
        "docs/ARCHITECTURE.md",
        "docs/QUERY.md",
        "docs/DATA.md",
        "docs/CONTRIBUTING.md",
        ".cursor/rules/woong.mdc",
    ]
    missing = [name for name in required if not (REPO_ROOT / name).exists()]
    assert not missing, f"Missing documents a session depends on: {missing}"


def test_locked_decisions_are_present() -> None:
    """STATUS.md is append only. These five must never be edited away."""
    status = (REPO_ROOT / "STATUS.md").read_text(encoding="utf-8").lower()
    for phrase in (
        "never gives a buy or sell recommendation",
        "switched off and says why",
        "no upstream provider name",
        "python computes every number",
        "filter and rank are separate stages",
    ):
        assert phrase in status, f"A locked decision went missing from STATUS.md: {phrase}"
