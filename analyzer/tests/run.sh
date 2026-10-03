#!/bin/sh
# Run the analyzer test suite with the standard library runner.
cd "$(dirname "$0")/.." && exec python3 -m unittest discover -s tests -t tests "$@"
