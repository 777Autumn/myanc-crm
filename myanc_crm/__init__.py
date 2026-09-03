"""Public interface for the staged CRM follow-up flow."""

from .core import Backend, Ledger, apply_followup, stage_followup

__all__ = ["Backend", "Ledger", "apply_followup", "stage_followup"]
