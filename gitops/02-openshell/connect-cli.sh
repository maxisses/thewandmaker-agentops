#!/usr/bin/env bash
# On the bastion: point the openshell CLI at the gateway on the cluster.
# Needs a logged-in oc (cluster-admin password in ~/.olli/cluster-admin, see docs/build-journal.md).
set -euo pipefail
NS=openshell
GW=${OPENSHELL_GATEWAY_NAME:-olli}
oc whoami >/dev/null 2>&1 || oc login "${ROSA_API_URL:?}" -u cluster-admin -p "$(cat ~/.olli/cluster-admin)" >/dev/null
HOST=$(oc get route openshell -n "$NS" -o jsonpath='{.spec.host}')
DIR=$HOME/.config/openshell/gateways/$GW
# The mTLS bundle has to be in place before "gateway add".
( umask 077; mkdir -p "$DIR/mtls"
  for k in ca.crt tls.crt tls.key; do
    oc -n "$NS" get secret openshell-client-tls -o jsonpath="{.data.${k//./\\.}}" | base64 -d > "$DIR/mtls/$k"
  done )
openshell gateway add "https://$HOST" --local --name "$GW" || true
openshell gateway select "$GW" >/dev/null 2>&1 || true
openshell status
