#!/usr/bin/env bash
# Chapter 2: traces from the apprentice into MLflow.
#   MLflow (OpenShift AI)  <- OTLP <- collector "otel-collector" <- OTLP <- OpenClaw (diagnostics-otel)
# Needs: gitops/12-mlflow applied and ready, namespace ollivanders (gitops/20-shop).
# After this: "make up-shop" (shop-front reads the scroll) and "make up-apprentice" (spans on).
set -euo pipefail
cd "$(dirname "$0")"

oc apply -f 00-access.yaml
oc wait --for=condition=Available mlflow/mlflow --timeout=300s

# The experiment, created through the OpenShift AI gateway with our own login.
UI=$(oc get mlflow mlflow -o jsonpath='{.status.url}')
EXP=$(UI="$UI" TOKEN="$(oc whoami -t)" python3 - <<'EOF'
import json, os, urllib.request, urllib.error
ui, tok = os.environ["UI"], os.environ["TOKEN"]
h = {"Authorization": "Bearer " + tok, "X-MLflow-Workspace": "ollivanders", "Content-Type": "application/json"}
def call(path, body=None):
    req = urllib.request.Request(ui + path, data=json.dumps(body).encode() if body else None, headers=h,
                                 method="POST" if body else "GET")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())
try:
    print(call("/api/2.0/mlflow/experiments/get-by-name?experiment_name=apprentice")["experiment"]["experiment_id"])
except urllib.error.HTTPError as e:
    if e.code != 404:
        raise
    print(call("/api/2.0/mlflow/experiments/create", {"name": "apprentice"})["experiment_id"])
EOF
)
echo "MLflow experiment 'apprentice' in workspace 'ollivanders': id $EXP"
oc create configmap scribe -n ollivanders --from-literal=experiment_id="$EXP" --from-literal=mlflow_ui="$UI" \
  --dry-run=client -o yaml | oc apply -f -
oc apply -f 10-collector.yaml
oc rollout restart deploy/otel-collector -n ollivanders
oc rollout status deploy/otel-collector -n ollivanders --timeout=180s
# shop-front reads the scroll with the scribe's token; restart it so it picks up the experiment.
oc rollout restart deploy/shop-front -n ollivanders 2>/dev/null || true
echo "Traces: $UI (workspace ollivanders, experiment apprentice)"
