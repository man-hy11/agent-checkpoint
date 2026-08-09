"""Narrow, value-free classification of probable credentials."""

import re


_PRIVATE_KEY = re.compile(
    r"-----(?:BEGIN|END) (?:[A-Z0-9]+ )*PRIVATE KEY-----", re.IGNORECASE
)
_GITHUB_TOKEN = re.compile(r"\b(?:gh[pousr]_|github_pat_)", re.IGNORECASE)
_OPENAI_TOKEN = re.compile(r"\bsk-[A-Za-z0-9_-]{21,}(?![A-Za-z0-9_-])")
_AWS_ACCESS_KEY = re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")
_SENSITIVE_ASSIGNMENT = re.compile(
    r"(?im)(?<![\w-])[\"']?"
    r"(?P<name>api[_-]?key|token|secret|password)"
    r"[\"']?[ \t]*[:=](?P<spacing>[ \t]*)"
    r"(?P<value>\"[^\"\r\n]*\"|'[^'\r\n]*'|[^\s,\r\n]+)"
)
_SENSITIVE_OPTION = re.compile(
    r"(?im)(?<!\S)--(?P<name>api[_-]?key|token|secret|password)(?:=|[ \t]+)"
    r"(?P<value>\"[^\"\r\n]*\"|'[^'\r\n]*'|[^\s,\r\n]+)"
)

_ASSIGNMENT_KINDS = {
    "apikey": "API key",
    "api_key": "API key",
    "api-key": "API key",
    "token": "access token",
    "secret": "secret",
    "password": "password",
}
_PLACEHOLDER_WORDS = {
    "changeme",
    "dummy",
    "example",
    "none",
    "null",
    "placeholder",
    "redacted",
    "replace-me",
    "replace_me",
    "sample",
    "test",
}


def find_secret_kind(text: str) -> str | None:
    """Return a probable credential class without returning its candidate value."""
    if _PRIVATE_KEY.search(text):
        return "private key"
    if _GITHUB_TOKEN.search(text):
        return "access token"
    if _OPENAI_TOKEN.search(text):
        return "access token"
    if _AWS_ACCESS_KEY.search(text):
        return "AWS access key"

    for match in _SENSITIVE_OPTION.finditer(text):
        value = match.group("value").strip("\"'").strip()
        if not _is_placeholder(value):
            return _ASSIGNMENT_KINDS[match.group("name").lower()]

    for match in _SENSITIVE_ASSIGNMENT.finditer(text):
        raw_value = match.group("value")
        if raw_value.startswith("#") and match.group("spacing"):
            continue
        value = raw_value.strip("\"'").strip()
        if not _is_placeholder(value):
            return _ASSIGNMENT_KINDS[match.group("name").lower()]
    return None


def _is_placeholder(value: str) -> bool:
    if not value:
        return True
    normalized = value.casefold()
    if normalized in _PLACEHOLDER_WORDS:
        return True
    if (
        re.fullmatch(r"\$\{[A-Za-z_][A-Za-z0-9_]*\}", value) is not None
        or (normalized.startswith("{{") and normalized.endswith("}}"))
        or (normalized.startswith("<") and normalized.endswith(">"))
    ):
        return True
    if re.fullmatch(r"\$[A-Za-z_][A-Za-z0-9_]*", value) is not None:
        return True
    return re.fullmatch(r"[x*._-]+", normalized) is not None
