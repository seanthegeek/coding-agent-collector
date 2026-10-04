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
from .crush import CrushParser
from .goose import GooseParser
from .continue_dev import ContinueParser
from .aider import AiderParser
from .zed import ZedParser
from .vscode import VsCodeParser
from .opencode import OpenCodeParser
from .kilo_code import KiloCodeParser
from .cline import ClineParser
from .roo_code import RooCodeParser
from .tabby import TabbyParser
from .openhands import OpenHandsParser
from .shellgpt import ShellGptParser

ALL: List[Parser] = [
    ClaudeCodeParser(),
    CodexParser(),
    AntigravityParser(),
    QwenCodeParser(),
    KiroParser(),
    GeminiCliParser(),
    CrushParser(),
    GooseParser(),
    ContinueParser(),
    AiderParser(),
    ZedParser(),
    VsCodeParser(),
    OpenCodeParser(),
    KiloCodeParser(),
    ClineParser(),
    RooCodeParser(),
    TabbyParser(),
    OpenHandsParser(),
    ShellGptParser(),
]


def by_agent() -> Dict[str, List[Parser]]:
    out: Dict[str, List[Parser]] = {}
    for p in ALL:
        out.setdefault(p.agent, []).append(p)
    return out


__all__ = ["ALL", "Options", "Parser", "by_agent"]
