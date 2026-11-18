#!/usr/bin/env bash
# The backup oracles' keys: OPENROUTER_API_KEY (the backup) and REDHATTMM_API_KEY (the second
# backup) from .env into the secret oracle-backup, which only the model gateway mounts
# (30-model-gateway.yaml). The keys go from .env to oc on stdin; they are never printed, never on a
# command line and never in git. Idempotent. A key that isn't in .env is left out, and that backup
# stays off; with neither, the secret is left alone and the model gateway runs with MaaS only.
set -euo pipefail
cd "$(dirname "$0")/../.."

if ! grep -qE '^(OPENROUTER|REDHATTMM)_API_KEY=..' .env; then
  echo "no OPENROUTER_API_KEY and no REDHATTMM_API_KEY in .env: the backup oracles stay off"
  exit 0
fi
python3 - <<'PY' | oc apply -f - >/dev/null
import base64, json
env = dict(l.rstrip("\n").split("=", 1) for l in open(".env") if "=" in l and not l.startswith("#"))
keys = {name: env.get(var, "").strip().strip('"').strip("'")
        for name, var in (("BACKUP_API_KEY", "OPENROUTER_API_KEY"), ("SPARE_API_KEY", "REDHATTMM_API_KEY"))}
print(json.dumps({"apiVersion": "v1", "kind": "Secret", "type": "Opaque",
                  "metadata": {"name": "oracle-backup", "namespace": "ollivanders",
                               "labels": {"app": "model-gateway"}},
                  "data": {k: base64.b64encode(v.encode()).decode() for k, v in keys.items() if v}}))
PY
echo "secret oracle-backup: ok"
