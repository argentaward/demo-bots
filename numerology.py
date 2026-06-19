import re
from datetime import date


MASTER_NUMBERS = {11, 22, 33}


def _reduce(n: int) -> int:
    while n > 9 and n not in MASTER_NUMBERS:
        n = sum(int(d) for d in str(n))
    return n


def soul_number(day: int) -> int:
    return _reduce(day)


def destiny_number(day: int, month: int, year: int) -> int:
    digits = f"{day:02d}{month:02d}{year:04d}"
    return _reduce(sum(int(d) for d in digits))


def parse_date(text: str) -> tuple[int, int, int]:
    text = text.strip()
    match = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", text)
    if not match:
        raise ValueError("format")
    d, m, y = int(match.group(1)), int(match.group(2)), int(match.group(3))
    date(y, m, d)
    if not (1900 <= y <= 2015):
        raise ValueError("year_range")
    return d, m, y
