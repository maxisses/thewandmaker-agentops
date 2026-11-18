#!/usr/bin/env bash
# Give the OpenShell supervisor in every apprentice sandbox room for more open files.
#
# Why: OpenShell 0.0.116's supervisor keeps one upstream connection to the tool gateway open for
# every MCP session the agent ever made (15 November: 527 of them after a day of campaigns), and
# it starts with the container default of 1024 open files. At 1024 it can't accept anything any
# more: every turn ends in 0 seconds with "Too many open files", and the shop says "The apprentice
# is lost for words". The hard limit is 524288, so we raise the soft one; the connections still
# pile up, but there is room for tens of thousands of turns.
#
# Needs a logged-in oc. Run it after a sandbox was (re)created; apprentice.sh does. Idempotent.
set -euo pipefail
LIMIT=${SUPERVISOR_NOFILE:-65536}
for pod in $(oc get pods -n openshell -o name | grep -E '^pod/default--apprentice(-[0-9]+)?$'); do
  oc exec -n openshell "$pod" -c agent -- sh -c "
    prlimit --pid 1 --nofile=$LIMIT:524288 &&
    echo \"${pod#pod/}: supervisor may open \$(awk '/Max open files/{print \$4}' /proc/1/limits) files, has \$(ls /proc/1/fd | wc -l) open\""
done
