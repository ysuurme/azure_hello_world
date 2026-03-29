---
capability: Observability
technology: Prometheus
category: Metric Collection
pros: 
  - Open-source standard
  - Powerful PromQL query language
cons: 
  - Requires dedicated management layer
  - External storage needed for long-term retention
when_to_use: Kubernetes environments, high cardinality metric requirements.
when_not_to_use: Pure Azure PaaS/Serverless (Use Azure Monitor natively instead).
---

# Prometheus Metric Collection Implementation

Prometheus is an open-source systems monitoring and alerting toolkit. It records real-time metrics in a time series database built using an HTTP pull model.

## Implementation Guidelines
1. **Scraping Architecture**: Instead of pushing metrics, Prometheus regularly scrapes HTTP endpoints exposed by your microservices (typically at `/metrics`).
2. **Exporters**: Leverage standard exporters (e.g., node_exporter, redis_exporter) to translate third-party service telemetry into Prometheus format.
3. **Data Retention**: By default, local storage is ephemeral. For historical analysis, configure Remote Write to an external store like Thanos or Cortex.
4. **Agent Integration**: When deploying in Azure Container Apps, consider running the OpenTelemetry Collector as a sidecar or daemon to aggregate and forward to central Prometheus infrastructure.
