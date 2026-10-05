#!/bin/sh
# Run the analyzer test suite with the standard library runner.
#
# No test names: run the whole suite with unittest discover; options such
# as -v, -k, -f, -p go to discover.
# One or more test names (test_catalog, test_parsers.ClaudeCodeTests,
# test_parsers.ClaudeCodeTests.test_rows): run only those, with tests/ on
# the import path so the modules import as discover imports them. -v, -k,
# -f, -c, -b still apply; -p, -s and -t are discover-only and are refused.
cd "$(dirname "$0")/.." || exit 2

names=0
discover_opt=""
skip=0
for arg in "$@"; do
    if [ "$skip" = 1 ]; then
        skip=0
        continue
    fi
    case $arg in
    -p | -s | -t | --pattern | --start-directory | --top-level-directory)
        discover_opt=$arg
        skip=1
        ;;
    -p* | -s* | -t* | --pattern=* | --start-directory=* | --top-level-directory=*)
        discover_opt=$arg
        ;;
    -k | --durations)
        skip=1
        ;;
    -*) ;;
    *)
        names=1
        ;;
    esac
done

if [ "$names" = 0 ]; then
    exec python3 -m unittest discover -s tests -t tests "$@"
fi
if [ -n "$discover_opt" ]; then
    echo "run.sh: $discover_opt applies only without test names" >&2
    exit 2
fi
PYTHONPATH="tests${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONPATH
exec python3 -m unittest "$@"
