# Research: what the platform really offers, matched against the story

Checked on 13 November 2026. Status labels: **read** means we read it in a primary source (Red Hat or
NVIDIA documentation), **reported** means a secondary source says so, **open** means nobody has
checked it yet. Nothing in here has been installed or run.

## The short version

The story holds. Every chapter has at least one Red Hat or ecosystem component that does what the
story needs, and three findings make the story better than we planned:

1. **The master's approval exists as a feature.** The OGX agent (formerly Llama Stack) has
   human-in-the-loop approval for tool calls: configured tools pause until a human approves or
   rejects them through the Responses API. That's the locked cabinet.
2. **The smuggled note has its own test engine.** MiDojo injects attack payloads into tool responses
   and grades the agent on getting the job done and on resisting the attack. That's the red-team
   case for indirect prompt injection.
3. **The release gate exists.** EvalHub has pass/fail thresholds and a side-by-side comparison of two
   evaluation runs in the OpenShift AI dashboard. That's version A against version B.

The weak spot is maturity. OpenShell and the OpenClaw starter kit are Developer Preview with
upstream artifacts, and we don't know yet whether OpenShift AI 3.5 installs on OpenShift 5.

## Platform baseline

| Item | Finding | Status |
|---|---|---|
| OpenShift 5 | Generally available since 9 November 2026, announced at KubeCon NA. Kubernetes 1.36. In-place update from 4.22. | read |
| OpenShift AI | 3.5 is the current release line. The old demo ran 3.5.2. | read |
| OpenShift AI 3.5 on OpenShift 5 | Not confirmed. The llm-d component table lists OpenShift 4.20+ for 3.5. | open |
| OpenShift 5 on AWS | Whether ROSA already offers 5.0, or only the self-managed installer does. | open |

## Chapter 1, contain: can I limit what it can do?

| Story element | Technology | Maturity | Status |
|---|---|---|---|
| A boundary around the apprentice | OpenShell in OpenShift AI 3.5: Helm deployment, mTLS, isolated sandboxes, controlled network egress. Guide in the agent-ops GitHub repository. Each agent runs as a pod; the dashboard lists OpenShell-managed Sandbox resources. | Developer Preview, upstream artifacts, not for production | read |
| Deny by default | OpenShell network policy pairs endpoints (host, port, optionally HTTP method and path) with the binaries allowed to reach them. No match means the proxy denies the connection with `policy_denied`. Network policy is hot-reloadable; filesystem (Landlock) and process rules are fixed at creation. | upstream | read |
| A badge instead of keys | OpenShell providers: the agent process only sees opaque placeholder tokens, and the proxy injects the real credential on the way out. For model calls a privacy router strips whatever the sandbox sends and injects the backend credential. | upstream. The `inference.local` host name is changing between versions, so check the version we install. | read |
| The badge itself | Kagenti `AgentRuntime` resource: injects an AuthBridge proxy for inbound JWT validation and outbound token exchange, plus SPIFFE workload identity. | Developer Preview since 3.4 | read |
| The apprentice | OpenClaw agent starter kit: Kustomize manifests or installer, models through the OGX inference gateway, traces to MLflow through the diagnostics-otel plugin, OAuth proxy in front. | Developer Preview since 3.5 EA2 | read |
| Tools only through the gateway | MCP gateway Operator (part of Red Hat Connectivity Link, installed separately) and the MCP Lifecycle Operator. | Technology Preview | read |
| The master's approval | Human-in-the-loop in the OGX agent: chosen tool calls pause until approved or rejected through the Responses API. OpenShell also has an operator approval flow for policy changes in its terminal UI; agents can't approve their own requests. | Developer Preview (OGX). Whether the OpenClaw path can use it is open. | read, fit open |
| The tryout room | Red Hat build of Agent Sandbox on OpenShift 5: short-lived, VM-isolated environments on Kata containers, with pre-provisioned warm pools and a sandbox router. | Technology Preview | read |
| Two walls | Red Hat describes running an OpenShell sandbox inside a Kata pod: OpenShell filters what leaves, Kata isolates the kernel. | blog, July 2026 | read |

## Chapter 2, see: can I see what it did?

| Story element | Technology | Maturity | Status |
|---|---|---|---|
| The day's scroll | MLflow Operator is a managed component of OpenShift AI. Traces show a span per model call and tool call with timings and payloads. | Generally available since 3.4 | read |
| Traces from the apprentice | The OpenClaw starter kit sends model calls, tool executions and context assembly as OpenTelemetry spans to MLflow. | Developer Preview | read |
| Trace view inside the product | Gen AI Studio embeds the MLflow trace UI with a call tree across models, MCP servers, knowledge sources and guardrails. | Technology Preview | read |
| Every allow and deny | OpenShell OCSF JSON export, one record per line, filterable with `select(.action == "Denied")`. | upstream | read |

One correction to the slide we took the four questions from: the OpenShell documentation calls OCSF
collection best-effort and says it's not a guarantee of complete audit history. So "an audit record
for every allow and deny" is a goal to test, and we shouldn't say it as a promise.

## Chapter 3, trust: can I trust it to ship?

| Story element | Technology | Maturity | Status |
|---|---|---|---|
| The rules | NeMo Guardrails through the `NemoGuardrails` resource (TrustyAI operator), configuration in a ConfigMap, input and output rails. The older FMS orchestrator is marked legacy. | Generally available since 3.4 | read (3.5 docs), GA claim reported |
| Rules on tool calls | NeMo Guardrails integration with the MCP gateway: guardrails on agent tool calls at the gateway, without touching the agent. | Technology Preview | read |
| Red teaming before every release | EvalHub with Garak as a built-in provider, next to LM Evaluation Harness, RAGAS and GuideLLM. A guided evaluation UI in the dashboard. | Technology Preview | read |
| The smuggled note | MiDojo: man-in-the-middle testing at the tool layer, declarative YAML scenarios, grades utility and security, records the full tool trace. | Developer Preview | read |
| The gate | EvalHub thresholds: pass or fail when submitting an evaluation run. | Technology Preview | read |
| Version A against version B | EvalHub side-by-side comparison of completed runs in an embedded MLflow view. | Technology Preview | read |

So the answer to "is red teaming in OpenShift AI by now?" is yes, as a preview: you start it from
the dashboard or with one API call, and the results land in MLflow.

## Chapter 4, scale: can it handle the Hogwarts rush?

| Story element | Technology | Maturity | Status |
|---|---|---|---|
| The rented oracle, governed | Models-as-a-Service external models: an `ExternalModel` resource puts third-party providers behind the same gateway, with token tracking and rate limits. Native provider APIs pass through unchanged. | Technology Preview | read |
| The model moves into the cellar | Distributed Inference with llm-d (llm-d 0.9, vLLM 0.24). | Generally available in 3.5 | reported |
| A fair turn for everyone | Models-as-a-Service is generally available since 3.4; multi-tenancy and showback are previews. | mixed | read |
| A thousand apprentices | OpenClaw Enterprise: an open control plane for persistent agents, announced 29 September 2026 by the OpenClaw Foundation with Red Hat and NVIDIA. Pilot stage, no Red Hat product yet. | upstream, early | read |

This fits the story better than expected: the model gateway is the same on day one (rented oracle)
and on the day of the rush (pool in the cellar). The apprentice never notices the move.

## What changes in the story

| Where | Before | Now |
|---|---|---|
| Chapter 1, approval | Our own approval service | Shown as a paused tool call that the master approves or rejects. Built on OGX human-in-the-loop if it fits, on our own shop API if it doesn't. |
| Chapter 2, audit | "Every allow and deny" | "Every deny we could find", and we say that collection is best-effort. |
| Chapter 3, red teaming | Garak only | Garak for what the apprentice says, MiDojo for the note smuggled into a tool response. |
| Chapter 3, fix | A dashboard tour | Five lines of rail configuration, then the EvalHub comparison of version A and B. |
| Chapter 4 | Told only | Still told, but with one true sentence: the gateway stays, the model behind it moves. |
| Wrap-up | Slide with product names | Each of the four answers gets its maturity label. |

## Open before we build the real thing

1. Does OpenShift AI 3.5 install on OpenShift 5, and is 5.0 available on AWS the way we need it?
2. Can the OpenClaw starter kit run inside an OpenShell sandbox on OpenShift today, or do we pick
   one of the two for the live part?
3. Does human-in-the-loop work on the OpenClaw path, or only for the OGX agent?
4. Do MiDojo and Garak accept our own scenarios quickly enough for a two-day build?
5. Which external model do we use, and what are its rate limits for 100 phones?

## Sources

- [OpenShift AI 3.5 release notes, Developer Preview features](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/release_notes/developer-preview-features_relnotes)
- [OpenShift AI 3.5 release notes, Technology Preview features](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/release_notes/technology-preview-features_relnotes)
- [Enabling AI safety with NeMo Guardrails, OpenShift AI 3.5](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/enabling_ai_safety_with_guardrails/enabling-ai-safety-with-nemo-guardrails_nemo-guardrails)
- [Evaluate LLMs with EvalHub, OpenShift AI 3.5](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/evaluating_ai_systems/evaluating-llms-with-evalhub_evaluate)
- [Test model safety with automated risk assessment, OpenShift AI 3.5](https://docs.redhat.com/en/documentation/red_hat_openshift_ai_self-managed/3.5/html/evaluating_ai_systems/test-model-safety-with-automated-risk-assessment_evaluate)
- [Distributed Inference with llm-d: release components](https://access.redhat.com/articles/7136620)
- [What's new in Red Hat OpenShift 5 for developers](https://developers.redhat.com/articles/2026/11/09/red-hat-openshift-5-for-developers)
- [Announcing Red Hat OpenShift 5](https://www.redhat.com/en/blog/announcing-red-hat-openshift-5)
- [Layered sandboxing for AI agents: OpenShift and OpenShell](https://developers.redhat.com/articles/2026/07/16/layered-sandboxing-ai-agents-openshift-and-openshell)
- [Red Hat AI and OpenShell](https://www.redhat.com/en/blog/red-hat-ai-and-openshell-driving-security-enhanced-agent-execution-for-enterprise-ai)
- [Why Red Hat is building an open foundation for enterprise agents with OpenClaw Enterprise](https://www.redhat.com/en/blog/why-red-hat-building-open-foundation-enterprise-agents-openclaw-enterprise)
- [How AI observability works with MLflow](https://developers.redhat.com/articles/2026/08/26/how-ai-observability-works-mlflow)
- [MCP gateway for Red Hat OpenShift, Technology Preview](https://www.redhat.com/en/blog/control-your-ai-agent-traffic-scale-model-context-protocol-gateway-red-hat-openshift-now-technology-preview)
- [OpenShell policy schema](https://docs.nvidia.com/openshell/reference/policy-schema)
- [OpenShell: manage providers and credentials](https://docs.nvidia.com/openshell/sandboxes/manage-providers)
- [OpenShell: OCSF JSON export](https://docs.nvidia.com/openshell/observability/ocsf-json-export)
- [OpenShell security best practices](https://docs.nvidia.com/openshell/latest/security/best-practices)
