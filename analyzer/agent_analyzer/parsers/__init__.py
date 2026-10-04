"""Parser registry. Add a parser module here and in the README's table."""
from __future__ import annotations

from typing import Dict, List

from .base import Options, Parser
from .antigravity import AntigravityParser
from .claude_code import ClaudeCodeParser
from .codex import CodexParser
from .opencode import OpenCodeParser
from .kilo_code import KiloCodeParser

ALL: List[Parser] = [ClaudeCodeParser(), CodexParser(), AntigravityParser()]
ALL.append(OpenCodeParser())
ALL.append(KiloCodeParser())


def by_agent() -> Dict[str, List[Parser]]:
    out: Dict[str, List[Parser]] = {}
    for p in ALL:
        out.setdefault(p.agent, []).append(p)
    return out


__all__ = ["ALL", "Options", "Parser", "by_agent"]
