from calendar import monthrange
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from app.categories import CATEGORY_GROUPS
from app.models import Transaction
from app.services.finance import EXCLUDED_OPERATIONS, is_expense


INVESTMENT_CATEGORIES = set(CATEGORY_GROUPS["Investments"])
MACRO_CATEGORIES = {name: set(categories) for name, categories in CATEGORY_GROUPS.items()}


def shift_month(month: date, offset: int) -> date:
    index = month.year * 12 + month.month - 1 + offset
    return date(index // 12, index % 12 + 1, 1)


def analyze_transactions(
    transactions: list[Transaction],
    today: date,
    months: int,
    mode: str,
    selected_month: date,
    selected_categories: set[str] | None = None,
    selected_tag_ids: set[int] | None = None,
) -> dict:
    selected_categories = selected_categories or set()
    selected_tag_ids = selected_tag_ids or set()
    first_month = shift_month(today.replace(day=1), 1 - months)
    month_keys = [shift_month(first_month, index).strftime("%Y-%m") for index in range(months)]
    month_totals = defaultdict(lambda: {"amount": Decimal("0"), "count": 0})
    day_totals = defaultdict(lambda: {"amount": Decimal("0"), "count": 0})
    category_totals = defaultdict(lambda: {"amount": Decimal("0"), "count": 0})
    inflows = Decimal("0")

    for transaction in transactions:
        if not first_month <= transaction.date <= today or transaction.pending or transaction.currency != "BRL":
            continue
        if selected_tag_ids and not any(tag.id in selected_tag_ids for tag in transaction.tags):
            continue
        if selected_categories and transaction.category not in selected_categories:
            continue
        if mode == "expenses":
            if not is_expense(transaction):
                continue
        elif transaction.category not in INVESTMENT_CATEGORIES or (transaction.operation_type or "").upper() in EXCLUDED_OPERATIONS:
            continue

        if transaction.amount < 0:
            if mode == "investments":
                inflows += abs(transaction.amount)
            continue
        if transaction.amount == 0:
            continue

        category_totals[transaction.category]["amount"] += transaction.amount
        category_totals[transaction.category]["count"] += 1
        monthly = month_totals[transaction.date.strftime("%Y-%m")]
        monthly["amount"] += transaction.amount
        monthly["count"] += 1
        if transaction.date.year == selected_month.year and transaction.date.month == selected_month.month:
            daily = day_totals[transaction.date.isoformat()]
            daily["amount"] += transaction.amount
            daily["count"] += 1

    last_day = min(monthrange(selected_month.year, selected_month.month)[1], today.day if selected_month.year == today.year and selected_month.month == today.month else 31)
    daily_dates = [selected_month + timedelta(days=index) for index in range(last_day)]
    monthly = [{"month": key, "amount": str(month_totals[key]["amount"]), "count": month_totals[key]["count"]} for key in month_keys]
    daily = [{"date": day.isoformat(), "amount": str(day_totals[day.isoformat()]["amount"]), "count": day_totals[day.isoformat()]["count"]} for day in daily_dates]
    category_breakdown = [
        {"category": name, "amount": str(values["amount"]), "count": values["count"]}
        for name, values in sorted(category_totals.items(), key=lambda item: (-item[1]["amount"], item[0]))
    ]
    return {
        "mode": mode,
        "months": months,
        "period_start": first_month.isoformat(),
        "period_end": today.isoformat(),
        "selected_month": selected_month.strftime("%Y-%m"),
        "selected_categories": sorted(selected_categories),
        "total": str(sum((row["amount"] for row in month_totals.values()), Decimal("0"))),
        "count": sum(row["count"] for row in month_totals.values()),
        "inflows": str(inflows),
        "monthly": monthly,
        "daily": daily,
        "categories": category_breakdown,
    }
