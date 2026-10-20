from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.database import Base, get_session
from app.main import app
from app.models import Transaction
from app.schemas import CategoryResult
from app.services.ai_classifier import AIResponseError, OpenAIClassifier
from app.services.analytics import shift_month
from app.services.finance import recurring_expenses, spending_summary
from app.services.pluggy import PluggyClient
from app.migrations import initialize_database
from tests.client import APIClient

ITEM_ID_1 = "11111111-1111-4111-8111-111111111111"
ITEM_ID_CATEGORY = "22222222-2222-4222-8222-222222222222"
ITEM_ID_STATE = "33333333-3333-4333-8333-333333333333"


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)

    async def override():
        with sessions() as session:
            yield session

    app.dependency_overrides[get_session] = override
    try:
        yield APIClient(), sessions
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_validation_filters_and_pagination(client):
    api, _ = client
    base = {"date": "2026-10-01", "description": "Mercado", "amount": "12.34"}
    for patch in ({"amount": "0"}, {"amount": "1.234"}, {"currency": "USD"}, {"category": "Inventada"}):
        assert api.post("/api/transactions", json={**base, **patch}).status_code == 422
    for day in (1, 2, 3):
        assert api.post("/api/transactions", json={**base, "date": f"2026-10-0{day}"}).status_code == 201
    rows = api.get("/api/transactions", params={"limit": 2, "offset": 1, "date_from": "2026-10-01", "date_to": "2026-10-03"}).json()
    assert [row["date"] for row in rows] == ["2026-10-02", "2026-10-01"]
    assert api.get("/api/transactions", params={"date_from": "2026-10-04", "date_to": "2026-10-01"}).status_code == 422
    assert api.patch(f"/api/transactions/{rows[0]['id']}", json={"category": None}).status_code == 422


@pytest.mark.parametrize(
    ("params", "expected_days"),
    [
        ([("categories", "Food delivery"), ("categories", "Eating out")], [7, 3, 2]),
        ([("categories", "Food and drinks")], [1]),
        ([("macro_categories", "Food and drinks")], [7, 3, 2, 1]),
        ([("macro_categories", "Food and drinks"), ("macro_categories", "Services")], [7, 6, 3, 2, 1]),
        ([("macro_categories", "Food and drinks"), ("categories", "Food delivery"), ("categories", "Food delivery")], [7, 3, 2, 1]),
        ([("category", "Groceries"), ("categories", "Food delivery")], [8, 7, 4, 2]),
        ([("categories", "Pharmacy")], []),
        ([("macro_categories", "Food and drinks"), ("limit", "2"), ("offset", "2")], [2, 1]),
        ([("macro_categories", "Food and drinks"), ("macro_categories", "Travel"), ("categories", "Groceries"), ("date_from", "2026-10-02"), ("date_to", "2026-10-05"), ("work_tag", "true")], [5, 4, 2]),
        ([], [8, 7, 6, 5, 4, 3, 2, 1]),
    ],
)
def test_transaction_category_selection_filters_sql_before_pagination(client, params, expected_days):
    api, _ = client
    tag_id = api.post("/api/tags", json={"name": "Work"}).json()["id"]
    categories = ["Food and drinks", "Food delivery", "Eating out", "Groceries", "Accommodation", "Internet", "Food delivery", "Groceries"]
    for day, category in enumerate(categories, 1):
        assert api.post("/api/transactions", json={"date": f"2026-10-{day:02}", "description": f"Movement {day}", "amount": "10", "category": category, "tag_ids": [tag_id] if day in (2, 4, 5, 7) else []}).status_code == 201
    query = [("tag_id", str(tag_id)) if key == "work_tag" else (key, value) for key, value in params]
    response = api.get("/api/transactions", params=query)
    assert response.status_code == 200
    assert [row["description"] for row in response.json()] == [f"Movement {day}" for day in expected_days]


def test_transaction_macro_filter_rejects_unknown_group(client):
    api, _ = client
    assert api.get("/api/transactions", params={"macro_categories": "Inventada"}).status_code == 422


def test_tag_management_assignment_counts_and_filter(client):
    api, _ = client
    first = api.post("/api/tags", json={"name": "  Viagem  "})
    assert first.status_code == 201
    tag_id = first.json()["id"]
    assert first.json()["name"] == "Viagem"
    assert api.post("/api/tags", json={"name": "viagem"}).status_code == 409
    assert api.post("/api/tags", json={"name": "  "}).status_code == 422
    second_id = api.post("/api/tags", json={"name": "Reembolsável"}).json()["id"]
    payload = {"date": "2026-10-01", "description": "Hotel", "amount": "120.00", "category": "Travel", "tag_ids": [tag_id, second_id]}
    created = api.post("/api/transactions", json=payload)
    assert created.status_code == 201
    tx_id = created.json()["id"]
    assert {tag["name"] for tag in created.json()["tags"]} == {"Viagem", "Reembolsável"}
    assert {tag["transaction_count"] for tag in api.get("/api/tags").json()} == {1}
    assert len(api.get("/api/transactions", params={"tag_id": tag_id}).json()) == 1
    assert api.get("/api/transactions", params={"tag_id": 999}).json() == []
    assert api.patch(f"/api/transactions/{tx_id}", json={"tag_ids": [999]}).status_code == 422
    assert api.patch(f"/api/transactions/{tx_id}", json={"tag_ids": [tag_id, tag_id]}).status_code == 422
    assert api.patch(f"/api/transactions/{tx_id}", json={"tag_ids": None}).status_code == 422
    renamed = api.patch(f"/api/tags/{tag_id}", json={"name": "Férias"})
    assert renamed.status_code == 200 and renamed.json()["transaction_count"] == 1
    assert api.patch(f"/api/tags/{tag_id}", json={"name": "reembolsável"}).status_code == 409
    assert api.delete(f"/api/tags/{tag_id}").status_code == 204
    assert [tag["name"] for tag in api.get("/api/transactions").json()[0]["tags"]] == ["Reembolsável"]
    assert api.get("/api/transactions", params={"tag_id": tag_id}).json() == []
    assert api.patch(f"/api/transactions/{tx_id}", json={"tag_ids": []}).json()["tags"] == []
    assert api.get("/api/tags").json()[0]["transaction_count"] == 0
    assert api.delete(f"/api/tags/{tag_id}").status_code == 404


def test_legacy_categories_are_migrated_once_with_backup(tmp_path, monkeypatch):
    import sqlite3
    import app.migrations as migrations

    database_path = tmp_path / "finance.db"
    engine = create_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO transactions (date, description, amount, currency, category, category_source, pending, created_at) VALUES ('2026-10-01', 'Mercado', 20, 'BRL', 'Alimentação', 'manual', 0, '2026-10-01')"))
    monkeypatch.setattr(migrations, "engine", engine)
    initialize_database()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT category FROM transactions")).scalar_one() == "Food and drinks"
    backups = list(tmp_path.glob("finance.before-category-migration-*.db"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as backup:
        assert backup.execute("SELECT category FROM transactions").fetchone()[0] == "Alimentação"
    initialize_database()
    assert len(list(tmp_path.glob("finance.before-category-migration-*.db"))) == 1
    engine.dispose()


def test_finance_rules_and_recurring():
    def tx(month, amount, category="Other", operation=None, description="Netflix"):
        return Transaction(date=date(2026, month, 10), amount=Decimal(str(amount)), currency="BRL", pending=False, category=category, operation_type=operation, description=description)

    rows = [tx(9, 30), tx(10, 32), tx(10, 100, "Transfers"), tx(10, 200, operation="PAGAMENTO_FATURA"), tx(10, 40, operation="ESTORNO"), tx(10, -10), tx(10, 10, "Income")]
    summary = spending_summary(rows, date(2026, 10, 19))
    assert summary["categories"] == [{"category": "Other", "amount": "32", "count": 1}]
    assert recurring_expenses(rows)[0]["months"] == 2


def test_analytics_filters_months_categories_and_investment_cash_flows(client):
    api, _ = client
    today = date.today()
    previous_month = shift_month(today, -1)

    def add(day, amount, category):
        response = api.post("/api/transactions", json={"date": day.isoformat(), "description": category, "amount": str(amount), "category": category})
        assert response.status_code == 201

    add(today, 50, "Groceries")
    add(today, 20, "Housing")
    add(previous_month, 30, "Groceries")
    add(today, 500, "Transfers")
    add(today, 100, "Fixed income")
    add(today, -25, "Proceeds interests and dividends")

    response = api.get("/api/analytics", params={"mode": "expenses", "months": 3, "month": previous_month.strftime("%Y-%m"), "category": "Groceries"})
    assert response.status_code == 200
    result = response.json()
    assert Decimal(result["total"]) == 80
    assert result["count"] == 2
    assert result["selected_month"] == previous_month.strftime("%Y-%m")
    assert Decimal(result["monthly"][-1]["amount"]) == 50
    assert Decimal(result["monthly"][-2]["amount"]) == 30
    assert Decimal(result["monthly"][0]["amount"]) == 0
    assert Decimal(result["daily"][0]["amount"]) == 30
    assert len(result["daily"]) >= 28
    assert Decimal(result["daily"][-1]["amount"]) == 0
    assert {item["category"]: Decimal(item["amount"]) for item in result["categories"]} == {"Groceries": 80}

    investments = api.get("/api/analytics", params={"mode": "investments", "months": 3}).json()
    assert Decimal(investments["total"]) == 100
    assert Decimal(investments["inflows"]) == 25
    assert investments["count"] == 1
    assert investments["categories"][0]["category"] == "Fixed income"
    assert Decimal(investments["categories"][0]["amount"]) == 100
    assert api.get("/api/analytics", params={"months": 25}).status_code == 422
    assert api.get("/api/analytics", params={"mode": "investments", "category": "Groceries"}).status_code == 200
    assert api.get("/api/analytics", params={"month": "2099-01"}).status_code == 422


def test_analytics_aggregates_multiple_selected_categories(client):
    api, _ = client
    today = date.today()
    previous_month = shift_month(today, -1)
    for day, amount, category in [
        (today, 20, "Eating out"),
        (today, 30, "Food delivery"),
        (previous_month, 5, "Food delivery"),
        (today, 100, "Groceries"),
        (today, 80, "Fixed income"),
        (today, 40, "Mutual funds"),
    ]:
        assert api.post("/api/transactions", json={"date": day.isoformat(), "description": category, "amount": str(amount), "category": category}).status_code == 201

    params = [("mode", "expenses"), ("months", "3"), ("categories", "Food delivery"), ("categories", "Eating out")]
    response = api.get("/api/analytics", params=params)
    assert response.status_code == 200
    result = response.json()
    assert result["selected_categories"] == ["Food delivery", "Eating out"]
    assert Decimal(result["total"]) == 55
    assert result["count"] == 3
    assert Decimal(result["monthly"][-1]["amount"]) == 50
    assert Decimal(result["monthly"][-2]["amount"]) == 5
    assert Decimal(result["daily"][today.day - 1]["amount"]) == 50
    assert "Food delivery" in result["available_categories"]
    assert "Eating out" in result["available_categories"]
    assert "Transfers" not in result["available_categories"]

    investments = api.get("/api/analytics", params=[("mode", "investments"), ("categories", "Fixed income"), ("categories", "Mutual funds")]).json()
    assert Decimal(investments["total"]) == 120
    assert investments["count"] == 2
    assert "Food delivery" not in investments["available_categories"]
    assert Decimal(api.get("/api/analytics").json()["total"]) == 150
    assert Decimal(api.get("/api/analytics", params=[("categories", "Food delivery"), ("categories", "Fixed income")]).json()["total"]) == 30


@pytest.mark.parametrize(
    ("selection", "expected", "inflows"),
    [
        ({"categories": ["Food and drinks"]}, {"Food and drinks": 10}, 0),
        ({"categories": ["Food delivery", "Eating out"]}, {"Food delivery": 25, "Eating out": 30}, 0),
        ({"macro_categories": ["Food and drinks"]}, {"Food and drinks": 10, "Food delivery": 25, "Eating out": 30}, 0),
        ({"macro_categories": ["Food and drinks", "Travel"]}, {"Food and drinks": 10, "Food delivery": 25, "Eating out": 30, "Travel": 40, "Accommodation": 50}, 0),
        ({"macro_categories": ["Services"]}, {"Internet": 70}, 0),
        ({"categories": ["Food delivery", "Food delivery"], "macro_categories": ["Food and drinks", "Food and drinks"]}, {"Food and drinks": 10, "Food delivery": 25, "Eating out": 30}, 0),
        ({"categories": ["Groceries"], "macro_categories": ["Food and drinks", "Travel"]}, {"Food and drinks": 10, "Food delivery": 25, "Eating out": 30, "Travel": 40, "Accommodation": 50, "Groceries": 60}, 0),
        ({"macro_categories": ["Food and drinks", "Travel"], "tags": ["Work"]}, {"Food delivery": 25, "Accommodation": 50}, 0),
        ({"macro_categories": ["Food and drinks"], "tags": ["Work", "Personal"]}, {"Food delivery": 25, "Eating out": 30}, 0),
        ({"mode": "investments", "macro_categories": ["Investments"]}, {"Fixed income": 80, "Mutual funds": 90}, 40),
        ({"mode": "investments", "categories": ["Fixed income"]}, {"Fixed income": 80}, 0),
        ({"mode": "investments", "categories": ["Proceeds interests and dividends"]}, {}, 15),
        ({"categories": ["Pharmacy"]}, {}, 0),
        ({}, {"Food and drinks": 10, "Food delivery": 25, "Eating out": 30, "Travel": 40, "Accommodation": 50, "Groceries": 60, "Internet": 70}, 0),
    ],
)
def test_dashboard_filters_apply_to_all_metrics(client, selection, expected, inflows):
    api, sessions = client
    today = date.today()
    previous_month = shift_month(today.replace(day=1), -1)
    tags = {name: api.post("/api/tags", json={"name": name}).json()["id"] for name in ("Work", "Personal")}
    for day, amount, category, names in [
        (today, 10, "Food and drinks", []),
        (today, 20, "Food delivery", ["Work", "Personal"]),
        (today, 30, "Eating out", ["Personal"]),
        (today, 40, "Travel", []),
        (today, 50, "Accommodation", ["Work"]),
        (today, 60, "Groceries", ["Work"]),
        (today, 70, "Internet", []),
        (today, 80, "Fixed income", []),
        (today, 90, "Mutual funds", []),
        (today, -15, "Proceeds interests and dividends", []),
        (today, -25, "Pension", []),
        (previous_month, 5, "Food delivery", ["Work"]),
    ]:
        assert api.post("/api/transactions", json={"date": day.isoformat(), "description": category, "amount": str(amount), "category": category, "tag_ids": [tags[name] for name in names]}).status_code == 201
    # These rows must never affect the selected BRL expenses or their composition.
    with sessions() as session:
        for overrides in [
            {"pending": True}, {"currency": "USD"}, {"operation_type": "ESTORNO"},
            {"date": shift_month(today.replace(day=1), -3)},
            {"date": today + timedelta(days=1)}, {"amount": Decimal("-1000")},
        ]:
            session.add(Transaction(**{"date": today, "description": "Excluded row", "amount": Decimal("1000"), "category": "Food delivery", **overrides}))
        session.commit()

    params = [("months", "3"), ("mode", selection.get("mode", "expenses"))]
    for key in ("categories", "macro_categories"):
        params.extend((key, value) for value in selection.get(key, []))
    params.extend(("tag_ids", str(tags[name])) for name in selection.get("tags", []))
    response = api.get("/api/analytics", params=params)
    assert response.status_code == 200
    result = response.json()
    expected_total = sum(expected.values())
    assert Decimal(result["total"]) == expected_total
    assert Decimal(result["inflows"]) == inflows
    assert {row["category"]: Decimal(row["amount"]) for row in result["categories"]} == expected
    assert sum(Decimal(row["amount"]) for row in result["categories"]) == expected_total
    assert sum(Decimal(row["amount"]) for row in result["monthly"]) == expected_total
    previous_total = 5 if "Food delivery" in expected else 0
    assert Decimal(result["monthly"][-2]["amount"]) == previous_total
    assert sum(Decimal(row["amount"]) for row in result["daily"]) == expected_total - previous_total
    expected_count = sum(2 if category == "Food delivery" else 1 for category in expected)
    assert result["count"] == expected_count
    assert sum(row["count"] for row in result["categories"]) == expected_count
    assert result["selected_categories"] == list(dict.fromkeys(selection.get("categories", [])))
    assert result["selected_macro_categories"] == list(dict.fromkeys(selection.get("macro_categories", [])))


def test_mocked_pluggy_sync_reuses_transactions_and_preserves_category(client, monkeypatch):
    api, _ = client
    async def get_item(self, item_id):
        return {"connector": {"id": 200, "name": "MeuPluggy"}, "status": "UPDATED", "consentExpiresAt": "2099-01-01T00:00:00Z"}
    async def get_accounts(self, item_id):
        return [{"id": "account-1", "name": "Conta", "type": "BANK", "currencyCode": "BRL", "balance": 100}]
    async def get_transactions(self, account_id):
        return [{"id": "transaction-1", "date": "2026-10-01", "description": "Compra", "amount": 20, "type": "DEBIT", "status": "POSTED"}]
    monkeypatch.setattr(PluggyClient, "get_item", get_item)
    monkeypatch.setattr(PluggyClient, "get_accounts", get_accounts)
    monkeypatch.setattr(PluggyClient, "get_transactions", get_transactions)
    first = api.post(f"/api/pluggy/items/{ITEM_ID_1}/sync")
    assert first.status_code == 200 and first.json()["transactions_added"] == 1
    tx_id = api.get("/api/transactions").json()[0]["id"]
    tag_id = api.post("/api/tags", json={"name": "Importante"}).json()["id"]
    api.patch(f"/api/transactions/{tx_id}", json={"category": "Food and drinks", "notes": "Minha anotação", "tag_ids": [tag_id]})
    second = api.post(f"/api/pluggy/items/{ITEM_ID_1}/sync")
    assert second.json()["transactions_added"] == 0
    rows = api.get("/api/transactions").json()
    assert len(rows) == 1 and rows[0]["category"] == "Food and drinks" and rows[0]["notes"] == "Minha anotação"
    assert [tag["name"] for tag in rows[0]["tags"]] == ["Importante"]
    assert api.get("/api/connections").json()[0]["status"] == "UPDATED"


def test_pluggy_category_is_imported_and_manual_correction_survives_sync(client, monkeypatch):
    api, _ = client
    raw = {"id": "tx-category", "date": "2026-10-01", "description": "Mercado", "amount": 20, "type": "DEBIT", "status": "POSTED", "category": "Groceries"}
    async def get_item(self, item_id):
        return {"connector": {"id": 200}, "status": "UPDATED"}
    async def get_accounts(self, item_id):
        return [{"id": "account-category", "name": "Conta", "type": "BANK"}]
    async def get_transactions(self, account_id):
        return [raw]
    monkeypatch.setattr(PluggyClient, "get_item", get_item)
    monkeypatch.setattr(PluggyClient, "get_accounts", get_accounts)
    monkeypatch.setattr(PluggyClient, "get_transactions", get_transactions)
    assert api.post(f"/api/pluggy/items/{ITEM_ID_CATEGORY}/sync").status_code == 200
    imported = api.get("/api/transactions").json()[0]
    assert imported["category"] == "Groceries" and imported["category_source"] == "pluggy"
    raw["category"] = None
    api.post(f"/api/pluggy/items/{ITEM_ID_CATEGORY}/sync")
    assert api.get("/api/transactions").json()[0]["category"] == "Groceries"
    api.patch(f"/api/transactions/{imported['id']}", json={"category": "Food and drinks"})
    raw["category"] = "Shopping"
    api.post(f"/api/pluggy/items/{ITEM_ID_CATEGORY}/sync")
    assert api.get("/api/transactions").json()[0]["category"] == "Food and drinks"


def test_category_rule_updates_matching_history_and_future_manual_transactions(client):
    api, _ = client
    def add(description):
        return api.post("/api/transactions", json={"date": "2026-10-01", "description": description, "amount": "20", "category": "Other"}).json()

    first = add("Mercado Central")
    second = add("  mercado   central  ")
    other = add("Mercado da Esquina")
    assert api.post(f"/api/transactions/{first['id']}/category-rule", json={"category": "Groceries"}).status_code == 409
    assert api.patch(f"/api/transactions/{first['id']}", json={"category": "Groceries"}).status_code == 200
    assert api.post(f"/api/transactions/{first['id']}/category-rule", json={"category": "Inventada"}).status_code == 422
    applied = api.post(f"/api/transactions/{first['id']}/category-rule", json={"category": "Groceries"})
    assert applied.status_code == 200
    assert applied.json()["transactions_updated"] == 2
    rows = {row["id"]: row for row in api.get("/api/transactions").json()}
    assert {rows[tx["id"]]["category_source"] for tx in (first, second)} == {"rule"}
    assert rows[other["id"]]["category"] == "Other"
    future = add("MERCADO CENTRAL")
    assert future["category"] == "Groceries" and future["category_source"] == "rule"
    assert api.patch(f"/api/transactions/{first['id']}", json={"category": "Food and drinks"}).status_code == 200
    reapplied = api.post(f"/api/transactions/{first['id']}/category-rule", json={"category": "Food and drinks"})
    assert reapplied.json()["transactions_updated"] == 3
    assert {row["category"] for row in api.get("/api/transactions").json() if row["id"] != other["id"]} == {"Food and drinks"}


def test_category_rule_overrides_pluggy_on_future_sync(client, monkeypatch):
    api, _ = client
    raw = [{"id": "rule-1", "date": "2026-10-01", "description": "Compra no mercado", "merchant": {"name": "Mercado Central"}, "amount": 20, "type": "DEBIT", "category": "Other"}]

    async def get_item(self, item_id):
        return {"connector": {"id": 200}, "status": "UPDATED"}
    async def get_accounts(self, item_id):
        return [{"id": "account-rule", "name": "Conta", "type": "BANK"}]
    async def get_transactions(self, account_id):
        return raw
    monkeypatch.setattr(PluggyClient, "get_item", get_item)
    monkeypatch.setattr(PluggyClient, "get_accounts", get_accounts)
    monkeypatch.setattr(PluggyClient, "get_transactions", get_transactions)

    assert api.post(f"/api/pluggy/items/{ITEM_ID_1}/sync").status_code == 200
    first = api.get("/api/transactions").json()[0]
    assert api.patch(f"/api/transactions/{first['id']}", json={"category": "Groceries"}).status_code == 200
    assert api.post(f"/api/transactions/{first['id']}/category-rule", json={"category": "Groceries"}).status_code == 200
    raw.append({"id": "rule-2", "date": "2026-10-02", "description": "Outra descrição", "merchant": {"name": "mercado central"}, "amount": 30, "type": "DEBIT", "category": "Shopping"})
    assert api.post(f"/api/pluggy/items/{ITEM_ID_1}/sync").status_code == 200
    rows = api.get("/api/transactions").json()
    assert len(rows) == 2
    assert {row["category"] for row in rows} == {"Groceries"}
    assert {row["category_source"] for row in rows} == {"rule"}
    assert api.post(f"/api/pluggy/items/{ITEM_ID_1}/sync").json()["transactions_added"] == 0
    assert {row["category"] for row in api.get("/api/transactions").json()} == {"Groceries"}


def test_connection_states_and_free_connector_guard(client, monkeypatch):
    api, _ = client
    item = {"connector": {"id": 200, "name": "MeuPluggy"}, "status": "OUTDATED"}
    async def get_item(self, item_id):
        return item
    monkeypatch.setattr(PluggyClient, "get_item", get_item)
    response = api.post(f"/api/pluggy/items/{ITEM_ID_STATE}/sync")
    assert response.status_code == 409
    assert api.get("/api/connections").json()[0]["status"] == "OUTDATED"
    item["status"] = "UPDATED"
    item["consentExpiresAt"] = "2020-01-01T00:00:00Z"
    assert api.post(f"/api/pluggy/items/{ITEM_ID_STATE}/sync").status_code == 409
    assert api.get("/api/connections").json()[0]["status"] == "CONSENT_EXPIRED"
    item["connector"]["id"] = 123
    assert api.post(f"/api/pluggy/items/{ITEM_ID_STATE}/sync").status_code == 422


def test_incomplete_item_id_is_rejected_before_calling_pluggy(client, monkeypatch):
    api, _ = client

    async def unexpected_call(self, item_id):
        raise AssertionError("A Pluggy não deve receber um ID incompleto")

    monkeypatch.setattr(PluggyClient, "get_item", unexpected_call)
    response = api.post("/api/pluggy/items/68e9a286/sync")
    assert response.status_code == 422
    assert "ID completo" in response.json()["detail"]


@pytest.mark.parametrize(
    ("upstream_status", "expected_status", "expected_message"),
    [(404, 404, "Item não encontrado"), (401, 502, "credenciais"), (429, 503, "limitou")],
)
def test_pluggy_http_errors_have_actionable_messages(client, monkeypatch, upstream_status, expected_status, expected_message):
    api, _ = client

    async def fail(self, item_id):
        request = httpx.Request("GET", f"https://api.pluggy.ai/items/{item_id}")
        response = httpx.Response(upstream_status, request=request)
        raise httpx.HTTPStatusError("upstream failure", request=request, response=response)

    monkeypatch.setattr(PluggyClient, "get_item", fail)
    response = api.post(f"/api/pluggy/items/{ITEM_ID_1}/sync")
    assert response.status_code == expected_status
    assert expected_message in response.json()["detail"]


def test_mocked_pluggy_auth_and_pages(monkeypatch):
    calls = []
    def handler(request):
        calls.append(request)
        if request.url.path == "/auth":
            return httpx.Response(200, json={"apiKey": "test-key"})
        if request.url.path == "/connect_token":
            return httpx.Response(200, json={"accessToken": "connect-key"})
        if request.url.path == "/v2/transactions":
            if request.url.params.get("after"):
                return httpx.Response(200, json={"results": [{"id": "second"}], "next": None})
            return httpx.Response(200, json={"results": [{"id": "first"}], "next": "?accountId=account&after=opaque%2Bcursor%3D"})
        return httpx.Response(200, json={"results": [{"id": str(request.url.params.get("page"))}], "totalPages": 2})
    transport = httpx.MockTransport(handler)
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original(transport=transport))
    import asyncio
    async def exercise():
        pluggy = PluggyClient(Settings(pluggy_client_id="id", pluggy_client_secret="secret"))
        assert await pluggy.create_connect_token("personal") == "connect-key"
        assert len(await pluggy.get_accounts("item")) == 2
        assert len(await pluggy.get_transactions("account")) == 2
    asyncio.run(exercise())
    assert sum(req.url.path == "/auth" for req in calls) == 1
    assert all(req.headers.get("X-API-KEY") == "test-key" for req in calls[1:])
    transaction_calls = [req for req in calls if req.url.path == "/v2/transactions"]
    assert len(transaction_calls) == 2
    assert transaction_calls[0].url.params["accountId"] == "account"
    assert transaction_calls[1].url.query == b"accountId=account&after=opaque%2Bcursor%3D"
    assert all(req.url.path != "/transactions" for req in calls)


def test_ai_response_failures_and_real_currency(monkeypatch):
    cases = [
        ({"status": "incomplete", "output": []}, "concluída"),
        ({"status": "completed", "output": [{"content": [{"type": "refusal"}]}]}, "recusou"),
        ({"status": "completed", "output": []}, "não retornou"),
        ({"status": "completed", "output_text": "not json"}, "inválida"),
    ]
    captured = []
    def handler(request):
        captured.append(request.content.decode())
        return httpx.Response(200, json=cases.pop(0)[0])
    transport = httpx.MockTransport(handler)
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original(transport=transport))
    import asyncio
    classifier = OpenAIClassifier(Settings(openai_api_key="test"))
    for _ in range(4):
        with pytest.raises(AIResponseError):
            asyncio.run(classifier.classify("Compra", "10", "USD"))
    assert all("USD" in payload for payload in captured)


def test_ai_failure_is_api_error_without_overwriting_notes(client, monkeypatch):
    api, _ = client
    tx = api.post("/api/transactions", json={"date": "2026-10-01", "description": "Compra", "amount": "10"}).json()
    api.patch(f"/api/transactions/{tx['id']}", json={"notes": "Anotação"})
    async def fail(self, description, amount, currency):
        raise AIResponseError("Resposta inválida")
    monkeypatch.setattr(OpenAIClassifier, "classify", fail)
    assert api.post(f"/api/transactions/{tx['id']}/classify").status_code == 502
    stored = api.get("/api/transactions").json()[0]
    assert stored["notes"] == "Anotação" and stored["classification_reason"] is None


def test_batch_classifies_only_uncategorized_and_preserves_notes(client, monkeypatch):
    api, _ = client
    async def classify(self, description, amount, currency):
        return CategoryResult(category="Food and drinks", confidence=0.9, merchant="Mercado", reasoning="Compra de comida")
    monkeypatch.setattr(OpenAIClassifier, "classify", classify)
    for n in range(12):
        api.post("/api/transactions", json={"date": "2026-10-01", "description": f"Compra {n}", "amount": "10"})
    # Manual entries are intentionally excluded from the automatic batch.
    assert api.post("/api/transactions/classify-batch").json()["attempted"] == 0
    _, sessions = client
    with sessions() as session:
        rows = session.query(Transaction).all()
        for row in rows:
            row.category_source = "pending"
        rows[0].notes = "Anotação pessoal"
        session.commit()
    result = api.post("/api/transactions/classify-batch").json()
    assert result["attempted"] == 10 and result["classified"] == 10
    classified = [row for row in api.get("/api/transactions").json() if row["category_source"] == "ai"]
    assert len(classified) == 10
    assert next(row for row in classified if row["notes"])["classification_reason"] == "Compra de comida"


def test_local_only_guard():
    import asyncio
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("192.0.2.1", 1234)), base_url="http://localhost") as remote:
            assert (await remote.get("/api/health")).status_code == 403
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 1234)), base_url="http://localhost") as local:
            result = await local.get("/api/health")
            assert result.status_code == 200 and result.headers["cache-control"] == "no-store"
    asyncio.run(exercise())


def test_schema_migration_and_backup(tmp_path, monkeypatch):
    import sqlite3
    import app.migrations as migrations
    from scripts.backup import backup_database
    db = tmp_path / "data" / "finance_bro.db"
    db.parent.mkdir()
    with sqlite3.connect(db) as connection:
        connection.execute("CREATE TABLE transactions (id INTEGER PRIMARY KEY, external_id TEXT, account_id INTEGER, date DATE, category TEXT)")
    old_engine = create_engine(f"sqlite:///{db}")
    monkeypatch.setattr(migrations, "engine", old_engine)
    initialize_database()
    with sqlite3.connect(db) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(transactions)")}
    assert {"classification_reason", "operation_type"} <= columns
    assert list(db.parent.glob("*.before-migration-*.db"))
    backup = backup_database(db, tmp_path / "backups")
    assert backup.exists() and backup.stat().st_mode & 0o777 == 0o600
    old_engine.dispose()
