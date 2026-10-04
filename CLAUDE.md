# CLAUDE.md

@AGENTS.md

Claude Code specific notes:

- Prefer `collectors/tests/smoke.sh dash` as the first check after any edit to
  a collector; dash is the strictest of the installed shells and catches most
  bash-isms. For the analyzer, run `analyzer/tests/run.sh`.
- The collector logs every collected path to stderr unless `-q` is passed.
  Use `-q` when running it from a tool call so the output stays readable.
- A live run against this workstation collects the author's own Claude Code,
  Gemini, Antigravity, Codex and Copilot state. Write it under the scratchpad
  directory and delete it afterwards.
- The research documents under `collectors/research/` and `analyzer/research/`
  link every source citation to the commit that was reviewed. Open that link
  when checking a path or record shape; the line numbers are only valid at
  that commit, not on the default branch.
- Parser work suits delegation: give a subagent the research document and the
  "Adding a parser" checklist in AGENTS.md, one agent per parser, and reserve
  the main session for review. The same pattern, one agent per lineage pair,
  did the citation linking pass.
