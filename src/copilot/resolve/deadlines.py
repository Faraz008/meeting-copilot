import calendar
import re
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Literal

WD = {
    "monday": 0,
    "mon": 0,
    "tuesday": 1,
    "tues": 1,
    "tue": 1,
    "wednesday": 2,
    "wed": 2,
    "thursday": 3,
    "thurs": 3,
    "thu": 3,
    "friday": 4,
    "fri": 4,
    "saturday": 5,
    "sat": 5,
    "sunday": 6,
    "sun": 6,
}

WD_RE = (
    r"(monday|mon|tuesday|tues|tue|wednesday|wed|"
    r"thursday|thurs|thu|friday|fri|saturday|sat|"
    r"sunday|sun)"
)

MONTHS = {month.lower(): index for index, month in enumerate(calendar.month_name) if month}

MONTHS |= {month.lower(): index for index, month in enumerate(calendar.month_abbr) if month}

MONTHS["sept"] = 9

MON = "|".join(sorted(MONTHS, key=len, reverse=True))

NUM = {
    "a": 1,
    "an": 1,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}


@dataclass
class Resolution:
    resolved_date: date | None
    status: Literal["resolved", "ambiguous", "unresolvable"] = "resolved"
    rule: str = ""
    resolved_time: time | None = None
    options: list[date] = field(default_factory=list)


# ---- Date helpers ----


def _mk(y: int, m: int, d: int) -> date | None:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def add_months(d: date, n: int) -> date:
    y, m = divmod(d.year * 12 + d.month - 1 + n, 12)
    m += 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def end_of_month(d: date) -> date:
    last_day = calendar.monthrange(d.year, d.month)[1]
    return date(d.year, d.month, last_day)


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def next_occ(d: date, wd: int) -> date:
    days = (wd - d.weekday() - 1) % 7 + 1
    return d + timedelta(days=days)


def add_business_days(d: date, n: int) -> date:
    while n > 0:
        d += timedelta(days=1)

        if d.weekday() < 5:
            n -= 1

    return d


def _infer_year(
    month: int,
    day: int,
    base: date,
) -> date | None:
    d = _mk(base.year, month, day)

    if d and d < base:
        d = _mk(base.year + 1, month, day)

    return d


def _amb(
    primary: date,
    options: list[date],
    rule: str,
) -> Resolution:
    return Resolution(
        primary,
        "ambiguous",
        rule,
        options=sorted(set(options)),
    )


# ---- Date resolution rules ----


def r_iso(text: str, base: date, order: str) -> Resolution | None:
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)

    if m:
        d = _mk(int(m[1]), int(m[2]), int(m[3]))

        if d:
            return Resolution(d, "resolved", "iso")

        return Resolution(None, "unresolvable", "invalid_date")

    return None


def r_monthname(
    text: str,
    base: date,
    order: str,
) -> Resolution | None:
    pattern = (
        rf"\b(?:(\d{{1,2}})(?:st|nd|rd|th)?\s+"
        rf"(?:of\s+)?({MON})|({MON})\s+"
        rf"(\d{{1,2}})(?:st|nd|rd|th)?)"
        rf"\b(?:,?\s+(\d{{4}}))?"
    )

    m = re.search(pattern, text)

    if not m:
        return None

    day = int(m[1] or m[4])
    month = MONTHS[m[2] or m[3]]

    if m[5]:
        d = _mk(int(m[5]), month, day)
    else:
        d = _infer_year(month, day, base)

    if d:
        return Resolution(d, "resolved", "month_name")

    return Resolution(None, "unresolvable", "invalid_date")


def r_numeric(
    text: str,
    base: date,
    order: str,
) -> Resolution | None:
    m = re.search(
        r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b",
        text,
    )

    if not m:
        return None

    a, b = int(m[1]), int(m[2])

    if order == "DMY":
        pairs = [(a, b), (b, a)]
    else:
        pairs = [(b, a), (a, b)]

    year = None

    if m[3]:
        year = int(m[3])

        if year < 100:
            year += 2000

    out = []

    for day, month in pairs:
        if year:
            d = _mk(year, month, day)
        elif 1 <= month <= 12:
            d = _infer_year(month, day, base)
        else:
            d = None

        if d and d not in out:
            out.append(d)

    if not out:
        return Resolution(None, "unresolvable", "invalid_date")

    if len(out) == 1:
        return Resolution(out[0], "resolved", "numeric")

    return _amb(out[0], out, "numeric_ambiguous")


def r_in_n(
    text: str,
    base: date,
    order: str,
) -> Resolution | None:
    number_words = "|".join(NUM)

    pattern = (
        rf"\b(?:in\s+)?((?:a\s+)?couple(?:\s+of)?|"
        rf"\d+|{number_words})\s+"
        r"(business days?|working days?|days?|weeks?|months?)\b"
    )

    m = re.search(pattern, text)

    if not m:
        return None

    quantity = m[1]

    if "couple" in quantity:
        n = 2
    elif quantity.isdigit():
        n = int(quantity)
    else:
        n = NUM[quantity]

    unit = m[2]

    if unit.startswith(("business", "working")):
        return Resolution(
            add_business_days(base, n),
            "resolved",
            "in_n_business_days",
        )

    if unit.startswith("day"):
        return Resolution(
            base + timedelta(days=n),
            "resolved",
            "in_n_days",
        )

    if unit.startswith("week"):
        return Resolution(
            base + timedelta(weeks=n),
            "resolved",
            "in_n_weeks",
        )

    return Resolution(
        add_months(base, n),
        "resolved",
        "in_n_months",
    )


def r_relative_day(
    text: str,
    base: date,
    order: str,
) -> Resolution | None:
    if re.search(r"\bday after tomorrow\b", text):
        return Resolution(
            base + timedelta(days=2),
            "resolved",
            "day_after_tomorrow",
        )

    if re.search(r"\btomorrow\b", text):
        return Resolution(
            base + timedelta(days=1),
            "resolved",
            "tomorrow",
        )

    return None


def r_month_end(
    text: str,
    base: date,
    order: str,
) -> Resolution | None:
    m = re.search(rf"\bend of ({MON})\b", text)

    if not m:
        return None

    month = MONTHS[m[1]]
    d = end_of_month(date(base.year, month, 1))

    if d < base:
        d = end_of_month(date(base.year + 1, month, 1))

    return Resolution(d, "resolved", "end_of_named_month")


def r_end_of(
    text: str,
    base: date,
    order: str,
) -> Resolution | None:
    pattern = r"\bend of (?:the )?(this |next )?(week|month|quarter|year)\b"
    m = re.search(pattern, text)

    if m:
        modifier = (m[1] or "").strip()
        unit = m[2]
    else:
        m = re.search(r"\b(eow|eom|eoq|eoy)\b", text)

        if not m:
            return None

        shortcuts = {
            "eow": "week",
            "eom": "month",
            "eoq": "quarter",
            "eoy": "year",
        }

        modifier = ""
        unit = shortcuts[m[1]]

    nxt = modifier == "next"

    if unit == "week":
        days = 3 + (7 if nxt else 0)
        friday = week_start(base) + timedelta(days=days)

        if friday < base:
            friday += timedelta(days=7)

        return Resolution(friday, "resolved", "end_of_week")

    if unit == "month":
        month_base = base.replace(day=1)

        if nxt:
            month_base = add_months(month_base, 1)

        return Resolution(
            end_of_month(month_base),
            "resolved",
            "end_of_month",
        )

    if unit == "quarter":
        quarter_month = ((base.month - 1) // 3 + 1) * 3
        d = end_of_month(date(base.year, quarter_month, 1))

        if nxt:
            d = end_of_month(add_months(d.replace(day=1), 3))

        return Resolution(d, "resolved", "end_of_quarter")

    year = base.year + (1 if nxt else 0)

    return Resolution(
        date(year, 12, 31),
        "resolved",
        "end_of_year",
    )


def r_day_of_month(
    text: str,
    base: date,
    order: str,
) -> Resolution | None:
    m = re.search(
        r"\b(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)\b",
        text,
    )

    if not m:
        return None

    day = int(m[1])

    for k in range(13):
        month_date = add_months(base.replace(day=1), k)
        d = _mk(month_date.year, month_date.month, day)

        if d and d >= base:
            return Resolution(d, "resolved", "day_of_month")

    return Resolution(None, "unresolvable", "invalid_date")


def r_weekday(
    text: str,
    base: date,
    order: str,
) -> Resolution | None:
    m = re.search(
        rf"\b(this|next|coming|following)?\s*{WD_RE}\b",
        text,
    )

    if not m:
        return None

    modifier = m[1] or ""
    weekday = WD[m[2]]

    if re.search(r"\bnext week\b", text):
        d = week_start(base) + timedelta(days=7 + weekday)

        return Resolution(d, "resolved", "weekday_next_week")

    if modifier in ("next", "following"):
        a = next_occ(base, weekday)
        b = week_start(base) + timedelta(days=7 + weekday)

        if a == b:
            return Resolution(a, "resolved", "next_weekday")

        return _amb(b, [a, b], "next_weekday_ambiguous")

    if modifier == "this":
        d = week_start(base) + timedelta(days=weekday)

        if d >= base:
            return Resolution(d, "resolved", "this_weekday")

        return Resolution(
            next_occ(base, weekday),
            "resolved",
            "this_weekday_passed_rolls_forward",
        )

    a = next_occ(base, weekday)

    if base.weekday() == weekday:
        return _amb(a, [base, a], "bare_weekday_is_today")

    return Resolution(a, "resolved", "bare_weekday")


def r_week_month_bare(
    text: str,
    base: date,
    order: str,
) -> Resolution | None:
    m = re.search(r"\b(this|next) (week|month)\b", text)

    if not m:
        return None

    nxt = m[1] == "next"
    unit = m[2]

    if unit == "week":
        days = 4 + (7 if nxt else 0)
        friday = week_start(base) + timedelta(days=days)

        if not nxt:
            if friday < base:
                friday += timedelta(days=7)

            return Resolution(friday, "resolved", "this_week")

        next_monday = week_start(base) + timedelta(days=7)

        return _amb(
            friday,
            [next_monday, friday],
            "next_week_ambiguous",
        )

    if not nxt:
        return Resolution(
            end_of_month(base),
            "resolved",
            "this_month",
        )

    first = add_months(base.replace(day=1), 1)
    last = end_of_month(first)

    return _amb(
        last,
        [first, last],
        "next_month_ambiguous",
    )


def r_today(
    text: str,
    base: date,
    order: str,
) -> Resolution | None:
    pattern = (
        r"\b(today|tonight|eod|cob|close of business|"
        r"end of (the )?day|this (evening|afternoon|morning))\b"
    )

    if re.search(pattern, text):
        return Resolution(base, "resolved", "today")

    return None


# ---- Rule configuration ----

RULES = [
    r_iso,
    r_monthname,
    r_numeric,
    r_in_n,
    r_relative_day,
    r_month_end,
    r_end_of,
    r_day_of_month,
    r_weekday,
    r_week_month_bare,
    r_today,
]

EVENT = re.compile(
    r"\b(when|once|after|before|until|release|launch|"
    r"demo|sprint|approv\w*|ready|done)\b"
)

VAGUE = re.compile(
    r"\b(asap|soon|later|sometime|eventually|whenever|"
    r"at some point|a few|several)\b"
)


# ---- Text normalization ----


def _normalize(raw: str) -> str:
    text = raw.lower().replace("\u2019", "'")

    text = re.sub(r"[^\w\s/:\-']", " ", text)
    text = re.sub(r"(?<!\d)-|-(?!\d)", " ", text)

    return re.sub(r"\s+", " ", text).strip()


def _time_of_day(text: str) -> time | None:
    m = re.search(
        r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b",
        text,
    )

    if m and 1 <= int(m[1]) <= 12:
        hour = int(m[1]) % 12
        minute = int(m[2] or 0)

        if m[3] == "pm":
            hour += 12

        return time(hour, minute)

    if "noon" in text:
        return time(12, 0)

    pattern = r"\b(eod|cob|close of business|end of (the )?day)\b"

    if re.search(pattern, text):
        return time(17, 0)

    return None


# ---- Main resolver ----


def resolve_deadline(
    raw: str,
    base: date,
    date_order: str = "DMY",
) -> Resolution:
    text = _normalize(raw)
    resolved_time = _time_of_day(text)

    for rule in RULES:
        result = rule(text, base, date_order)

        if result:
            result.resolved_time = resolved_time if result.resolved_date else None
            return result

    if EVENT.search(text):
        return Resolution(
            None,
            "unresolvable",
            "event_relative",
        )

    if VAGUE.search(text):
        return Resolution(
            None,
            "unresolvable",
            "vague",
        )

    return Resolution(
        None,
        "unresolvable",
        "unrecognized",
    )


# ---- Naive baseline parser ----


def resolve_deadline_naive(
    raw: str,
    base: date,
    date_order: str = "DMY",
) -> Resolution:
    """Off-the-shelf parser used as the later Week ablation baseline."""

    import dateparser

    settings = {
        "RELATIVE_BASE": datetime.combine(base, time()),
        "PREFER_DATES_FROM": "future",
    }

    dt = dateparser.parse(raw, settings=settings)

    if dt:
        return Resolution(
            dt.date(),
            "resolved",
            "dateparser",
        )

    return Resolution(
        None,
        "unresolvable",
        "dateparser_none",
    )
