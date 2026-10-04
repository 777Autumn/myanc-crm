"""Bounded CRM reads, with identity resolved only from the authenticated host."""

import re
from datetime import datetime, timedelta, timezone

from . import core
from .customers import STAGES
from .connections import ConnectionBlocked


BEIJING = timezone(timedelta(hours=8))
CUSTOMER_FIELDS = frozenset({"keyword", "owner", "owner_ref", "stages", "due",
                             "date_from", "date_to", "offset"})


def _offset(value):
    if type(value) is not int or not 0 <= value <= 2**31 - 1:
        raise ValueError("offset must be a nonnegative integer")
    return value


def _boundary(value, name):
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        moment = datetime.fromisoformat(value).replace(tzinfo=BEIJING)
        if name == "date_to":
            moment += timedelta(days=1)
        return moment
    return core._parse_time(value, name).astimezone(BEIJING)


def customers(request, backend, ledger, config, principal, now=None):
    """Read 20 customers; next_request freezes relative dates for later pages."""
    try:
        principal = core._principal(principal)
        actor = core._actor_for_principal(principal, config)
        request = core._mapping(request, "request")
        core._only_keys(request, CUSTOMER_FIELDS)
        moment = core._now(now)
        offset = _offset(request.get("offset", 0))
        keyword = None
        if "keyword" in request:
            keyword = core._required_text(request["keyword"], "keyword", 200)
        owner = request.get("owner", "me")
        if owner not in ("me", "all") or ("owner_ref" in request and "owner" in request):
            raise ValueError("use owner me/all or one verified owner_ref")
        stages = request.get("stages", [])
        if (not isinstance(stages, list) or len(stages) > len(STAGES)
                or any(not isinstance(stage, str) or stage not in STAGES for stage in stages)):
            raise ValueError("stages must contain configured stage names")
        due = request.get("due")
        if due not in (None, "today", "overdue", "unscheduled"):
            raise ValueError("due must be today, overdue or unscheduled")
        if due and ("date_from" in request or "date_to" in request):
            raise ValueError("use due or an explicit date range")
        lower = _boundary(request["date_from"], "date_from") if "date_from" in request else None
        upper = _boundary(request["date_to"], "date_to") if "date_to" in request else None
        if due == "today":
            upper = moment.astimezone(BEIJING).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        elif due == "overdue":
            upper = moment.astimezone(BEIJING)
        if lower and upper and lower >= upper:
            raise ValueError("date_from must precede date_to")
        if offset and due in ("today", "overdue"):
            raise ValueError("follow the returned next_request to preserve the date boundary")
        owner_id = actor["feishu_user_id"] if owner == "me" else None
        if "owner_ref" in request:
            ref = core._required_text(request["owner_ref"], "owner_ref", 132)
            person = ledger.get_assignee(ref, principal)
            if person is None:
                raise ValueError("owner_ref is not verified for this conversation")
            current = backend.get_assignee(person["id"])
            if current is None or current.get("id") != person["id"] or current.get("name") != person["name"]:
                raise ValueError("the verified owner changed; resolve again")
            owner_id = person["id"]
        query = {"offset": offset, "stages": list(dict.fromkeys(stages))}
        if "owner_ref" in request:
            query["owner_ref"] = request["owner_ref"]
        else:
            query["owner"] = owner
        if keyword is not None:
            query["keyword"] = keyword
        if lower:
            query["date_from"] = lower.isoformat()
        if upper:
            query["date_to"] = upper.isoformat()
        if due == "unscheduled":
            query["due"] = due
    except ConnectionBlocked:
        raise
    except (ValueError, TypeError, OverflowError) as exc:
        return core._blocked("invalid_customers_request", str(exc))
    except Exception:
        return {"status": "unavailable", "code": "owner_lookup_failed"}
    try:
        page = backend.list_customers(keyword=keyword, owner_id=owner_id, stages=query["stages"],
                                      date_from=query.get("date_from"), date_to=query.get("date_to"),
                                      unscheduled=due == "unscheduled", offset=offset, limit=20)
        rows = _page(page, 20)
        for row in rows:
            core._validate_customer(row)
        # ponytail: offset pages are live views; use a snapshot only if concurrent-edit consistency is required.
        return {"status": "found", "customers": [core._display_customer(row, backend) for row in rows],
                "has_more": page["has_more"], "query": query, "read_at": core._iso(moment),
                "next_request": {**query, "offset": offset + len(rows)} if page["has_more"] else None}
    except ConnectionBlocked:
        raise
    except Exception:
        return {"status": "unavailable", "code": "customers_read_failed"}


def _page(page, limit):
    page = core._mapping(page, "query page")
    rows = page.get("items")
    if (not isinstance(rows, list) or len(rows) > limit or type(page.get("has_more")) is not bool
            or (page["has_more"] and not rows)):
        raise ValueError("invalid bounded query page")
    return rows


def customer_history(record_id, backend, offset=0):
    """Read one history page only after the caller has resolved its customer."""
    try:
        offset = _offset(offset)
        page = backend.read_customer_history_page(record_id, offset=offset, limit=10)
        rows = _page(page, 10)
        if any(row.get("customer_record_id") != record_id for row in rows):
            raise ValueError("history contains another customer")
        for row in rows:
            core._parse_time(row.get("occurred_at"), "occurred_at")
        return {"history_status": "available", "history": [core._display_followup(row, backend) for row in rows],
                "has_more": page["has_more"], "truncated": page["has_more"],
                "next_offset": offset + len(rows) if page["has_more"] else None}
    except ConnectionBlocked:
        raise
    except Exception:
        return {"history_status": "unavailable", "history": None}
