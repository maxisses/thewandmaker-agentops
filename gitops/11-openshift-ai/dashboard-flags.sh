#!/usr/bin/env bash
# OpenShift AI dashboard: the gen AI studio and its guardrails switches (Technology Preview in 3.5).
# They are off by default. On, the dashboard shows the gen AI studio's playground with two
# guardrail switches; it still has no page for our own NemoGuardrails resource (build journal,
# "The machinery moves into the deck"). Slide 18 shows the resource in the OpenShift console.
#
#   bash gitops/11-openshift-ai/dashboard-flags.sh on     # what the cluster has since 15 November
#   bash gitops/11-openshift-ai/dashboard-flags.sh off    # back to the default
set -euo pipefail
case "${1:-on}" in
  on) v=true ;;
  off) v=false ;;
  *) echo "usage: $0 on|off" >&2; exit 2 ;;
esac
oc patch odhdashboardconfig odh-dashboard-config -n redhat-ods-applications --type merge \
  -p "{\"spec\":{\"dashboardConfig\":{\"genAiStudio\":$v,\"guardrails\":$v}}}" >/dev/null
echo "dashboard flags genAiStudio and guardrails: $v"
