# Solution Architecture Requirements Template

Please describe the software solution you want to build. The TDA uses the information below to select optimal capabilities and technologies.

IMPORTANT: The five sections below are the essential information the agent needs to produce a first-pass design. The remainder of the file describes an explicit bypass to continue the design when answers are incomplete, default assumptions the agent will apply, and an iterative refinement process.

---

## Essential Information (provide these if you can)

1) Core Objective & Business Value
- Describe the primary goal and target users; include measurable success criteria (SLA / uptime target, p95/p99 latency goals, RTO/RPO if relevant).

2) Expected Workload & Scale
- Average and peak requests per second, concurrent users, traffic patterns (steady vs spiky), and whether the app is stateful or stateless.

3) Data Sensitivity & Integrity
- Types of data (PII, financial, public), durability and encryption requirements, retention and backup expectations.

4) Connectivity & Integration
- External systems, on-premise dependencies, partner APIs, required latencies or protocols, message/event integration needs.

5) Non-Functional Constraints
- Hard constraints: budget, latency, regulatory requirements, forbidden services or vendor lock-in concerns.

Example short answer (one paragraph): "A zone-redundant, highly available web app for B2B order intake; target 99.99% uptime, p95 < 200ms, avg 100 RPS, peak 1k RPS; stores invoices (PII) in an encrypted relational DB; integrates with on-prem SAP; budget $2k/mo."

---

## If you don't have all answers — Quick bypass: Continue with assumptions

If you prefer the agent to produce a solution now rather than answer every question, reply or select: `Continue with assumptions`.

When the user chooses this bypass the agent will:
- Use the provided Essential Information items as authoritative where present.
- Apply the Default Assumptions (below) for any missing items.
- Produce a first-pass design, clearly listing which assumptions were used and which items remain open.

### Default Assumptions (applied only when the user provides no value)
- Single primary region with 3 Availability Zones (zone-redundant).
- Stateless front-end/API services; persistent state kept in managed PaaS databases and blob storage.
- CI/CD via GitHub Actions; container images stored in Azure Container Registry (ACR).
- Observability: Application Insights + Log Analytics; default retention 90 days.
- Security: Entra ID + Managed Identity for service auth; WAF on Application Gateway; DB private endpoints.
- Baseline load assumption (if no scale info): 100 RPS average / 1,000 RPS peak.

The agent will flag any assumption that appears to contradict user-provided values.

---

## Iteration & Refinement Workflow

1) Initial Draft — Agent creates:
	- Executive summary (2–3 sentences)
	- Architecture sketch (Markdown + component list + simple ASCII/data-flow diagram)
	- Short deployment plan (3 immediate steps)
	- Open questions list (items the agent assumed or could not resolve), ranked by impact (High/Medium/Low)

2) Prioritized Clarification — User answers the highest-impact open questions.

3) Revised Design — Agent re-generates the architecture and highlights deltas from the prior draft.

4) Finalization — Agent can produce an IaC skeleton (Bicep/Terraform), CI/CD snippets, and an operations checklist when the design stabilizes.

Each iteration is lightweight — the agent updates the design and shows a concise diff of changes.

---

## Short-Term Outline (what you get immediately after Continue)

- Executive summary and rationale
- Proposed topology: ingress → compute → data stores → caches → monitoring
- Component list with recommended Azure services (or equivalents for other clouds)
- Data flow and security controls
- Rough cost/scale notes and top 3 risks with mitigations
- Open questions for the next iteration

---

## Suggested prompt for the agent UI (paste into the intake box)

```
User: "Baseline highly available zone-redundant web application"

Essential inputs (paste if available):
- Core objective & business value: ...
- Expected workload & scale: ...
- Data sensitivity & integrity: ...
- Connectivity & integration: ...
- Non-functional constraints: ...

If any essentials are missing, the agent may proceed with defaults. To force the agent to continue now use: Continue with assumptions

Task: Produce an initial architecture draft (summary, architecture_markdown, deployment_plan, open_questions, cost_notes, security_controls). Also return a one-page human-friendly markdown.
```

---

## How to iterate

- After the initial draft, answer the high-impact open questions the agent lists and reply `Iterate`.
- The agent will produce a new draft and a short diff explaining what changed.

---

If you'd like, I can now produce a first-pass design for the example you gave: "Baseline highly available zone-redundant web application". Reply `Continue with assumptions` and I'll generate the draft immediately (and include the open questions). 

