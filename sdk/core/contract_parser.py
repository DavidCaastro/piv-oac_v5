"""sdk/core/contract_parser.py — ContractParser: stateless helpers for LLM output parsing.

Centralises all regex-based parsing that was previously spread across session_async.py
module-level helpers. All methods are @staticmethod — no mutable state.

Also defines EvalScoreResult for structured evaluation scores.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field

from sdk.exceptions import MalformedOutput


@dataclass
class EvalScoreResult:
    """Structured result from EvaluationAgent scoring."""

    session_id: str
    expert_id: str
    phase: str
    scores: dict
    aggregate: float
    parse_error: bool = False
    timestamp_ms: int = field(default_factory=lambda: int(time.time() * 1000))

    def to_dict(self) -> dict:
        return {
            "session_id":   self.session_id,
            "expert_id":    self.expert_id,
            "phase":        self.phase,
            "scores":       self.scores,
            "aggregate":    self.aggregate,
            "parse_error":  self.parse_error,
            "timestamp_ms": self.timestamp_ms,
        }


class ContractParser:
    """Stateless contract output parser.

    All methods are class-level @staticmethod — safe to call from async contexts
    without instantiation.
    """

    _VERDICT_RE    = re.compile(r"GATE_VERDICT\s*:\s*(APPROVED|REJECTED)", re.I)
    _REJECTED_RE   = re.compile(r"^\s*REJECTED\b", re.I | re.M)
    _APPROVED_RE   = re.compile(r"^\s*APPROVED\b",  re.I | re.M)
    _RATIONALE_RE  = re.compile(
        r"GATE_VERDICT\s*:\s*(?:APPROVED|REJECTED)\s*[—\-]?\s*(.+?)(?:\n|$)", re.I
    )
    _JSON_FENCE_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
    _JSON_RAW_RE   = re.compile(
        r'(\{[^{}]*"scores"\s*:\s*\{[^{}]+\}[^{}]*\})', re.DOTALL
    )

    @staticmethod
    def parse_verdict(text: str) -> bool:
        """Parse APPROVED/REJECTED from agent LLM output. Default: REJECTED.

        Priority:
          1. GATE_VERDICT: APPROVED|REJECTED (explicit declaration)
          2. Standalone REJECTED line
          3. Standalone APPROVED line
          4. Ambiguity → False (security invariant)
        """
        m = ContractParser._VERDICT_RE.search(text)
        if m:
            return m.group(1).upper() == "APPROVED"
        if ContractParser._REJECTED_RE.search(text):
            return False
        if ContractParser._APPROVED_RE.search(text):
            return True
        return False  # ambiguity = REJECTED — security invariant

    @staticmethod
    def extract_rationale(text: str) -> str:
        """Extract inline rationale after GATE_VERDICT line (first 200 chars)."""
        m = ContractParser._RATIONALE_RE.search(text)
        if m:
            return m.group(1).strip()[:200]
        return text[:200].replace("\n", " ")

    @staticmethod
    def parse_eval_scores(
        text: str,
        expert_id: str,
        session_id: str,
    ) -> EvalScoreResult:
        """Extract JSON scores from EvaluationAgent output.

        Strategy:
          1. Look for ```json ... ``` fence block
          2. Fallback: regex for raw JSON object with key "scores"
          3. If nothing found: EvalScoreResult(parse_error=True, aggregate=0.0)

        Raises MalformedOutput only when a fence block exists but contains invalid JSON.
        """
        # 1. JSON fence
        m = ContractParser._JSON_FENCE_RE.search(text)
        if m:
            try:
                data = json.loads(m.group(1))
                return ContractParser._build_score_result(data, expert_id, session_id)
            except (ValueError, KeyError) as exc:
                raise MalformedOutput(
                    agent_id=expert_id,
                    expected="valid JSON in ```json``` fence",
                    got=m.group(1)[:200],
                ) from exc

        # 2. Raw JSON fallback (no fence)
        m2 = ContractParser._JSON_RAW_RE.search(text)
        if m2:
            try:
                data = json.loads(m2.group(1))
                return ContractParser._build_score_result(data, expert_id, session_id)
            except (ValueError, KeyError):
                pass

        # 3. Nothing parseable
        return EvalScoreResult(
            session_id=session_id,
            expert_id=expert_id,
            phase="PHASE_6",
            scores={},
            aggregate=0.0,
            parse_error=True,
        )

    @staticmethod
    def _build_score_result(
        data: dict,
        expert_id: str,
        session_id: str,
    ) -> EvalScoreResult:
        scores = data.get("scores", {})
        aggregate = round(
            scores.get("FUNC", 0) * 0.35
            + scores.get("SEC",  0) * 0.25
            + scores.get("QUAL", 0) * 0.20
            + scores.get("COH",  0) * 0.15
            + scores.get("FOOT", 0) * 0.05,
            3,
        )
        return EvalScoreResult(
            session_id=session_id,
            expert_id=expert_id,
            phase="PHASE_6",
            scores=scores,
            aggregate=aggregate,
        )
