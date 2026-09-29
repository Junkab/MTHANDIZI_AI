#!/bin/bash
# Runs the full test suite. Must be run from this directory (workflow-engine/)
# since tests load the real service JSON files via relative path services/*.json.
set -e
cd "$(dirname "$0")"
if [ ! -f build/workflow-tests.jar ]; then
  echo "No build found - running build.sh first"
  ./build.sh
fi
java -cp build/workflow-tests.jar mthandizi.workflow.test.RunTestsKt
