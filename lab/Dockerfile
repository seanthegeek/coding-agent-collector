# Disposable sandbox for running CLI coding agents against a scratch home.
# Nothing from the host is mounted; the home lives in a named volume and is
# exported with lab.sh for the collector to read in image mode.
FROM node:22-bookworm

# npm packages installed globally (outside the home, so the exported fixture
# holds only agent state, never the agent binaries). Override at build time:
#   NPM_AGENTS="@anthropic-ai/claude-code @github/copilot" ./lab.sh build
ARG NPM_AGENTS="@anthropic-ai/claude-code @openai/codex @google/gemini-cli"
# Python packages, for example PIP_AGENTS="aider-chat".
ARG PIP_AGENTS=""

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates curl git less procps ripgrep sqlite3 \
      python3 python3-pip python3-venv \
 && rm -rf /var/lib/apt/lists/*

RUN npm install -g $NPM_AGENTS && npm cache clean --force

RUN if [ -n "$PIP_AGENTS" ]; then \
      python3 -m venv /opt/agents && /opt/agents/bin/pip install --no-cache-dir $PIP_AGENTS; \
    else mkdir -p /opt/agents/bin; fi
ENV PATH=/opt/agents/bin:$PATH

# Replace the image's default user with one whose name will show up in the
# collector's user enumeration.
RUN userdel -r node 2>/dev/null || true \
 && useradd -m -u 1000 -s /bin/bash agent

# A small git repository so project discovery has a cwd to find.
USER agent
ENV HOME=/home/agent
RUN git config --global user.name lab \
 && git config --global user.email lab@example.invalid \
 && git config --global init.defaultBranch main \
 && mkdir -p /home/agent/work/sample \
 && cd /home/agent/work/sample \
 && git init -q \
 && printf '# sample\n\nScratch project for exercising coding agents.\n' > README.md \
 && printf 'Keep answers short. This repository is a test fixture.\n' > AGENTS.md \
 && printf 'def add(a, b):\n    return a + b\n' > calc.py \
 && git add -A && git commit -qm 'Initial commit'

WORKDIR /home/agent/work/sample
CMD ["sleep", "infinity"]
