"""Parser registry. Add a parser module here and in the parser table in docs/parsers.md."""

from __future__ import annotations

from .agent_zero import AgentZeroParser
from .aider import AiderParser
from .antigravity import AntigravityParser
from .base import Options, Parser
from .claude_code import ClaudeCodeParser
from .cline import ClineParser
from .codex import CodexParser
from .cody import CodyParser
from .continue_dev import ContinueParser
from .crush import CrushParser
from .gemini_cli import GeminiCliParser
from .goose import GooseParser
from .hermes import HermesParser
from .kilo_code import KiloCodeParser
from .kiro import KiroParser
from .letta import LettaParser
from .little_coder import LittleCoderParser
from .muse_code import MuseCodeParser
from .nanobot import NanobotParser
from .ollama import OllamaParser
from .open_interpreter import OpenInterpreterParser
from .openclaw import OpenClawParser
from .opencode import OpenCodeParser
from .openhands import OpenHandsParser
from .pearai import PearAiParser
from .pi import PiParser
from .qwen_code import QwenCodeParser
from .roo_code import RooCodeParser
from .shellgpt import ShellGptParser
from .tabby import TabbyParser
from .twinny import TwinnyParser
from .vscode import VsCodeParser
from .zed import ZedParser

ALL: list[Parser] = [
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
    PiParser(),
    LittleCoderParser(),
    LettaParser(),
    HermesParser(),
    AgentZeroParser(),
    OpenInterpreterParser(),
    OpenClawParser(),
    NanobotParser(),
    CodyParser(),
    TwinnyParser(),
    PearAiParser(),
    MuseCodeParser(),
    OllamaParser(),
]


def by_agent() -> dict[str, list[Parser]]:
    out: dict[str, list[Parser]] = {}
    for p in ALL:
        out.setdefault(p.agent, []).append(p)
    return out


__all__ = ["ALL", "Options", "Parser", "by_agent"]
