---
capability: Database
technology: Azure Cosmos DB
category: Data Persistence
pros: 
  - Planet-scale high availability (99.999% SLA)
  - Multi-model NoSQL capability
  - Single-digit millisecond latency
cons: 
  - High cost for sustained, heavy workloads if not partitioned correctly
  - Complex RU (Request Unit) sizing model
when_to_use: Global distribution requirements, unpredictable traffic spikes, IoT telemetry storage.
when_not_to_use: Heavily relational schemas with deep JOIN queries, highly constrained budgets.
---

# Azure Cosmos DB Implementation

Cosmos DB is Microsoft's globally distributed, multi-model database service structured around NoSQL paradigms.

## Implementation Guidelines
1. **Partitioning**: The partition key is the most critical design decision. Always select a property that has a wide range of values and distributes requests evenly to avoid Hot Partitions.
2. **Consistency Levels**: Cosmos provides 5 consistency levels. Default to 'Session' consistency, which offers read-your-own-writes guarantees while preserving high availability and low latency. Provide 'Strong' consistency only when absolute transactional truth is required.
3. **Data Modeling**: Denormalize data whenever possible. Given the lack of JOINs, fetching a single document containing embedded arrays is vastly more performant and cost-effective than fetching multiple relationship records.
4. **Vector Search Extension**: If acting as part of an RAG agent pipeline, utilize Cosmos's newly integrated Vector Search functionality to store embeddings adjacent to the raw JSON document payloads.
