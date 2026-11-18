#!/usr/bin/env python3
"""Run Terraform for one stage with the project's credentials and an account guard.
Usage: python3 scripts/tf.py bootstrap|foundation|rosa <terraform arguments>
Refuses to run when the AWS keys in .env belong to another account than infra/context.json."""
import json, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from withenv import ROOT, project_environment

STAGES = ("bootstrap", "foundation", "rosa")

def main():
    if len(sys.argv) < 3 or sys.argv[1] not in STAGES:
        sys.exit(__doc__)
    stage, args = sys.argv[1], sys.argv[2:]
    ctx = json.loads((ROOT / "infra" / "context.json").read_text())
    env = project_environment()
    who = subprocess.run(["aws", "sts", "get-caller-identity", "--query", "Account", "--output", "text"], env=env, capture_output=True, text=True)
    if who.returncode or who.stdout.strip() != ctx["account_id"]:
        sys.exit("AWS account check failed: keys in .env do not match infra/context.json. Nothing was run.")
    env["TF_VAR_expected_account_id"] = ctx["account_id"]
    env["TF_VAR_region"] = ctx["region"]
    env["TF_VAR_project"] = ctx["project"]
    if stage == "foundation":
        env["TF_VAR_availability_zone"] = ctx["availability_zone"]
    if stage == "rosa":
        version_file = ROOT / "infra" / "rosa" / "VERSION"
        env["TF_VAR_openshift_version"] = version_file.read_text().strip()
        # The rhcs provider reads the Red Hat login from the local rosa/ocm login.
        for candidate in (Path.home() / "Library/Application Support/ocm/ocm.json", Path.home() / ".config/ocm/ocm.json"):
            if candidate.is_file():
                auth = json.loads(candidate.read_text())
                if auth.get("refresh_token"):
                    env["RHCS_TOKEN"] = auth["refresh_token"]
                    env["RHCS_CLIENT_ID"] = auth.get("client_id", "cloud-services")
                    env.pop("RHCS_CLIENT_SECRET", None)
                    break
    if args[0] == "init":
        (ROOT / "local").mkdir(exist_ok=True, mode=0o700)
        if stage == "bootstrap":
            args += ["-reconfigure", "-backend-config=path=" + str(ROOT / "local" / "bootstrap.tfstate")]
        else:
            bucket = ctx["project"] + "-tfstate-" + ctx["account_id"]
            args += ["-reconfigure", "-backend-config=bucket=" + bucket, "-backend-config=region=" + ctx["region"]]
    print("Account " + ctx["account_id"] + " verified. Stage: " + stage, flush=True)
    return subprocess.call(["terraform", *args], cwd=ROOT / "infra" / stage, env=env)

if __name__ == "__main__":
    sys.exit(main())
