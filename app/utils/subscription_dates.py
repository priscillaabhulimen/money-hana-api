import calendar
from datetime import date, timedelta


def _last_day_of_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def _next_fixed_monthly(anchor_day: int, from_date: date) -> date:
    year, month = from_date.year, from_date.month
    last_day = _last_day_of_month(year, month)
    day = min(anchor_day, last_day)
    candidate = date(year, month, day)
    if candidate <= from_date:
        month += 1
        if month > 12:
            month = 1
            year += 1
        last_day = _last_day_of_month(year, month)
        day = min(anchor_day, last_day)
        candidate = date(year, month, day)
    return candidate


def _next_fixed_weekly(anchor_day: int, from_date: date) -> date:
    # anchor_day: 0=Mon, 6=Sun — matches Python's weekday()
    days_ahead = anchor_day - from_date.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return from_date + timedelta(days=days_ahead)


def _next_fixed_yearly(anchor_day: int, anchor_month: int, from_date: date) -> date:
    year = from_date.year
    last_day = _last_day_of_month(year, anchor_month)
    day = min(anchor_day, last_day)
    candidate = date(year, anchor_month, day)
    if candidate <= from_date:
        year += 1
        last_day = _last_day_of_month(year, anchor_month)
        day = min(anchor_day, last_day)
        candidate = date(year, anchor_month, day)
    return candidate


def _advance_periodic(current_due: date, frequency: str) -> date:
    if frequency == "weekly":
        return current_due + timedelta(weeks=1)
    if frequency == "monthly":
        month = current_due.month + 1
        year = current_due.year
        if month > 12:
            month = 1
            year += 1
        last_day = _last_day_of_month(year, month)
        return date(year, month, min(current_due.day, last_day))
    if frequency == "yearly":
        year = current_due.year + 1
        last_day = _last_day_of_month(year, current_due.month)
        return date(year, current_due.month, min(current_due.day, last_day))
    raise ValueError(f"Unknown frequency: {frequency}")


def calculate_next_due_date(
    billing_type: str,
    frequency: str,
    anchor_day: int | None,
    anchor_month: int | None,
    from_date: date,
) -> date:
    if billing_type == "periodic":
        return _advance_periodic(from_date, frequency)

    if billing_type == "fixed_date":
        if frequency == "monthly":
            if anchor_day is None:
                raise ValueError("anchor_day required for fixed_date monthly")
            return _next_fixed_monthly(anchor_day, from_date)
        if frequency == "weekly":
            if anchor_day is None:
                raise ValueError("anchor_day required for fixed_date weekly")
            return _next_fixed_weekly(anchor_day, from_date)
        if frequency == "yearly":
            if anchor_day is None or anchor_month is None:
                raise ValueError("anchor_day and anchor_month required for fixed_date yearly")
            return _next_fixed_yearly(anchor_day, anchor_month, from_date)

    raise ValueError(f"Unknown billing_type: {billing_type}")


def advance_due_date(subscription) -> date:
    """Advance next_due_date by one period after confirmation or dismissal."""
    from_date = subscription.next_due_date
    if subscription.billing_type == "periodic":
        return _advance_periodic(from_date, subscription.frequency)
    if subscription.billing_type == "fixed_date":
        if subscription.frequency == "monthly":
            return _next_fixed_monthly(subscription.anchor_day, from_date)
        if subscription.frequency == "weekly":
            return _next_fixed_weekly(subscription.anchor_day, from_date)
        if subscription.frequency == "yearly":
            return _next_fixed_yearly(
                subscription.anchor_day,
                subscription.anchor_month,
                from_date,
            )
    raise ValueError("Cannot advance due date — unknown billing configuration")