"""sdk/core/interview.py — PHASE 0.1 interview handler (abstract I/O contract).

The interview protocol activates only for Level 2 tasks (ComplexityClassifier decides).
Three I/O modes are supported: Console, Callback, and PreSupplied.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class MissingAnswerError(Exception):
    """Raised when a required answer is not present in a PreSuppliedHandler."""


class InterviewHandler(ABC):
    """Abstract base for all interview I/O modes."""

    @abstractmethod
    def ask(self, question: str) -> str:
        """Present *question* to the user and return their answer."""
        ...

    def confirm(self, message: str) -> bool:
        """Ask a yes/no confirmation. Default implementation uses ask()."""
        answer = self.ask(f"{message} [y/N]").strip().lower()
        return answer in ("y", "yes")


class ConsoleHandler(InterviewHandler):
    """Interactive console I/O — used by CLI (`piv-oac run`)."""

    def ask(self, question: str) -> str:
        return input(f"\n[PIV/OAC] {question}\n> ").strip()


class CallbackHandler(InterviewHandler):
    """Custom UI integration — caller provides a callback function.

    The callback receives the question string and must return the answer string.

    Example:
        Session.init(provider="anthropic").run(
            objective="...",
            on_question=lambda q: my_ui.prompt(q)
        )
    """

    def __init__(self, callback) -> None:
        self._callback = callback

    def ask(self, question: str) -> str:
        result = self._callback(question)
        if not isinstance(result, str):
            raise TypeError(
                f"CallbackHandler: callback must return str, got {type(result).__name__}"
            )
        return result.strip()


class PreSuppliedHandler(InterviewHandler):
    """Programmatic mode — answers are provided upfront as a dict.

    Keys are question strings (exact match). Unknown questions raise MissingAnswerError
    unless a default is provided.

    Example:
        Session.init(provider="anthropic").run(
            objective="...",
            answers={"protected_endpoints": ["/api/users"], "refresh_tokens": True}
        )
    """

    def __init__(self, answers: dict, *, default: str | None = None) -> None:
        self._answers = {str(k): str(v) for k, v in answers.items()}
        self._default = default

    def ask(self, question: str) -> str:
        if question in self._answers:
            return self._answers[question]
        if self._default is not None:
            return self._default
        raise MissingAnswerError(
            f"No pre-supplied answer for question: '{question}'. "
            "Add it to the answers dict or provide a default."
        )


# ---------------------------------------------------------------------------
# Interview session (drives the Q&A loop)
# ---------------------------------------------------------------------------

class InterviewSession:
    """Manages a single PHASE 0.1 interview using a given handler.

    The Orchestrator provides the questions; InterviewSession collects answers.
    """

    def __init__(self, handler: InterviewHandler) -> None:
        self._handler = handler
        self._transcript: list[dict[str, str]] = []

    def ask(self, question: str) -> str:
        """Ask one question and record the Q&A pair."""
        answer = self._handler.ask(question)
        self._transcript.append({"question": question, "answer": answer})
        return answer

    def ask_all(self, questions: list[str]) -> dict[str, str]:
        """Ask multiple questions and return {question: answer} mapping."""
        return {q: self.ask(q) for q in questions}

    @property
    def transcript(self) -> list[dict[str, str]]:
        """Return the full Q&A transcript (immutable view)."""
        return list(self._transcript)


# ---------------------------------------------------------------------------
# Standard PIV/OAC question set (PHASE 0.1 — Level 2 tasks only)
# ---------------------------------------------------------------------------

# Ordered list of (answer_key, question_text, required).
# Optional questions: empty answer is accepted and key is omitted from result.
_STANDARD_QUESTIONS: list[tuple[str, str, bool]] = [
    (
        "scope",
        "What must be delivered? Describe the main components or features "
        "(comma-separated or one per line).",
        True,
    ),
    (
        "acceptance_criteria",
        "How will we know this is done? List acceptance criteria "
        "(comma-separated or one per line).",
        True,
    ),
    (
        "constraints",
        "Are there any technical constraints? (e.g. must use library X, "
        "no breaking changes to API) — press Enter to skip.",
        False,
    ),
    (
        "out_of_scope",
        "What is explicitly excluded from this task? — press Enter to skip.",
        False,
    ),
]


def run_interview(
    objective: str,
    handler: InterviewHandler,
) -> dict[str, str]:
    """Run the standard PHASE 0.1 interview and return collected answers.

    Args:
        objective: The user's raw objective — prepended to context.
        handler:   I/O handler (Console, Callback, or PreSupplied).

    Returns:
        dict with keys: objective, scope, acceptance_criteria,
        and optionally: constraints, out_of_scope.
        Required keys are always present; optional keys only if non-empty.
    """
    session = InterviewSession(handler)
    answers: dict[str, str] = {"objective": objective}

    for key, question, required in _STANDARD_QUESTIONS:
        # Try short key first (programmatic callers pass {scope: "...", ...}).
        # Fall back to full question text (ConsoleHandler / CallbackHandler path).
        try:
            answer = handler.ask(key).strip()
        except MissingAnswerError:
            answer = session.ask(question).strip()

        if answer:
            answers[key] = answer
        elif required:
            # Required field left blank — use objective as fallback
            answers[key] = objective

    return answers
