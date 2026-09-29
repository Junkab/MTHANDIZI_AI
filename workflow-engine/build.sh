#!/bin/bash
# Compiles the workflow engine + tests into a single runnable jar.
# Requires kotlinc on PATH - see README.md for how to get it without Maven/Gradle.
set -e
cd "$(dirname "$0")"
mkdir -p build
kotlinc src/main/*.kt src/test/*.kt -include-runtime -d build/workflow-tests.jar
echo "Built build/workflow-tests.jar"
