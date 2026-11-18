#!/usr/bin/env bash
# Chapter 3: the apprentice's rails (NeMo Guardrails from OpenShift AI) in the model path.
# Needs: OpenShift AI with trustyai Managed (gitops/11-openshift-ai), namespace ollivanders.
# The rails call the model themselves (topic check, translation), so they get the MaaS key as a
# secret; it is read from .env and never printed.
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$(cd ../.. && pwd)

python3 - "$ROOT/.env" <<'EOF' | oc apply -f - >/dev/null
import base64, json, sys
env = {}
for line in open(sys.argv[1]):
    if "=" in line and not line.lstrip().startswith("#"):
        k, v = line.rstrip("\n").split("=", 1)
        env[k.strip()] = v.strip()
print(json.dumps({"apiVersion": "v1", "kind": "Secret", "type": "Opaque",
                  "metadata": {"name": "maas-key", "namespace": "ollivanders"},
                  "data": {"OPENAI_API_KEY": base64.b64encode(env["modelkey"].encode()).decode()}}))
EOF
echo "secret maas-key: ok"

for rel in 1.5 1.5.1; do
  cm="rails-${rel//./-}"
  oc create configmap "$cm" -n ollivanders --from-file=config.yaml=rails/config.yaml \
    --from-file=actions.py=rails/actions.py --from-file=rails.co="rails/rails-$rel.co" \
    --dry-run=client -o yaml | oc apply -f -
done
bash "$ROOT/scripts/wait-for.sh" crd nemoguardrails.trustyai.opendatahub.io
oc apply -f nemo.yaml
# Config maps are read at start: restart so a changed rail is picked up.
oc rollout restart deploy/rails -n ollivanders 2>/dev/null || true
for i in $(seq 1 60); do
  oc rollout status deploy/rails -n ollivanders --timeout=10s >/dev/null 2>&1 && break
  sleep 5
done
oc get pods -n ollivanders -l app=rails 2>/dev/null || oc get pods -n ollivanders | grep rails
