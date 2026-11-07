import ipaddress
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_KEYS = {"trk", "trackingid", "ref", "refid", "source", "from", "fbclid", "gclid"}


def public_https_url(value: str) -> str:
    value = value.strip()
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").rstrip(".")
        if (
            parsed.scheme != "https"
            or not host
            or "." not in host
            or parsed.username
            or parsed.password
            or parsed.port not in {None, 443}
            or host.endswith((".localhost", ".local", ".internal"))
            or any(ord(char) < 33 for char in value)
            or "\\" in value
            or len(value) > 4096
        ):
            raise ValueError
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError
        host.encode("idna")
    except (ValueError, UnicodeError) as exc:
        raise ValueError("Use a public HTTPS URL without credentials or a custom port") from exc
    return value


def canonical_url(value: str) -> str:
    parsed = urlsplit(public_https_url(value))
    host = (parsed.hostname or "").encode("idna").decode().lower().rstrip(".")
    query = sorted(
        (key, val)
        for key, val in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.casefold().startswith("utm_") and key.casefold() not in TRACKING_KEYS
    )
    return urlunsplit(("https", host, parsed.path or "/", urlencode(query), ""))
