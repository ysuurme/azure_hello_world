---
capability: Compute
technology: Azure Container Apps
category: Application Hosting
pros: 
  - Serverless Container execution (KEDA-driven auto-scaling to 0)
  - Native integration with Dapr
  - Built-in Envoy ingress and traffic splitting
cons: 
  - Less control than native AKS
  - Cold starts can impact latency sensitive workloads
when_to_use: Microservices, API backends, event-driven background workers.
when_not_to_use: Stateful legacy monoliths requiring deep OS access or specific DaemonSets.
---

# Azure Container Apps Implementation

Azure Container Apps (ACA) is a fully managed, serverless container environment built atop Azure Kubernetes Service (AKS), simplified for developers who lack the infrastructure overhead of managing clusters.

## Implementation Guidelines
1. **Network Boundaries**: Leverage internal environments (VNet integration) when hosting private backend logic. Expose only explicit Frontends via External Ingress.
2. **KEDA Autoscaling**: By default, define scaling rules based on HTTP traffic or metrics (like Azure Service Bus queue length). 
3. **Identities**: Bind a User-Assigned Managed Identity to the Container App profile to securely query secrets from KeyVault, preventing raw keys in environment variables.
4. **Resiliency**: If your agent must manage retries to downstream APIs (like AI Search or OpenAI), install Dapr Sidecars in your environment and leverage built-in resiliency policies instead of coding transient fault handling in Python.
