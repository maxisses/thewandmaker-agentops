#!/usr/bin/env python3
"""Check what the build needs before you run it ("make preflight"). Read-only.

It changes nothing: not on this machine, not on the cluster, not on the bastion. It never prints a
value from .env, only whether a name is there. Exit code 0 when nothing required is missing.

    python3 scripts/preflight.py            # everything
    python3 scripts/preflight.py --local    # only this machine and .env (no cluster, no bastion)

Lines start with ok, MISSING (the build stops without it), warn (works, but read the line) or
skip (could not be checked, and why).
"""
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KUBECONFIG = os.path.join(ROOT, "local", "kubeconfig")
OCENV = dict(os.environ, KUBECONFIG=KUBECONFIG)

missing, warnings = [], []


def line(state, what, how=""):
    print(f"  {state:<8}{what}" + (f"  ->  {how}" if how and state != "ok" else ""))
    if state == "MISSING":
        missing.append(what)
    elif state == "warn":
        warnings.append(what)


def head(title):
    print(f"\n{title}")


def run(cmd, env=None, timeout=30, stdin=None):
    try:
        r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=timeout, input=stdin)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, "", str(e)


def oc(*args, timeout=30):
    return run(["oc", *args], env=OCENV, timeout=timeout)


def oc_json(*args):
    code, out, _ = oc(*args, "-o", "json")
    try:
        return json.loads(out) if code == 0 else None
    except ValueError:
        return None


def load_env():
    env = {}
    path = os.path.join(ROOT, ".env")
    if not os.path.isfile(path):
        return None
    for raw in open(path):
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", raw.strip())
        if m:
            env[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return env


# ---- this machine ---------------------------------------------------------------------------
TOOLS = [
    # name, required, what needs it
    ("oc", True, "every make target on the cluster"),
    ("helm", True, "make up-openshell (OpenShell's chart from ghcr.io)"),
    ("python3", True, "all scripts (standard library only)"),
    ("bash", True, "the install scripts in gitops/"),
    ("make", True, "the build order"),
    ("ssh", True, "everything that runs on the bastion"),
    ("scp", True, "copies scripts to the bastion"),
    ("openssl", True, "make up-shop creates the shop's tokens"),
    ("git", False, "make vendor (only for a local OpenShell CLI)"),
    ("openshell", False, "optional on this machine; the build uses the one on the bastion"),
    ("terraform", False, "only make up (your own ROSA cluster)"),
    ("aws", False, "only make up and make status"),
    ("rosa", False, "only make login / link-account / up; the bastion needs its own"),
    ("node", False, "only make captures (with puppeteer-core and Chrome)"),
    ("ffmpeg", False, "only make film"),
    ("zip", False, "only make deck-zip"),
]


def check_tools():
    head("This machine")
    for name, required, why in TOOLS:
        if shutil.which(name):
            line("ok", name)
        else:
            line("MISSING" if required else "warn", name, why)
    if sys.version_info < (3, 9):
        line("MISSING", "python3 3.9 or newer", f"this is {sys.version.split()[0]}")
    code, out, _ = run(["oc", "version", "--client", "-o", "json"])
    try:
        v = json.loads(out)["clientVersion"]["gitVersion"] if code == 0 else ""
        v = json.loads(out).get("releaseClientVersion") or v
        if v:
            line("ok", f"oc client {v} (we built with 4.21 against a 4.22 cluster)")
    except (ValueError, KeyError):
        pass


# ---- .env -----------------------------------------------------------------------------------
REQUIRED = [
    ("ROSA_API_URL", "API URL of the cluster"),
    ("BASTION_HOST", "host with rosa, oc and (after make bastion-cli) openshell"),
    ("BASTION_USER", "ssh user on that host"),
    ("model", "main model's name"),
    ("modelendpoint", "main model's OpenAI-compatible endpoint"),
    ("modelkey", "main model's API key"),
]
OPTIONAL = [
    ("OPENROUTER_API_KEY", "backup oracle; answers first in the default mode backup-first (paid)"),
    ("REDHATTMM_BASE_URL", "second backup endpoint"),
    ("REDHATTMM_MODEL", "second backup's model"),
    ("REDHATTMM_API_KEY", "second backup's key"),
    ("DECK_PASSWORD", "password door of the hosted live deck"),
]
OWN_CLUSTER = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION", "RHCS_CLIENT_ID", "RHCS_CLIENT_SECRET"]


def check_env():
    head(".env (names only, no values are read out)")
    env = load_env()
    if env is None:
        line("MISSING", ".env", "cp .env.example .env and fill it in")
        return {}
    for name, why in REQUIRED:
        line("ok" if env.get(name) else "MISSING", name, why)
    for name, why in OPTIONAL:
        line("ok" if env.get(name) else "warn", name, "not set: " + why)
    spare = [bool(env.get(k)) for k in ("REDHATTMM_BASE_URL", "REDHATTMM_MODEL", "REDHATTMM_API_KEY")]
    if any(spare) and not all(spare):
        line("warn", "REDHATTMM_*", "set all three or none")
    if env.get("ROSA_API_URL") and not re.match(r"^https://[^/]+", env["ROSA_API_URL"]):
        line("warn", "ROSA_API_URL", "should look like https://api.<cluster>.<domain>:443")
    if env.get("modelendpoint") and not re.match(r"^https?://", env["modelendpoint"]):
        line("warn", "modelendpoint", "should be a full URL ending in /v1 or /v1/chat/completions")
    have = [k for k in OWN_CLUSTER if env.get(k)]
    if len(have) == len(OWN_CLUSTER):
        line("ok", "AWS_* and RHCS_* (only make up needs them)")
    else:
        line("warn", "AWS_* / RHCS_*", "not complete: fine when the cluster already exists, make up needs all five")
    if not os.path.isfile(os.path.join(ROOT, "infra", "context.json")):
        line("warn", "infra/context.json", "only make up: copy infra/context.example.json and set your AWS account ID")
    return env


# ---- the cluster ----------------------------------------------------------------------------
OPERATORS = [
    # package, channel, what it is
    ("rhods-operator", "stable-3.5", "Red Hat OpenShift AI 3.5"),
    ("openshift-cert-manager-operator", "stable-v1", "cert-manager"),
    ("leader-worker-set", "stable-v1.0", "LeaderWorkerSet"),
    ("mcp-gateway", "preview", "MCP gateway (preview channel)"),
    ("agent-sandbox-operator", "preview-0.9", "Red Hat build of Agent Sandbox 0.9 (preview channel)"),
]
CRDS = [
    ("sandboxes.agents.x-k8s.io", "make up-agent-sandbox"),
    ("datascienceclusters.datasciencecluster.opendatahub.io", "make up-operators"),
    ("mcpgatewayextensions.mcp.kuadrant.io", "make up-operators"),
    ("mlflows.mlflow.opendatahub.io", "make up-openshift-ai"),
    ("nemoguardrails.trustyai.opendatahub.io", "make up-openshift-ai"),
]


def quantity(q, unit):
    """CPU in cores or memory in GiB from a Kubernetes quantity."""
    q = str(q)
    if unit == "cpu":
        return float(q[:-1]) / 1000 if q.endswith("m") else float(q)
    for suffix, factor in (("Ki", 1 / 1024 / 1024), ("Mi", 1 / 1024), ("Gi", 1), ("Ti", 1024)):
        if q.endswith(suffix):
            return float(q[:-2]) * factor
    return float(q) / 1024 ** 3


def check_cluster(env):
    head("The cluster (read-only)")
    if not shutil.which("oc"):
        line("skip", "cluster checks", "no oc")
        return
    if not os.path.isfile(KUBECONFIG):
        line("MISSING", "local/kubeconfig", "make up-access on a ROSA cluster with a bastion; "
             "elsewhere: KUBECONFIG=local/kubeconfig oc login <api> as a cluster-admin")
        return
    code, who, err = oc("whoami")
    if code:
        line("MISSING", "login to the cluster", "make cluster-login (tokens last 24 hours); oc said: " + err[:120])
        return
    line("ok", f"logged in as {who}")
    code, server, _ = oc("whoami", "--show-server")
    if env.get("ROSA_API_URL") and server and server.rstrip("/").split(":")[1] != env["ROSA_API_URL"].rstrip("/").split(":")[1]:
        line("warn", "local/kubeconfig points at another cluster than ROSA_API_URL in .env")
    code, out, _ = oc("auth", "can-i", "*", "*", "--all-namespaces")
    line("ok" if out == "yes" else "MISSING", "cluster-admin rights", "SCCs, operators and cluster roles need them")

    cv = oc_json("get", "clusterversion", "version")
    if cv:
        version = cv["status"]["desired"]["version"]
        m = re.match(r"(\d+)\.(\d+)", version)
        if m and (int(m.group(1)), int(m.group(2))) >= (4, 22):
            line("ok", f"OpenShift {version} (built on 4.22.21)")
        else:
            line("warn", f"OpenShift {version}", "built and tested on 4.22 only; the OpenShell SCC needs image volumes")
    infra = oc_json("get", "infrastructure", "cluster")
    if infra:
        st = infra.get("status", {})
        topo = st.get("controlPlaneTopology", "?")
        line("ok", f"platform {st.get('platform', '?')}, control plane {topo}"
             + (" (hosted, as ours: ROSA HCP)" if topo == "External" else " (ours was ROSA HCP; make up-access is ROSA only)"))

    nodes = oc_json("get", "nodes")
    if nodes:
        workers = [n for n in nodes["items"]
                   if "node-role.kubernetes.io/master" not in n["metadata"].get("labels", {})
                   and "node-role.kubernetes.io/control-plane" not in n["metadata"].get("labels", {})] or nodes["items"]
        cpu = sum(quantity(n["status"]["allocatable"]["cpu"], "cpu") for n in workers)
        mem = sum(quantity(n["status"]["allocatable"]["memory"], "mem") for n in workers)
        gpus = sum(int(n["status"]["allocatable"].get("nvidia.com/gpu", 0)) for n in workers)
        text = f"{len(workers)} worker nodes, {cpu:.0f} vCPU, {mem:.0f} GiB allocatable, {gpus} GPUs (none needed)"
        # ours: 2 x m6a.xlarge + 3 x m6a.2xlarge = 32 vCPU, 128 GiB
        if cpu >= 24 and mem >= 90:
            line("ok", text)
        else:
            line("warn", text, "we ran on 32 vCPU / 128 GiB (2 x m6a.xlarge + 3 x m6a.2xlarge); "
                 "make up-access adds the three big ones on ROSA")
    sc = oc_json("get", "storageclass")
    if sc is not None:
        default = [s["metadata"]["name"] for s in sc["items"]
                   if s["metadata"].get("annotations", {}).get("storageclass.kubernetes.io/is-default-class") == "true"]
        line("ok" if default else "MISSING", "default storage class" + (f" ({default[0]})" if default else ""),
             "MLflow asks for a 10Gi volume without naming a class")
    code, domain, _ = oc("get", "ingresses.config.openshift.io", "cluster", "-o", "jsonpath={.spec.domain}")
    if domain:
        line("ok", f"ingress domain {domain}")
        code, out, err = run(["python3", "-c", "import sys,urllib.request,urllib.error\n"
                              "try: urllib.request.urlopen('https://console-openshift-console.'+sys.argv[1], timeout=10)\n"
                              "except urllib.error.HTTPError: pass\n", domain], timeout=20)
        if code == 0:
            line("ok", "router certificate is trusted by this machine")
        else:
            line("warn", "router certificate", "this machine does not trust it (or the console is unreachable): phones "
                 "scanning the QR code and the deck's frames need a certificate browsers accept")
    reg = oc_json("get", "configs.imageregistry.operator.openshift.io", "cluster")
    if reg is not None:
        state = reg.get("spec", {}).get("managementState")
        line("ok" if state == "Managed" else "MISSING", f"internal image registry ({state})",
             "the shop, the deck and the sandbox image are built on the cluster")
    elif cv:
        # hosted control planes may hide the operator config; the registry service is the proof
        code, _, _ = oc("get", "svc", "image-registry", "-n", "openshift-image-registry")
        line("ok" if code == 0 else "MISSING", "internal image registry",
             "the shop, the deck and the sandbox image are built on the cluster")

    head("Operator catalog (redhat-operators) and what is installed")
    for package, channel, what in OPERATORS:
        pm = oc_json("get", "packagemanifest", package, "-n", "openshift-marketplace")
        channels = [c["name"] for c in (pm or {}).get("status", {}).get("channels", [])]
        if pm is None:
            line("MISSING", f"{package}: not in the catalog", what)
        elif channel not in channels:
            line("MISSING", f"{package}: no channel {channel}", f"{what}; the catalog has {', '.join(channels) or 'none'}")
        else:
            line("ok", f"{package}, channel {channel}")
    code, out, _ = oc("get", "crd", "-o", "name")
    have = set(x.split("/", 1)[-1] for x in out.split())
    for crd, target in CRDS:
        if crd in have:
            line("ok", f"installed: {crd}")
        else:
            print(f"  todo    {crd}  ->  arrives with {target}")
    for ns in ("ollivanders", "openshell", "olli-build"):
        code, _, _ = oc("get", "namespace", ns)
        print(f"  {'ok' if code == 0 else 'todo':<8}namespace {ns}" + ("" if code == 0 else "  ->  created by make up-platform"))


# ---- the bastion ----------------------------------------------------------------------------
def check_bastion(env):
    head("The bastion (read-only, over ssh)")
    if not (env.get("BASTION_HOST") and env.get("BASTION_USER")):
        line("skip", "bastion checks", "BASTION_HOST and BASTION_USER are not in .env")
        return
    target = f"{env['BASTION_USER']}@{env['BASTION_HOST']}"
    probe = ("export PATH=$HOME/.local/bin:$PATH\n"
             "for c in oc rosa openshell curl; do command -v $c >/dev/null && echo have:$c || echo no:$c; done\n"
             "oc whoami >/dev/null 2>&1 && echo have:oc-login || echo no:oc-login\n"
             "rosa whoami >/dev/null 2>&1 && echo have:rosa-login || echo no:rosa-login\n")
    code, out, err = run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", target, "bash -s"],
                         stdin=probe, timeout=60)
    if code and "have:" not in out:
        line("MISSING", "ssh to the bastion without a password prompt",
             "ssh-copy-id your key first; ssh said: " + (err.splitlines()[-1][:120] if err else "nothing"))
        return
    line("ok", "ssh to the bastion with a key")
    got = set(out.split())
    line("ok" if "have:oc" in got else "MISSING", "bastion: oc", "the sandbox scripts call oc there")
    line("ok" if "have:curl" in got else "MISSING", "bastion: curl", "installs the OpenShell CLI")
    line("ok" if "have:rosa" in got else "warn", "bastion: rosa",
         "make up-access needs it (cluster-admin, machine pool); without ROSA, skip that target")
    if "have:rosa" in got:
        line("ok" if "have:rosa-login" in got else "warn", "bastion: rosa is logged in", "rosa login on the bastion")
    line("ok" if "have:oc-login" in got else "warn", "bastion: oc is logged in", "make up-access does it; or oc login there yourself")
    if "have:openshell" in got:
        line("ok", "bastion: openshell CLI")
    else:
        print("  todo    bastion: openshell CLI  ->  arrives with make bastion-cli")


def main():
    local_only = "--local" in sys.argv
    print("Preflight for the digital apprentice's platform. Nothing is changed.")
    check_tools()
    env = check_env()
    if local_only:
        print("\n(--local: cluster and bastion not checked)")
    else:
        check_cluster(env)
        check_bastion(env)
    print()
    if missing:
        print(f"{len(missing)} missing, {len(warnings)} to read. Missing:")
        for m in missing:
            print(f"  - {m}")
        sys.exit(1)
    print(f"Nothing required is missing. {len(warnings)} warnings to read above.")


if __name__ == "__main__":
    main()
