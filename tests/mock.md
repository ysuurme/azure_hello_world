1. Core Objective & Business Value
We are building a "Real-Time Fraud Detection & Payment Settlement" engine for a growing fintech. The application intercepts transactions between an e-commerce platform and banking gateways to perform pattern analysis. The primary goal is to reduce fraudulent chargebacks by 25% while providing a daily settlement dashboard for finance teams.

2. Expected Workload & Scale
The traffic profile is extremely spiky. Our steady baseline is approximately 500 requests per minute. However, we must handle massive bursts of up to 20,000 requests per minute during "Flash Sale" events and the holiday shopping season. The application is stateless, but fraud analysis requires a low-latency cache for temporary session scoring.

3. Data Sensitivity & Integrity
The system handles PCI-DSS compliant payment records and PII (Personally Identifiable Information). We require a 99.99% monthly availability SLA. All data must be synchronously replicated across at least three availability zones within the primary region to ensure zero data loss during a localized data center outage.

4. Connectivity & Integration
This engine must integrate with external banking APIs via mutual TLS (mTLS). It also requires a secure, high-speed connection back to an on-premise mainframe ledger. We prefer to avoid public internet routing for this connection and want to explore Private Link or VPN options.

5. Non-Functional Constraints
Cost: The monthly budget for the entire production environment is capped at $750/month.

Latency: The "Fraud Check" API call must return a decision in under 120ms to avoid disrupting the user checkout experience.

Deployment: The system must be fully containerized and support "Blue/Green" deployments to ensure zero-downtime updates.

Portability: Favor managed services that abstract infrastructure but allow us to move the containerized logic between Azure regions if necessary.

## Why this prompt tests the Agent effectively:
Cost vs. SLA: The $750/month budget is tight for a 99.99% SLA requiring zone redundancy. The agent will have to reason between expensive AKS clusters versus more cost-effective Azure Container Apps (ACA) that support "Scale-to-Zero".

Stateless vs. State: By mentioning "stateless logic" but a "low-latency cache," the agent should suggest Azure Cache for Redis or Cosmos DB with zonal redundancy.

Security Depth: The requirement for mTLS and private connectivity forces the agent to consider Application Gateway v2 with WAF and Azure Private Link, testing its knowledge of the WAF Security pillar.

Operational Excellence: The request for "Blue/Green" deployments tests the agent’s ability to recommend Azure Dev CLI (azd) or Terraform workflows for revision-based management .