#!/usr/bin/env python3
"""Run a command with the project's .env loaded as data. Never prints values.
Usage: python3 scripts/withenv.py <command> [args...]"""
import os, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def load_env():
    env = {}
    for line in (ROOT / ".env").read_text().splitlines():
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", line.strip())
        if m:
            env[m.group(1)] = m.group(2)
    return env

def project_environment():
    e = load_env()
    env = dict(os.environ)
    for k in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION", "RHCS_CLIENT_ID", "RHCS_CLIENT_SECRET"):
        env[k] = e[k]
    env["AWS_DEFAULT_REGION"] = e["AWS_REGION"]
    for k in ("AWS_PROFILE", "AWS_SESSION_TOKEN"):
        env.pop(k, None)
    env["KUBECONFIG"] = str(ROOT / "local" / "kubeconfig")
    return env

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.exit(subprocess.call(sys.argv[1:], env=project_environment()))
