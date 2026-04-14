# PIV/OAC v5.0 — Anthropic provider entrypoint
# All instructions are in sys/. Read sys/_index.md before acting.
from sdk import Session

Session.init(provider="anthropic").run()
