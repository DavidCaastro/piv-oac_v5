# PIV/OAC v5.0 — Ollama provider entrypoint (local inference, Tier 2/3)
# All instructions are in sys/. Read sys/_index.md before acting.
from sdk import Session

Session.init(provider="ollama").run()
