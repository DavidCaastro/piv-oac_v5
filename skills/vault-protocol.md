# skills/vault-protocol.md — Vault Protocol

## When to Load

When handling credentials, managing API keys, or responding to VaultError.

## Three Vault Operations

```python
from sdk.vault import Vault

# 1. Injection scan (before every LLM call)
result = Vault.scan_for_injection(text)

# 2. Credential retrieval (provider initialization)
key = Vault.get_credential("anthropic")  # reads ANTHROPIC_API_KEY

# 3. Asset verification (skill loading)
digest = Vault.verify("skill-name", Path("skills/manifest.json"))
```

## Credential Sources

| Provider | Env var | Where set |
|---|---|---|
| Anthropic | `ANTHROPIC_API_KEY` | `.env` file or system env |
| OpenAI | `OPENAI_API_KEY` | `.env` file or system env |
| Ollama | None (local) | — |

`.env` is gitignored. Never committed. Never in context. Never logged.

## Zero-Hardcode Rule

No credential value appears in:
- Any Python source file
- Any markdown file
- Any log line
- Any PMIA message
- Any git commit

Violation = SecurityAgent CROSS_ALERT.

## MCP Vault Integration (advanced)

For organizations using MCP-managed secrets:
```python
# Credentials flow via MCP, never into agent context
# Vault.get_credential() reads from env var set by MCP runtime
# No SDK changes required — env var injection point is the same
```

## VaultError Response

```
VaultError raised (injection detected or missing credential):
  → Log: level=ERROR, action=vault_error
  → For injection: CROSS_ALERT to SecurityAgent
  → For missing credential: ESCALATION to MasterOrchestrator
  → Session paused until resolved
```

## Audit Trail

Every Vault.scan_for_injection() call is logged:
```json
{"action": "injection_scan", "outcome": "PASS", "tier": 1, "tokens_used": 0}
```
Even clean scans are logged — audit completeness requires it.
