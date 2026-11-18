#!/usr/bin/env bash
# Register Red Hat MaaS (OpenAI-compatible) as the model behind inference.local.
# Run where the openshell CLI is connected. Expects in the environment:
#   OPENAI_API_KEY  the MaaS key (read by the CLI from the environment, never on the command line)
#   MAAS_BASE_URL   e.g. https://maas-rhdp.apps.maas.redhatworkshops.io/v1
#   MAAS_MODEL      e.g. qwen38-27b
# The gateway keeps the key. Sandboxes only ever see https://inference.local.
#   MODEL_GATEWAY_URL  optional; if set, the route goes through our model-gateway
#                      (http://model-gateway.ollivanders.svc:8080/v1), which switches off
#                      Qwen's thinking phase and passes the key on to MaaS.
set -euo pipefail
: "${OPENAI_API_KEY:?}" "${MAAS_BASE_URL:?}" "${MAAS_MODEL:?}"
MAAS_BASE_URL=${MODEL_GATEWAY_URL:-$MAAS_BASE_URL}

if openshell provider get maas >/dev/null 2>&1; then
  openshell provider update maas --credential OPENAI_API_KEY --config "OPENAI_BASE_URL=${MAAS_BASE_URL}"
else
  openshell provider create --name maas --type openai --credential OPENAI_API_KEY \
    --config "OPENAI_BASE_URL=${MAAS_BASE_URL}"
fi
openshell inference set --provider maas --model "$MAAS_MODEL"
openshell inference get
