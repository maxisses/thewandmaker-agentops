"""One way to call oc for all helper scripts: a short limit and three tries.

The cluster's API hangs now and then (17 November: "oc extract" sat for minutes, twice, and the
next call took a second). A helper that waits forever right before a talk is worse than one that
tries again.
"""
import subprocess
import time


def flagged(args, limit):
    """The time limit as an oc flag. In "oc exec ... -- command" it has to stand before the "--":
    behind it, it would be handed to the command."""
    i = args.index("--") if "--" in args else len(args)
    return args[:i] + [f"--request-timeout={limit}s"] + args[i:]


def oc_out(args, env=None, tries=3, limit=25):
    err = None
    for _ in range(tries):
        try:
            return subprocess.run(["oc", *flagged(list(args), limit)], capture_output=True, text=True,
                                  check=True, timeout=limit + 10, env=env).stdout
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            err = e
            time.sleep(3)
    raise SystemExit(f"oc {' '.join(args[:2])} failed {tries} times: "
                     + ((getattr(err, "stderr", "") or "").strip()[:120] or f"no answer in {limit + 10} seconds")
                     + "\nIs the login still good? make cluster-login")
