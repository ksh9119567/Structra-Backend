#!/bin/sh
# Run the automated test-suite.
#
#   scripts/run_tests.sh                      whole suite
#   scripts/run_tests.sh teams                one app
#   scripts/run_tests.sh teams projects tasks several apps
#   scripts/run_tests.sh projects -v 2        anything else is passed to `manage.py test`
#   scripts/run_tests.sh --failfast --parallel 4
#
# Apps: accounts organizations teams projects tasks governance comments sprints core
# (`core` = shared permissions, utils, activity logging, HTTP behaviour)
#
# Tests use config/settings_test.py automatically: in-memory SQLite, an in-memory
# fake Redis, eager Celery and captured e-mail - no Postgres / Redis / Docker needed.
# Set TEST_DB=postgres to run against PostgreSQL instead (see docs/TESTING.md).
set -e
cd "$(dirname "$0")/.."

if [ -x .task_venv/Scripts/python.exe ]; then
  PY=.task_venv/Scripts/python.exe
elif [ -x .task_venv/bin/python ]; then
  PY=.task_venv/bin/python
else
  PY=${PYTHON:-python}
fi

labels=""
extra=""
for arg in "$@"; do
  case "$arg" in
    accounts|comments|governance|organizations|projects|sprints|tasks|teams) labels="$labels app.$arg" ;;
    core) labels="$labels core" ;;
    *) extra="$extra $arg" ;;
  esac
done

# shellcheck disable=SC2086
exec "$PY" manage.py test $labels $extra
