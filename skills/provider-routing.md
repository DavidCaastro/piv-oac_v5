# skills/provider-routing.md — Provider Routing

## When to Load

When configuring or debugging tier assignments for agent operations, or when
ProviderRouter needs explicit decision logic for an agent/task combination.

---

## Routing Decision Matrix

Intersection of Agent Level (rows) and Task Complexity (columns) as classified by
ComplexityClassifier in `sdk/core/classifier.py`.

| Agent Level | Complexity L0 (trivial) | Complexity L1 (moderate) | Complexity L2 (high) |
|---|---|---|---|
| L0 OrchestratorAgent | Tier 3 — anthropic/claude-opus-4-6 | Tier 3 — anthropic/claude-opus-4-6 | Tier 3 — anthropic/claude-opus-4-6 |
| L1 SpecializedAgent | Tier 1 if deterministic; else Tier 3 | Tier 2 if GPU+≤13B; else Tier 3 | Tier 3 — fast model ok |
| L1.5 Tool-AugmentedAgent | Tier 2 (structured plan, local) | Tier 2 preferred; Tier 3 fallback | Tier 3 — cloud required |
| L2 ExpertAgent | Tier 2 (mechanical code) | Tier 2 or Tier 3 (domain decides) | Tier 3 — expert cloud model |
| Tier 1 operations | No LLM — pure Python | N/A | N/A |

**Complexity levels** are emitted by `ComplexityClassifier.classify(task)`:
- `L0` — deterministic, rule-based, no ambiguity
- `L1` — moderate reasoning, moderate context
- `L2` — deep reasoning, long context, cross-domain synthesis

---

## Tier Assignment Rules

### Tier 1 — Deterministic (no LLM)

Conditions (ALL must be true):
- Complexity classifier returns `L0`
- Operation is expressible as pure Python logic or regex
- No free-text generation required
- Examples: StandardsAgent docstring checks, `.env.example` consistency scan,
  linting runs, arithmetic budget estimation

### Tier 2 — Local (Ollama)

Conditions (ALL must be true):
- Complexity classifier returns `L1`
- `available_gpu = True` (detected at session init)
- `model_size <= 13B` parameters
- `latency_ok = True` (task is not latency-critical)
- Ollama endpoint reachable (TCP probe passes)

### Tier 3 — Cloud (Anthropic / OpenAI / Gemini)

Conditions (ANY is sufficient):
- Complexity classifier returns `L2`
- `available_gpu = False`
- `model_size > 13B`
- `latency_critical = True` (need lowest latency SLA)
- Ollama TCP probe fails (auto-fallback from Tier 2)
- Task involves PII and Ollama is not the compliance-preferred provider

---

## Provider Configuration Profiles

```yaml
anthropic:
  default_model: claude-opus-4-6
  fast_model: claude-haiku-4-5-20251001
  max_tokens: 8192
  system_prompt_style: explicit_role
  strengths: [reasoning, code_review, long_context]

openai:
  default_model: gpt-4o
  fast_model: gpt-4o-mini
  max_tokens: 16384
  system_prompt_style: role_in_messages
  strengths: [function_calling, json_mode, vision]

ollama:
  default_model: qwen2.5-coder:32b
  fast_model: qwen2.5-coder:7b
  max_tokens: 4096
  system_prompt_style: explicit_role
  strengths: [privacy, offline, cost_zero]

gemini:
  default_model: gemini-2.0-flash-exp
  fast_model: gemini-2.0-flash
  max_tokens: 8192
  system_prompt_style: role_in_messages
  strengths: [multimodal, grounding, speed]
```

---

## Role-to-Model Mapping

| Agent Role | Recommended Provider | Model | Justification |
|---|---|---|---|
| OrchestratorAgent (L0) | anthropic | claude-opus-4-6 | Long-context reasoning, multi-step orchestration |
| SecurityAgent (L1) | anthropic | claude-haiku-4-5-20251001 | Speed + deterministic checklist validation |
| ExpertAgent (L2) | domain-dependent | see domain config | Matched to domain's primary provider preference |
| CoherenceAgent (L1) | any | fast_model of chosen provider | Coherence checks are fast and pattern-driven |
| AuditAgent (L1.5) | ollama | qwen2.5-coder:7b | Privacy-first; audit logs must not leave perimeter |
| StandardsAgent | Tier 1 | no LLM | Fully deterministic; docstring grep + regex |
| DocumentationAgent | anthropic or ollama | claude-opus-4-6 / qwen2.5-coder:32b | Cloud for architecture docs; local for API reference |

---

## Model Degradation Chain

When the primary provider or model fails (timeout, quota, HTTP 5xx), apply this
chain in order. Log every step with reason code.

```
1. claude-opus-4-6          → primary (Anthropic Tier 3)
2. claude-sonnet-4-6        → first fallback (same provider, lower cost)
3. claude-haiku-4-5-20251001→ second fallback (Anthropic fast tier)
4. gpt-4o                   → cross-provider fallback (OpenAI)
5. gpt-4o-mini              → OpenAI fast tier
6. ollama (local fallback)  → qwen2.5-coder:7b or configured local model
7. ESCALATION               → if all above fail: emit ESCALATION(PROVIDER_CHAIN_EXHAUSTED)
                               Halt session. Do not retry silently.
```

**CROSS_ALERT rule:** if the same agent triggers fallback 3 or more times within
a single session, emit `CROSS_ALERT(REPEATED_FALLBACK, agent_id, count)` and
include it in the session telemetry summary. Do not suppress.

---

## Security Constraints

**(A) PII and encryption:** never route a request containing PII to a cloud provider
unless `encryption_in_transit = verified` is confirmed in the provider's config.
If unverified, route to Ollama or reject with `SECURITY_BLOCK(PII_UNENCRYPTED)`.

**(B) Vault-first credential:** credentials must be present in `Vault` before any
provider is initialized. No lazy credential loading. If `Vault.get_credential(provider)`
raises `CredentialNotFound`, abort init and emit `ESCALATION(MISSING_CREDENTIAL)`.
Never fall back to environment variable scanning at runtime outside of `vault.py`.

**(C) Audit every provider switch:** each time ProviderRouter switches provider
(including fallback), write a structured audit log entry:
```json
{ "event": "PROVIDER_SWITCH", "from": "<prev>", "to": "<next>",
  "reason": "<reason_code>", "agent_id": "<id>", "ts": "<iso8601>" }
```

**(D) HIPAA/HIGH compliance scope:** when session compliance scope is `HIPAA` or
`HIGH`, Ollama is the mandatory provider. Cloud providers are prohibited regardless
of model capability or latency requirements. Enforce at `ProviderRouter.get_provider()`.

---

## Quality Tuning Notes

**(A) Small models (≤7B):** inject explicit format instructions at the top of the
user message. Include a one-shot example of the exact output format expected.
Do not rely on implicit instruction following.

**(B) Anthropic models:** place role and persona in the `system` field, not in the
first `user` message. The `explicit_role` style (see config profiles) outperforms
`role_in_messages` for instruction adherence on Claude.

**(C) OpenAI models:** use JSON mode (`response_format: { type: "json_object" }`)
for any structured output task. It is more reliable than asking for JSON in the prompt.
Enable `function_calling` for tool-use tasks instead of text-parsed outputs.

**(D) Ollama models:** set `temperature: 0.1` for deterministic/code tasks.
Set `temperature: 0.7` for creative or generative tasks. Default Ollama temperature
is 0.8 which is too high for structured code generation.

---

## Fallback

If Ollama is unreachable (TCP probe fails at session init):
- `ProviderRouter.get_provider(TIER2)` returns the configured cloud provider
- No error raised to user; session continues on Tier 3
- Fallback is logged: `{ "event": "TIER2_FALLBACK", "reason": "OLLAMA_UNREACHABLE" }`
- If this occurs 3+ times in the same session: emit `CROSS_ALERT(REPEATED_FALLBACK)`

If a cloud provider returns HTTP 429 (rate limit):
- Wait `retry_after` seconds if provided in response headers
- If no header: exponential backoff starting at 5s, max 3 retries
- After 3 failures: advance one step in the Model Degradation Chain

If all providers in the degradation chain are exhausted:
- Emit `ESCALATION(PROVIDER_CHAIN_EXHAUSTED)`
- Halt the current phase; do not proceed to next gate

---

## Credential Flow

Tier 3 credentials are read exclusively via `Vault.get_credential(provider)`,
which reads from the environment variable designated for that provider.
- Credentials are never stored on the provider instance after `__init__`
- Credentials are never logged, echoed, or inserted into context windows
- Credentials are never passed between agents; each agent initializes its own
  provider instance from Vault independently
- `vault.py` is the single source of truth; no other module may call `os.getenv`
  for provider API keys

```python
# Correct usage — always through Vault
from sdk.core.vault import Vault
credential = Vault.get_credential("anthropic")  # raises CredentialNotFound if missing

# Incorrect — never do this
import os
api_key = os.getenv("ANTHROPIC_API_KEY")  # bypasses Vault, violates security constraint
```

<!-- v5.1 — expanded from v4 audit -->
