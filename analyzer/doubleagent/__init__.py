"""doubleagent: forensic analysis of AI agent use on a system.

Reads a collector archive, an extracted collection directory, or any loose
directory tree (a copied home directory, a mounted image), detects which AI
agents left state in it, and parses the agents' transcripts into a
normalised JSONL timeline. Nothing here runs on the host under investigation.
"""

VERSION = "0.9.0"
