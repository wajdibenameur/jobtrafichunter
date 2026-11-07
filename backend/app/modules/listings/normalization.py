import hashlib
import json
import re


def fingerprint(
    title: str | None, company: str | None, city: str | None, description: str | None, url: str
) -> str:
    values = [
        re.sub(r"\s+", " ", value or "").strip().casefold()
        for value in (title, company, city, description)
    ]
    if not all(values[:2]):
        values.append(url)
    return hashlib.sha256(json.dumps(values, ensure_ascii=True).encode()).hexdigest()
