#!/usr/bin/env python3
"""OpenShell's own interface, `openshell term`, in a Terminal window of its own (for slide 12).

OpenShell has no web page: its operator interface is a terminal UI. It lists the gateway and the
sandboxes; pick `apprentice`, press Enter, then `l` for the live log, where every request shows
up as an OCSF event, ALLOWED or DENIED, with the policy that decided it. The CLI and its client
certificate live on the bastion, so the window is an ssh session there.

  scripts/shell-ui.py          # or: make shell-ui

Reads the bastion's user and host from .env; prints nothing from it.
"""
import os
import subprocess

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
env = dict(l.rstrip("\n").split("=", 1) for l in open(os.path.join(ROOT, ".env")) if "=" in l and not l.startswith("#"))
target = f"{env['BASTION_USER']}@{env['BASTION_HOST']}"
cmd = f"ssh -t {target} 'bash -lc \"openshell term\"'"
script = f'tell application "Terminal"\n  do script "{cmd.replace(chr(34), chr(92) + chr(34))}"\n  activate\nend tell'
subprocess.run(["osascript", "-e", script], check=True, stdout=subprocess.DEVNULL)
print("OpenShell's terminal UI is open in a Terminal window: pick apprentice, Enter, then l for the live log.")
