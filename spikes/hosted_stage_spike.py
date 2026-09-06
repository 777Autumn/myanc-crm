"""THROWAWAY, OFFLINE ONLY: fixed read/stage/result contract over existing CRM core.

No server, file handoff, marker, permission interception, CLI credentials or
process lifecycle. `connect` and `click` stand for trusted transport boundaries;
`call` is the ONLY model-facing boundary. This does NOT implement/authenticate IPC.
"""

from copy import deepcopy
from datetime import datetime
import secrets

from myanc_crm import core


class SpikeHost:
    def __init__(self, backend, ledger, config):
        self.backend, self.ledger, self.config = backend, ledger, config
        self.sessions = {}
        self.cards = {}

    def connect(self, trusted_principal):
        """Host-only fixture for authenticated Feishu session establishment."""
        core._actor_for_principal(trusted_principal, self.config)
        token = secrets.token_urlsafe(32)
        self.sessions[token] = deepcopy(trusted_principal)
        return token

    def call(self, token, command, payload, now):
        principal = self.sessions.get(token)
        if principal is None or principal["user_id"] not in self.config["allowed_actors"]:
            return {"status": "blocked", "code": "unauthenticated"}
        try:
            if command == "customer":
                core._only_keys(payload, {"customer_query"})
                query = core._required_text(payload.get("customer_query"), "customer_query", 256)
                matches, _ = core._resolve_customer(query, self.backend)
                views = [core._display_customer(row, self.backend) for row in matches]
                if len(matches) != 1:
                    return {
                        "status": "needs_selection" if matches else "not_found",
                        "candidates": views,
                    }
                row = self.backend.get_customer(matches[0]["record_id"])
                if row is None:
                    return {"status": "unavailable", "code": "customer_disappeared"}
                # ponytail: fixture-only list; production needs a bounded Base query,
                # not a scan or a public raw-API/SQL proxy.
                history = sorted(
                    (entry for entry in self.backend.followups.values()
                     if entry["customer_record_id"] == row["record_id"]),
                    key=lambda entry: datetime.fromisoformat(entry["occurred_at"]),
                    reverse=True,
                )
                return {
                    "status": "found", "read_at": now.isoformat(),
                    "customer": core._display_customer(row, self.backend),
                    "history": [core._display_followup(entry, self.backend) for entry in history[:10]],
                    "truncated": len(history) > 10,
                }
            if command == "stage":
                staged = core.stage_followup(payload, self.backend, self.ledger, self.config, token, now)
                if staged["status"] != "staged":
                    return staged
                approval = core.begin_approval(
                    {"change_id": staged["change_id"], "principal": principal},
                    self.backend, self.ledger, self.config, token, now,
                )
                if approval["status"] != "pending":
                    return approval
                try:
                    message_id = self.publish(approval)
                except Exception:
                    return {
                        "status": "unavailable", "code": "approval_delivery_failed",
                        "change_id": approval["change_id"], "approval_id": approval["approval_id"],
                    }
                bound = core.bind_approval_card(
                    {"approval_id": approval["approval_id"],
                     "principal": {**principal, "message_id": message_id}},
                    self.ledger, self.config,
                )
                if bound["status"] != "bound":
                    return bound
                result = {**approval, "card_message_id": message_id}
                self.cards[message_id] = deepcopy(result)
                return deepcopy(result)
            if command == "result":
                core._only_keys(payload, {"change_id"})
                change_id = core._opaque_id(payload.get("change_id"), "change_id", "chg_")
                approval = self.ledger.get_approval_for_change(change_id)
                if approval is None or not core._same_principal(approval["principal"], principal):
                    return {"status": "blocked", "code": "result_not_accessible"}
                state = approval["state"]
                if state == "pending" and now > datetime.fromisoformat(approval["expires_at"]):
                    state = "expired"
                return {
                    "status": state, "change_id": change_id,
                    "queried_at": now.isoformat(), "receipt": deepcopy(approval["receipt"]),
                    "card_bound": bool(approval["card_message_id"]),
                }
            return {"status": "blocked", "code": "unsupported_model_command"}
        except (TypeError, ValueError):
            return {"status": "blocked", "code": "invalid_request"}
        except Exception:
            # A stage/delivery failure may have persisted a draft. Never infer
            # either CRM success or a visible approval card from this error.
            return {"status": "unavailable", "code": "query_or_delivery_failed"}

    def publish(self, approval):
        """Fake Feishu delivery, returning a server-chosen message ID."""
        return "card-" + secrets.token_urlsafe(12)

    def click(self, approval_id, decision, trusted_callback, now):
        """Host-only path; not reachable through `call`, never accepts business fields."""
        claimed = core.claim_approval_decision(
            {"approval_id": approval_id, "decision": decision, "principal": trusted_callback},
            self.ledger, self.config, now,
        )
        if not claimed.get("execute"):
            return claimed
        result = core.execute_claimed_approval(
            {"approval_id": approval_id, "principal": trusted_callback},
            self.backend, self.ledger, self.config, now,
        )
        self.cards[trusted_callback["message_id"]] = deepcopy(result)
        return result
