from datetime import datetime, timedelta
from typing import Any

from app.shared.clock import utcnow


def verified_automation(
    legal_status: str, evidence: dict[str, Any], *, now: datetime | None = None
) -> bool:
    if legal_status != "PERMITTED":
        return False
    now = now or utcnow()
    required = (
        "api_url",
        "terms_url",
        "access_method",
        "allowed_usage",
        "rate_limit",
        "reviewer",
        "evidence",
    )
    if not all(isinstance(evidence.get(key), str) and evidence[key].strip() for key in required):
        return False
    if evidence.get("robots_allowed") is not True or evidence.get("access_confirmed") is not True:
        return False
    for key in ("robots_checked_at", "terms_reviewed_at"):
        try:
            checked = datetime.fromisoformat(str(evidence[key]))
            if checked.tzinfo is None or checked > now or now - checked >= timedelta(days=90):
                return False
        except (KeyError, ValueError, TypeError):
            return False
    return True
