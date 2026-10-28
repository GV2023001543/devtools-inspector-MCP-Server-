from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


_SECRET_KEY = re.compile(r"token|secret|password|passwd|authorization|api[-_]?key|cookie", re.I)
_BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*")
_ASSIGNMENT = re.compile(
    r"(?i)\b(api[-_]?key|access[-_]?token|refresh[-_]?token|token|password|secret|authorization)"
    r"\s*[:=]\s*(['\"]?)[^\s,;'\"]+"
)


def redact_text(value: str, limit: int = 1000) -> str:
    value = _BEARER.sub("Bearer [REDACTED]", value)
    value = _ASSIGNMENT.sub(lambda match: f"{match.group(1)}=[REDACTED]", value)
    return value[:limit]


def redact_url(value: str) -> str:
    try:
        parts = urlsplit(value)
        if not parts.scheme or not parts.netloc:
            return redact_text(value, 2000)
        host = parts.hostname or ""
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        if parts.port:
            host = f"{host}:{parts.port}"
        query = urlencode(
            [(key, "[REDACTED]" if _SECRET_KEY.search(key) else item) for key, item in parse_qsl(parts.query, keep_blank_values=True)]
        )
        fragment = parts.fragment
        if "=" in fragment:
            fragment = urlencode(
                [(key, "[REDACTED]" if _SECRET_KEY.search(key) else item) for key, item in parse_qsl(fragment, keep_blank_values=True)]
            )
        else:
            fragment = redact_text(fragment, 500)
        return urlunsplit((parts.scheme, host, parts.path, query, fragment))[:2000]
    except ValueError:
        return redact_text(value, 2000)