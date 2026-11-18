#!/usr/bin/env bash
# Install OpenShell 0.0.116 (Red Hat images) on the current cluster and connect the local CLI.
# Idempotent: run it again after a change. Needs KUBECONFIG pointing at the cluster.
set -euo pipefail
cd "$(dirname "$0")"

VERSION=0.0.116
NS=openshell
GW_NAME=${OPENSHELL_GATEWAY_NAME:-olli}
SCC=${OPENSHELL_SCC:-openshell-sandbox-minimum-required}

oc apply -f 00-namespace-scc.yaml
if [[ "$SCC" == privileged ]]; then
  echo "Fallback: granting the privileged SCC to openshell-sandbox"
  oc adm policy add-scc-to-user privileged -z openshell-sandbox -n "$NS"
fi

DOMAIN=$(oc get ingresses.config.openshift.io cluster -o jsonpath='{.spec.domain}')
ROUTE_HOST="openshell-${NS}.${DOMAIN}"

helm upgrade --install openshell oci://ghcr.io/nvidia/openshell/helm-chart \
  --version "$VERSION" --namespace "$NS" \
  -f values.yaml \
  --set "pkiInitJob.serverDnsNames[0]=${ROUTE_HOST}" \
  --wait --timeout 10m

oc create route passthrough openshell --service=openshell --port=8080 \
  --hostname="$ROUTE_HOST" -n "$NS" --dry-run=client -o yaml | oc apply -f -

# Local CLI: register the gateway and drop the mTLS client bundle where the CLI looks for it.
if command -v openshell >/dev/null; then
  DIR="$HOME/.config/openshell/gateways/${GW_NAME}"
  # The bundle has to be in place before "gateway add", or the add fails.
  ( umask 077; mkdir -p "$DIR/mtls"
    for k in ca.crt tls.crt tls.key; do
      oc -n "$NS" get secret openshell-client-tls -o jsonpath="{.data.${k//./\\.}}" | base64 -d > "$DIR/mtls/$k"
    done )
  openshell gateway add "https://${ROUTE_HOST}" --local --name "$GW_NAME" || true
  openshell status || true
else
  echo "openshell CLI not found. Run vendor/agent-ops/scripts/install-openshell-cli.sh first."
fi
echo "Gateway: https://${ROUTE_HOST}"
