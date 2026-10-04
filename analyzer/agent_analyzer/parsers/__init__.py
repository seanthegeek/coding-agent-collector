"""Parser registry. Add a parser module here and in the README's table."""
from __future__ import annotations

from typing import Dict, List

from .base import Options, Parser
from .antigravity import AntigravityParser
from .claude_code import ClaudeCodeParser
from .codex import CodexParser
from .kiro import KiroParser
from .qwen_code import QwenCodeParser
from .gemini_cli import GeminiCliParser

ALL: List[Parser] = [
    ClaudeCodeParser(),
    CodexParser(),
    AntigravityParser(),
    QwenCodeParser(),
    KiroParser(),
    GeminiCliParser(),
]


def by_agent() -> Dict[str, List[Parser]]:
    out: Dict[str, List[Parser]] = {}
    for p in ALL:
        out.setdefault(p.agent, []).append(p)
    return out


__all__ = ["ALL", "Options", "Parser", "by_agent"]
