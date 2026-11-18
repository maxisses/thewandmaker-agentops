#!/usr/bin/env python3
"""Run a script from this repo on the bastion, where the openshell CLI lives.

    python3 scripts/on-bastion.py gitops/02-openshell/provider-maas.sh

The script is copied to ~/.olli/ and run there. Values from .env that the script needs
(MaaS key, endpoint, model) go over ssh's stdin as exports, so they never show up in a
command line, a log or this terminal.
"""
import os
import shlex
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_env():
    env = {}
    with open(os.path.join(ROOT, ".env")) as f:
        for line in f:
            line = line.rstrip("\n")
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    script, extra = sys.argv[1], sys.argv[2:]   # extra files are copied next to the script
    env = load_env()
    target = f"{env['BASTION_USER']}@{env['BASTION_HOST']}"
    subprocess.run(["ssh", "-o", "BatchMode=yes", target, "umask 077; mkdir -p ~/.olli"], check=True)
    subprocess.run(["scp", "-q", "-o", "BatchMode=yes"]
                   + [os.path.join(ROOT, p) for p in [script] + extra]
                   + [f"{target}:.olli/"], check=True)
    base = env["modelendpoint"].split("/chat/completions")[0]
    lines = [
        "export PATH=$HOME/.local/bin:$PATH NO_COLOR=1",
        "export ROSA_API_URL=" + shlex.quote(env["ROSA_API_URL"]),
        "export OPENAI_API_KEY=" + shlex.quote(env["modelkey"]),
        "export MAAS_BASE_URL=" + shlex.quote(base),
        "export MAAS_MODEL=" + shlex.quote(env["model"]),
        "export MODEL_GATEWAY_URL=" + shlex.quote(os.environ.get("MODEL_GATEWAY_URL",
                                                  "http://model-gateway.ollivanders.svc:8080/v1")),
    ] + [f"export {k}=" + shlex.quote(os.environ[k]) for k in ("APPRENTICE_NAME",) if os.environ.get(k)] + [
        "bash ~/.olli/" + shlex.quote(os.path.basename(script)),
    ]
    r = subprocess.run(["ssh", "-o", "BatchMode=yes", target, "bash -s"],
                       input="\n".join(lines) + "\n", text=True)
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
