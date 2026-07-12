import re

# ISO 6346 letter values: A=10, then +1 each, skipping multiples of 11 (11, 22, 33).
_LETTER_VALUES = dict(zip(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    [10, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 23, 24,
     25, 26, 27, 28, 29, 30, 31, 32, 34, 35, 36, 37, 38],
))

_ID_RE = re.compile(r"[A-Z]{4}\d{7}")


def validate_iso6346(container_id: str) -> bool:
    """ISO 6346 container ID check-digit validation (4 letters + 6 digits + check digit)."""
    if not container_id or not _ID_RE.fullmatch(container_id):
        return False
    total = sum(
        (_LETTER_VALUES[ch] if ch.isalpha() else int(ch)) * (2 ** i)
        for i, ch in enumerate(container_id[:10])
    )
    return (total % 11) % 10 == int(container_id[10])
