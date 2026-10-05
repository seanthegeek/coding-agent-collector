"""Analyst-side analyzer for coding-agent-collector output.

Reads a collector archive, an extracted collection directory, or any loose
directory tree (a copied home directory, a mounted image), detects which AI
coding agents left state in it, and parses the agents' transcripts into a
normalised JSONL timeline. Nothing here runs on the host under investigation.
"""

VERSION = "0.8.1"
