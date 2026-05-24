# ADR-014: Non-OpenAI (Mistral) model stack; Anthropic deferred

## Status

Accepted

## Context and Problem Statement

The pilot used `gpt-5-mini` (intake + diagram) and `DeepSeek-V3.1` (composer). The maintainer's preferred model stack is Anthropic / Gemini / Mistral / open-source, and explicitly **not** OpenAI. We needed to choose models for three roles on the dedicated Foundry (see [ADR-013](ADR-013-dedicated-foundry.md)):

1. fast/cheap quick tasks (intake reviewer),
2. high-quality reasoning (architecture composer / diagram refine),
3. D2 diagram (DSL/code) generation.

Constraints discovered:
- **Gemini is not on Azure AI Foundry** (Google Vertex only) — out for the `AIProjectClient` path.
- **Anthropic Claude is in the Foundry catalog** (claude-sonnet-4-6, opus, haiku) — but it is served through the Anthropic Messages surface, not the OpenAI-compatible API that `AIProjectClient.get_openai_client()` returns. Deploying it also requires a Marketplace partner attestation (`modelProviderData`) accepted via the portal.
- **Mistral** models (Mistral-small, Mistral-Large-3, Codestral) are available and serve cleanly through the OpenAI-compatible client.

## Considered Options

- **Option A — All-Mistral (3 models).** mistral-small (fast), Mistral-Large-3 (reasoning), Codestral (D2). OpenAI-client compatible, single vendor, no extra integration.
- **Option B — Mistral + Claude-for-reasoning.** Use claude-sonnet-4-6 for the composer/refine role.
- **Option C — Keep gpt-5-mini + DeepSeek.** Against the no-OpenAI preference.

## Decision Outcome

Chosen: **Option A now, Option B deferred.**

`AGENT_MODELS` is set to:
- `intake_reviewer` → `mistral-small-2503`
- `architecture_composer` → `Mistral-Large-3`
- `diagram_studio` → `Codestral-2501`

`claude-sonnet-4-6` **is deployed** on the Foundry but intentionally unused by the app: wiring Claude requires a separate `AnthropicFoundry`/Messages client integration (it does not follow the OpenAI SDK surface the agents currently use). That integration is a future stage, captured here so the deployed Claude model is not mistaken for dead config.

### Positive Consequences

- Fully off OpenAI, honouring the maintainer's preference.
- Single, OpenAI-compatible client path — minimal code change (config only).
- Verified live: SP → Foundry → `mistral-small-2503` inference returns successfully.

### Negative Consequences

- Mistral-Large-3 is good but not best-in-class at reasoning vs. Claude Sonnet.
- A `claude-sonnet-4-6` deployment sits idle until the AnthropicFoundry client is added.

## Pros and Cons of the Options

### Option A — All-Mistral
- Good, because one client surface, no new dependency, immediate.
- Bad, because reasoning quality is a notch below Claude.

### Option B — Mistral + Claude
- Good, because best reasoning for the refine/compose role.
- Bad, because requires a separate Anthropic client integration and Marketplace attestation.

### Option C — Keep OpenAI
- Bad, because it contradicts the explicit no-OpenAI preference.
