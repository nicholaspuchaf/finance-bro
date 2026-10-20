from app.models import Transaction


def transaction_name(transaction: Transaction) -> str:
    return (transaction.merchant or transaction.description).strip()


def name_key(name: str) -> str:
    return " ".join(name.split()).casefold()


def assign_rule_category(transaction: Transaction, category: str) -> None:
    transaction.category = category
    transaction.category_source = "rule"
    transaction.category_confidence = None
    transaction.classification_reason = None
