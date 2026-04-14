# skills/provider-routing.md — Provider Routing

## When to Load

When configuring or debugging tier assignments for agent operations.

## Routing Decision (Tier 1, deterministic)

```
Is operation deterministically resolvable?  → Tier 1 (no provider)
Is operation mechanical + local_model set?  → Tier 2 (Ollama)
Requires genuine reasoning?                 → Tier 3 (cloud)
```

## Tier Assignment by Agent Level

| Agent Level | Without local_model | With local_model |
|---|---|---|
| L0 MasterOrchestrator | Tier 3 | Tier 3 (complexity requires cloud) |
| L1 Control agents | Tier 3 | Tier 3 (reasoning + veto authority) |
| L1.5 DomainOrchestrator | Tier 3 | Tier 2 (structured plan) |
| L2 SpecialistAgent | Tier 3 | Tier 2 (mechanical code) |
| Tier 1 operations | No LLM | No LLM |

## Tier 2 Fallback

If Ollama is unreachable (TCP probe fails):
→ ProviderRouter.get_provider(TIER2) returns cloud provider
→ No error, no user notification
→ Session continues normally on Tier 3

## Provider Initialization

```python
Session.init(
    provider="anthropic",      # cloud (Tier 3)
    local_model="llama3.2:1b"  # Tier 2 (optional)
)

Session.init(
    provider="ollama",         # fully local (no cloud)
    model="llama3.2:3b"
)
```

## Model Size Guide (Tier 2)

| Machine | Recommended model | RAM |
|---|---|---|
| Limited (< 4GB free) | `llama3.2:1b` | ~800MB |
| Mid-range (4–8GB) | `llama3.2:3b` | ~2GB |
| Capable (> 8GB) | `qwen2.5:7b` | ~5GB |

## Credential Flow

Tier 3 credentials: `Vault.get_credential(provider)` → reads env var only.
Never stored on provider instance after `__init__`.
Never logged. Never echoed. Never in context.
