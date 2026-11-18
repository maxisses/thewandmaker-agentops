#!/usr/bin/env bash
# On the bastion: bring running apprentices in line with openclaw.json without recreating them
# (recreating a sandbox empties its audit log). Sets the settings that changed after the sandboxes
# were made, then restarts OpenClaw's gateway inside each sandbox so they take effect.
#
#   mcp.sessionIdleTtlMs   close a conversation's MCP connection after two idle minutes; without
#                          it OpenClaw holds every one open and refuses the 257th conversation
#
# Sessions, pairings and the audit log survive: only the gateway process restarts. Idempotent.
# (The pattern is anchored: a plain "pkill -f openclaw-gateway" also matches this very shell.
# A gateway that holds hundreds of MCP connections takes its time to stop, or doesn't: after
# fifteen seconds it is killed.)
set -euo pipefail
TTL=${MCP_SESSION_IDLE_TTL_MS:-120000}
for NAME in $(openshell sandbox list | awk '$1 ~ /^apprentice(-[0-9]+)?$/ {print $1}'); do
  openshell sandbox exec -n "$NAME" --no-tty --timeout 180 -- sh -c "
    openclaw config set mcp.sessionIdleTtlMs $TTL >/dev/null &&
    openclaw config validate >/dev/null &&
    (pkill -f '^openclaw-gateway' || true) &&
    for i in \$(seq 1 15); do pgrep -f '^openclaw-gateway' >/dev/null || break; sleep 1; done &&
    (pkill -9 -f '^openclaw-gateway' && sleep 1 || true) &&
    sh ~/.openclaw/start-gateway.sh &&
    echo \"$NAME: mcp.sessionIdleTtlMs = \$(openclaw config get mcp.sessionIdleTtlMs 2>/dev/null | tail -1)\"" </dev/null
done
