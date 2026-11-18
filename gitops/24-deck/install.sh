#!/usr/bin/env bash
# Serve the deck from the cluster: stage a copy of deck/ with the hosted live config, build the
# image on the cluster, deploy it behind an HTTPS route. Idempotent; run it again after any change
# to the deck (make up-deck). Nothing here names a cluster: every address is read from the one
# you are logged in to.
set -euo pipefail
cd "$(dirname "$0")/../.."

STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT
mkdir "$STAGE/site"
# Without the laptop's own live config: that one holds the desk key.
tar -C deck --exclude js/config.local.js --exclude .DS_Store \
  --exclude assets/img/scenes/src --exclude assets/video/intro-flat-first-cut.mp4 -cf - . | tar -C "$STAGE/site" -xf -
python3 scripts/deck-live.py --hosted "$STAGE/site/js/config.local.js"
if grep -rqF -f <(oc extract secret/shop-tokens -n ollivanders --keys=desk --to=-) "$STAGE/site"; then
  echo "the desk key is in the staged deck: not building" >&2; exit 1
fi
# Nor the deck's password: slide 1 sends what is typed to the shop, which holds it (secret deck-login).
if oc get secret deck-login -n ollivanders >/dev/null 2>&1 &&
   grep -rqF -f <(oc extract secret/deck-login -n ollivanders --keys=password --to=-) "$STAGE/site"; then
  echo "the deck password is in the staged deck: not building" >&2; exit 1
fi
cp gitops/24-deck/Dockerfile "$STAGE/Dockerfile"

oc apply -f gitops/24-deck/deck.yaml
oc start-build deck -n ollivanders --from-dir="$STAGE" --follow --wait >/dev/null
echo "deck image built"
oc rollout status deploy/deck -n ollivanders --timeout=300s
echo "Deck: https://$(oc get route deck -n ollivanders -o jsonpath='{.spec.host}')   (scripted for everyone)"
echo "Live: the same address, then the password on slide 1 (DECK_PASSWORD in .env; key L jumps to the field)"
