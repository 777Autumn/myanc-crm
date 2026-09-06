"""Public interface for the host-approved CRM follow-up flow."""

from .core import (
    Backend,
    Ledger,
    apply_followup,
    begin_approval,
    bind_approval_card,
    claim_approval_decision,
    decide_approval,
    execute_claimed_approval,
    stage_followup,
)

__all__ = [
    "Backend",
    "Ledger",
    "apply_followup",
    "begin_approval",
    "bind_approval_card",
    "claim_approval_decision",
    "decide_approval",
    "execute_claimed_approval",
    "stage_followup",
]
