import re
import unicodedata
from collections import defaultdict
from datetime import date
from decimal import Decimal

from app.categories import CATEGORY_GROUPS
from app.models import Transaction


EXCLUDED_CATEGORIES = {
    category
    for group in ("Transfers", "Same person transfer", "Investments", "Income")
    for category in CATEGORY_GROUPS[group]
}
EXCLUDED_OPERATIONS = {"PAGAMENTO_FATURA", "PAGAMENTO_DE_FATURA", "TRANSFERENCIA_MESMA_TITULARIDADE", "ESTORNO"}


def is_expense(tx: Transaction) -> bool:
    category = tx.category.casefold()
    excluded_provider_category = category.startswith(("transfer", "same person transfer", "investments", "income")) or category in {"credit card payment", "third-party transfers"}
    return (
        not tx.pending and tx.currency == "BRL" and tx.amount > 0
        and tx.category not in EXCLUDED_CATEGORIES
        and not excluded_provider_category
        and (tx.operation_type or "").upper() not in EXCLUDED_OPERATIONS
    )


def spending_summary(transactions: list[Transaction], today: date) -> dict:
    rows = defaultdict(lambda: {"amount": Decimal("0"), "count": 0})
    current = [tx for tx in transactions if today.replace(day=1) <= tx.date <= today]
    for tx in current:
        if is_expense(tx):
            rows[tx.category]["amount"] += tx.amount
            rows[tx.category]["count"] += 1
    categories = [
        {"category": name, "amount": str(values["amount"]), "count": values["count"]}
        for name, values in sorted(rows.items(), key=lambda item: item[1]["amount"], reverse=True)
    ]
    return {"month": today.strftime("%Y-%m"), "categories": categories, "transaction_count": len(current), "uncategorized_count": sum(tx.category == "Uncategorized" and not tx.pending for tx in transactions)}


def recurring_expenses(transactions: list[Transaction]) -> list[dict]:
    groups = defaultdict(list)
    for tx in transactions:
        if not is_expense(tx):
            continue
        label = tx.merchant or tx.description
        folded = unicodedata.normalize("NFKD", label.casefold())
        key = re.sub(r"[^a-z0-9]+", " ", "".join(c for c in folded if not unicodedata.combining(c))).strip()
        if key:
            groups[key].append(tx)
    result = []
    for key, items in groups.items():
        months = {(tx.date.year, tx.date.month) for tx in items}
        if len(months) < 2:
            continue
        amounts = [tx.amount for tx in items]
        if min(amounts) < max(amounts) * Decimal("0.8"):
            continue
        latest = max(items, key=lambda tx: tx.date)
        result.append({"description": latest.merchant or latest.description, "months": len(months), "last_date": latest.date.isoformat(), "last_amount": str(latest.amount), "currency": latest.currency})
    return sorted(result, key=lambda item: item["last_date"], reverse=True)
