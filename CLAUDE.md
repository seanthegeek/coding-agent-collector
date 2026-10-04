# CLAUDE.md

@AGENTS.md

Claude Code specific notes:

- Prefer `collectors/tests/smoke.sh dash` as the first check after any edit to
  a collector; dash is the strictest of the installed shells and catches most
  bash-isms. For the analyzer, run `analyzer/tests/run.sh`.
- Before committing Python, Markdown, sh or PowerShell, run the matching
  lint commands from "Quality gates" in AGENTS.md; CI runs them, the
  pre-commit hook does not.
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

## Orchestration

Work in this repository is split by model to keep Fable usage for the parts
that need it:

- **Fable plans.** The main session, on Fable, scopes the task, reads what it
  needs to write a precise brief, and decides how to split the work.
- **Opus implements.** Every implementation step goes to a subagent with
  `model: opus`: parsers, catalog research, citation passes, and the
  integration that merges the pieces. One subagent per self-contained unit
  (one parser, one research document, one lineage pair), launched in
  parallel. When several units touch the same files, give each subagent
  `isolation: worktree`, tell it to commit on its branch without pushing,
  keep shared-file edits append-only, and send one more Opus subagent to
  merge the branches and resolve the predictable overlaps (registries,
  fixtures, test classes, README tables).
- **Fable reviews.** The main session reads each subagent's report, checks
  the diff against the brief and the research documents, runs the test
  suite itself, fixes or sends back what is wrong, then commits and pushes.
  Subagent reports are evidence, not approval; a claim that tests pass is
  re-run, not trusted.

The brief for each subagent lives in the scratchpad as one file every
subagent in that round reads, so the rules are identical and the prompt per
agent is only its assignment. The brief names the files to read first, the
rules that must hold, the files the agent may and may not touch, and the
report format.

If Fable becomes unavailable mid-task (a usage-limit or rate-limit error
from the API), say so to the user in plain words before doing anything
else, then continue with Opus: run the planning and review steps through
`model: opus` subagents rather than stopping, and label the result as
Opus-reviewed so the user can decide whether a Fable pass is still wanted.
Never fabricate a report from a subagent that was cut off; relaunch it.
