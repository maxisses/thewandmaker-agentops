#!/usr/bin/env bash
# OpenShell CLI 0.0.116 for a Linux box without root (our bastion): the static musl build from
# the GitHub release, checked against the release checksum file, into ~/.local/bin.
set -euo pipefail
V=v0.0.116
F=openshell-x86_64-unknown-linux-musl.tar.gz
URL=https://github.com/NVIDIA/OpenShell/releases/download/$V
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
cd "$T"
curl -fsSL --retry 3 -O "$URL/$F" -O "$URL/openshell-checksums-sha256.txt"
grep " \*\?$F\$" openshell-checksums-sha256.txt | sed 's/\*//' | sha256sum -c --quiet
mkdir -p "$HOME/.local/bin"
tar -xzf "$F"
install -m 0755 "$(find . -type f -name openshell | head -1)" "$HOME/.local/bin/openshell"
"$HOME/.local/bin/openshell" --version
