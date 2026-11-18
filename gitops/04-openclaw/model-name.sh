#!/usr/bin/env bash
# On the bastion: running apprentices ask for the model under a neutral name, "oracle", instead of
# "qwen38-27b". The apprentice's traces (MLflow) and his console show the name he asks for; behind
# the model gateway a different model may answer, so a model's own name there was wrong half the
# time. OpenShell's inference.local sets the real model on the way out (openshell inference set),
# so the name the apprentice uses is a label and nothing else.
#
#   bash model-name.sh                               # every apprentice
#   APPRENTICE_NAME=apprentice-3 bash model-name.sh  # one of them, to try it first
#
# The config is saved as openclaw.json.before-oracle first. If the config does not validate or the
# apprentice does not answer afterwards, the old config is put back. Only OpenClaw's gateway
# process restarts: sessions, pairings and the audit log survive. Idempotent.
set -euo pipefail
ID=${MODEL_LABEL:-oracle}
SHOWN=${MODEL_SHOWN:-Oracle, through the model gateway}
ONLY=${APPRENTICE_NAME:-}
RESTART='(pkill -f "^openclaw-gateway" || true); for i in $(seq 1 15); do pgrep -f "^openclaw-gateway" >/dev/null || break; sleep 1; done; (pkill -9 -f "^openclaw-gateway" && sleep 1 || true); sh ~/.openclaw/start-gateway.sh'
for NAME in $(openshell sandbox list | awk '$1 ~ /^apprentice(-[0-9]+)?$/ {print $1}'); do
  [ -z "$ONLY" ] || [ "$ONLY" = "$NAME" ] || continue
  openshell sandbox exec -n "$NAME" --no-tty --timeout 240 -- sh -c "
    cd ~/.openclaw
    [ -f openclaw.json.before-oracle ] || cp -p openclaw.json openclaw.json.before-oracle
    if openclaw config set 'models.providers.shop.models[0].id' '$ID' >/dev/null 2>&1 &&
       openclaw config set 'models.providers.shop.models[0].name' '$SHOWN' >/dev/null 2>&1 &&
       openclaw config set agents.defaults.model.primary 'shop/$ID' >/dev/null 2>&1 &&
       openclaw config validate >/dev/null 2>&1; then
      $RESTART >/dev/null 2>&1
      OUT=\$(openclaw agent --thinking off --json --session-id model-\$\$ --message '[customer: a walk-in] Good day. One sentence, please: which wood forgives a nervous beginner?' 2>/dev/null | tr -d '\n' | head -c 4000)
      if echo \"\$OUT\" | grep -q '\"text\"'; then
        echo \"$NAME: asks for \$(openclaw config get agents.defaults.model.primary 2>/dev/null | tail -1), and answers\"
        exit 0
      fi
      echo \"$NAME: no answer under the new name, putting the old config back\"
    else
      echo \"$NAME: the config did not take the new name, putting the old config back\"
    fi
    cp -p openclaw.json.before-oracle openclaw.json
    $RESTART >/dev/null 2>&1
    echo \"$NAME: old config is back\"
    exit 1" </dev/null || true
done
