from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_session
from app.main import app
from app.schemas import CATEGORIES, CategoryResult
from app.services.pluggy import transaction_values
from tests.client import APIClient


def test_normalizes_a_pluggy_transaction():
    transaction = transaction_values({
        "id": "tx-123",
        "date": "2026-10-19T12:35:00.000Z",
        "description": "PADARIA CENTRAL",
        "amount": -28.9,
        "currencyCode": "BRL",
        "status": "POSTED",
        "merchant": {"name": "Padaria Central"},
    })

    assert transaction == {
        "external_id": "tx-123",
        "date": date(2026, 10, 19),
        "description": "PADARIA CENTRAL",
        "merchant": "Padaria Central",
        "amount": Decimal("-28.9"),
        "currency": "BRL",
        "pending": False,
        "operation_type": None,
    }


def test_normalizes_pending_transaction_and_fallback_description():
    transaction = transaction_values({
        "id": "tx-456",
        "accountingDate": "2026-10-18",
        "amount": 75,
        "status": "PENDING",
    })

    assert transaction["description"] == "Transação"
    assert transaction["pending"] is True
    assert transaction["date"] == date(2026, 10, 18)


def test_normalizes_bank_credits_and_debits_to_income_and_expense_signs():
    incoming = transaction_values({"id": "in", "date": "2026-10-01", "amount": 1200, "type": "CREDIT"}, "BANK")
    outgoing = transaction_values({"id": "out", "date": "2026-10-01", "amount": 45, "type": "DEBIT"}, "BANK")

    assert incoming["amount"] == Decimal("-1200")
    assert outgoing["amount"] == Decimal("45")


def test_category_result_accepts_only_supported_categories():
    result = CategoryResult(category="Food and drinks", confidence=0.92, merchant="Mercado", reasoning="Compra de alimentos")
    assert result.category in CATEGORIES

    with pytest.raises(ValidationError):
        CategoryResult(category="Categoria inventada", confidence=0.92, merchant=None, reasoning="Teste")


def test_transaction_api_stores_and_filters_a_manual_transaction():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(test_engine)
    test_session = sessionmaker(bind=test_engine, expire_on_commit=False)

    async def override_session():
        with test_session() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    client = APIClient()
    try:
        created = client.post("/api/transactions", json={
            "date": "2026-10-19",
            "description": "Café",
            "amount": "18.50",
            "category": "Food and drinks",
        })
        assert created.status_code == 201
        assert created.json()["category_source"] == "manual"

        filtered = client.get("/api/transactions", params={"search": "Café", "category": "Food and drinks"})
        assert filtered.status_code == 200
        assert len(filtered.json()) == 1
        assert filtered.json()[0]["description"] == "Café"
    finally:
        app.dependency_overrides.clear()
        test_engine.dispose()
