from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from uuid import UUID

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.categories import CATEGORY_GROUPS
from app.config import get_settings
from app.database import get_session
from app.migrations import initialize_database
from app.models import Account, BankConnection, CategoryRule, Tag, Transaction, transaction_tags, utc_now
from app.schemas import CATEGORIES, CategoryRuleCreate, ConnectionRead, TagCreate, TagRead, TransactionCreate, TransactionRead, TransactionUpdate
from app.services.ai_classifier import AIConfigurationError, AIResponseError, OpenAIClassifier
from app.services.analytics import analyze_transactions, shift_month
from app.services.category_rules import assign_rule_category, name_key, transaction_name
from app.services.finance import EXCLUDED_CATEGORIES, recurring_expenses, spending_summary
from app.services.pluggy import PluggyClient, PluggyConfigurationError, PluggyResponseError, transaction_values


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="Finance Bro API", version="0.1.0", lifespan=lifespan)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)


class LocalOnlyMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.inner(scope, receive, send)
        client = scope.get("client")
        if client and client[0] not in {"127.0.0.1", "::1", "localhost", "testclient"}:
            return await JSONResponse(status_code=403, content={"detail": "API disponível apenas localmente."})(scope, receive, send)

        async def send_with_no_store(message):
            if message["type"] == "http.response.start" and scope.get("path", "").startswith("/api/"):
                message["headers"] = list(message.get("headers", [])) + [(b"cache-control", b"no-store")]
            await send(message)

        await self.inner(scope, receive, send_with_no_store)


app.add_middleware(LocalOnlyMiddleware)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/config")
async def public_config():
    return {
        "pluggy_configured": bool(settings.pluggy_client_id and settings.pluggy_client_secret),
        "ai_configured": bool(settings.openai_api_key),
        "categories": CATEGORIES,
        "category_groups": [{"name": name, "categories": list(categories)} for name, categories in CATEGORY_GROUPS.items()],
    }


@app.get("/api/summary")
async def summary(session: Session = Depends(get_session)):
    return spending_summary(session.scalars(select(Transaction)).all(), date.today())


@app.get("/api/analytics")
async def analytics(
    mode: str = Query(default="expenses", pattern="^(expenses|investments)$"),
    months: int = Query(default=1, ge=1, le=24),
    month: str | None = Query(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    category: str | None = None,
    categories: list[str] = Query(default_factory=list),
    session: Session = Depends(get_session),
):
    today = date.today()
    first_month = shift_month(today.replace(day=1), 1 - months)
    try:
        selected_month = date.fromisoformat(f"{month}-01") if month else today.replace(day=1)
    except ValueError as exc:
        raise HTTPException(422, "Mês inválido.") from exc
    if not first_month <= selected_month <= today.replace(day=1):
        raise HTTPException(422, "O mês selecionado está fora do período de análise.")
    available_categories = list(CATEGORY_GROUPS["Investments"]) if mode == "investments" else [name for name in CATEGORIES if name not in EXCLUDED_CATEGORIES]
    selected_categories = list(dict.fromkeys([*categories, *([category] if category else [])]))
    if any(name not in available_categories for name in selected_categories):
        raise HTTPException(422, "Categoria inválida para esta análise.")
    transactions = session.scalars(select(Transaction).where(Transaction.date >= first_month, Transaction.date <= today)).all()
    result = analyze_transactions(transactions, today, months, mode, selected_month, set(selected_categories))
    result["selected_categories"] = selected_categories
    result["available_categories"] = available_categories
    return result


@app.get("/api/recurring")
async def recurring(session: Session = Depends(get_session)):
    return recurring_expenses(session.scalars(select(Transaction).order_by(desc(Transaction.date))).all())


def resolve_tags(session: Session, tag_ids: list[int]) -> list[Tag]:
    if len(set(tag_ids)) != len(tag_ids):
        raise HTTPException(422, "A mesma tag foi informada mais de uma vez.")
    if not tag_ids:
        return []
    tags = session.scalars(select(Tag).where(Tag.id.in_(tag_ids)).order_by(Tag.name)).all()
    if len(tags) != len(tag_ids):
        raise HTTPException(422, "Uma ou mais tags não existem.")
    return tags


@app.get("/api/tags", response_model=list[TagRead])
async def list_tags(session: Session = Depends(get_session)):
    rows = session.execute(
        select(Tag, func.count(transaction_tags.c.transaction_id))
        .outerjoin(transaction_tags, Tag.id == transaction_tags.c.tag_id)
        .group_by(Tag.id, Tag.name)
        .order_by(Tag.name)
    ).all()
    return [TagRead(id=tag.id, name=tag.name, transaction_count=count) for tag, count in rows]


@app.post("/api/tags", response_model=TagRead, status_code=201)
async def create_tag(payload: TagCreate, session: Session = Depends(get_session)):
    name_key = payload.name.casefold()
    if session.scalar(select(Tag.id).where(Tag.name_key == name_key)) is not None:
        raise HTTPException(409, "Já existe uma tag com esse nome.")
    tag = Tag(name=payload.name, name_key=name_key)
    session.add(tag)
    session.commit()
    return TagRead(id=tag.id, name=tag.name, transaction_count=0)


@app.patch("/api/tags/{tag_id}", response_model=TagRead)
async def rename_tag(tag_id: int, payload: TagCreate, session: Session = Depends(get_session)):
    tag = session.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(404, "Tag não encontrada.")
    name_key = payload.name.casefold()
    if session.scalar(select(Tag.id).where(Tag.name_key == name_key, Tag.id != tag_id)) is not None:
        raise HTTPException(409, "Já existe uma tag com esse nome.")
    tag.name = payload.name
    tag.name_key = name_key
    count = session.scalar(select(func.count()).select_from(transaction_tags).where(transaction_tags.c.tag_id == tag_id))
    session.commit()
    return TagRead(id=tag.id, name=tag.name, transaction_count=count or 0)


@app.delete("/api/tags/{tag_id}", status_code=204)
async def delete_tag(tag_id: int, session: Session = Depends(get_session)):
    tag = session.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(404, "Tag não encontrada.")
    session.delete(tag)
    session.commit()


@app.get("/api/transactions", response_model=list[TransactionRead])
async def list_transactions(
    search: str = "",
    category: str = "",
    tag_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
):
    query = select(Transaction).order_by(desc(Transaction.date), desc(Transaction.id)).limit(limit).offset(offset)
    if tag_id is not None:
        query = query.join(Transaction.tags).where(Tag.id == tag_id)
    if date_from and date_to and date_from > date_to:
        raise HTTPException(422, "A data inicial deve ser anterior à data final.")
    if search:
        query = query.where(or_(Transaction.description.ilike(f"%{search}%"), Transaction.merchant.ilike(f"%{search}%")))
    if category:
        query = query.where(Transaction.category == category)
    if date_from:
        query = query.where(Transaction.date >= date_from)
    if date_to:
        query = query.where(Transaction.date <= date_to)
    return session.scalars(query).all()


@app.post("/api/transactions", response_model=TransactionRead, status_code=201)
async def create_transaction(payload: TransactionCreate, session: Session = Depends(get_session)):
    values = payload.model_dump(exclude={"tag_ids"})
    rule = session.scalar(select(CategoryRule).where(CategoryRule.name_key == name_key(values["description"])))
    transaction = Transaction(**values, category_source="manual", tags=resolve_tags(session, payload.tag_ids))
    if rule is not None:
        assign_rule_category(transaction, rule.category)
    session.add(transaction)
    session.commit()
    session.refresh(transaction)
    return transaction


@app.post("/api/transactions/{transaction_id}/category-rule")
async def create_category_rule(transaction_id: int, payload: CategoryRuleCreate, session: Session = Depends(get_session)):
    transaction = session.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(404, "Transação não encontrada.")
    if transaction.category != payload.category:
        raise HTTPException(409, "A categoria desta transação mudou. Selecione a categoria novamente.")
    name = transaction_name(transaction)
    key = name_key(name)
    rule = session.scalar(select(CategoryRule).where(CategoryRule.name_key == key))
    if rule is None:
        rule = CategoryRule(name=name, name_key=key, category=payload.category)
        session.add(rule)
    else:
        rule.name = name
        rule.category = payload.category
    updated = 0
    for matching in session.scalars(select(Transaction)).all():
        if name_key(transaction_name(matching)) == key:
            assign_rule_category(matching, payload.category)
            updated += 1
    session.commit()
    return {"name": name, "category": payload.category, "transactions_updated": updated}


@app.patch("/api/transactions/{transaction_id}", response_model=TransactionRead)
async def update_transaction(transaction_id: int, payload: TransactionUpdate, session: Session = Depends(get_session)):
    transaction = session.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(404, "Transação não encontrada.")
    if "category" in payload.model_fields_set and payload.category is None:
        raise HTTPException(422, "Informe uma categoria válida.")
    if "tag_ids" in payload.model_fields_set:
        if payload.tag_ids is None:
            raise HTTPException(422, "Informe uma lista de tags.")
        transaction.tags = resolve_tags(session, payload.tag_ids)
    for field, value in payload.model_dump(exclude_unset=True, exclude={"tag_ids"}).items():
        setattr(transaction, field, value)
    if "category" in payload.model_fields_set:
        transaction.category_source = "manual"
    session.commit()
    session.refresh(transaction)
    return transaction


@app.delete("/api/transactions/{transaction_id}", status_code=204)
async def delete_transaction(transaction_id: int, session: Session = Depends(get_session)):
    transaction = session.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(404, "Transação não encontrada.")
    session.delete(transaction)
    session.commit()


@app.post("/api/transactions/{transaction_id}/classify", response_model=TransactionRead)
async def classify_transaction(transaction_id: int, session: Session = Depends(get_session)):
    transaction = session.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(404, "Transação não encontrada.")
    try:
        result = await OpenAIClassifier(settings).classify(transaction.description, str(transaction.amount), transaction.currency)
    except AIConfigurationError as exc:
        raise HTTPException(503, str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(502, "Não foi possível consultar o serviço de IA.") from exc
    except AIResponseError as exc:
        raise HTTPException(502, str(exc)) from exc
    transaction.category = result.category
    transaction.category_confidence = result.confidence
    transaction.category_source = "ai"
    transaction.merchant = result.merchant or transaction.merchant
    transaction.classification_reason = result.reasoning
    session.commit()
    session.refresh(transaction)
    return transaction


@app.post("/api/transactions/classify-batch")
async def classify_batch(session: Session = Depends(get_session)):
    candidates = session.scalars(select(Transaction).where(Transaction.category == "Uncategorized", Transaction.category_source.notin_(["manual", "rule"]), Transaction.pending.is_(False)).order_by(desc(Transaction.date)).limit(10)).all()
    classified = 0
    errors = []
    classifier = OpenAIClassifier(settings)
    for tx in candidates:
        try:
            result = await classifier.classify(tx.description, str(tx.amount), tx.currency)
            tx.category = result.category
            tx.category_source = "ai"
            tx.category_confidence = result.confidence
            tx.classification_reason = result.reasoning
            tx.merchant = result.merchant or tx.merchant
            session.commit()
            classified += 1
        except AIConfigurationError as exc:
            raise HTTPException(503, str(exc)) from exc
        except (AIResponseError, httpx.HTTPError) as exc:
            session.rollback()
            errors.append({"id": tx.id, "error": str(exc)})
    return {"attempted": len(candidates), "classified": classified, "errors": errors}


@app.get("/api/connections", response_model=list[ConnectionRead])
async def list_connections(session: Session = Depends(get_session)):
    return session.scalars(select(BankConnection).options(selectinload(BankConnection.accounts))).all()


@app.post("/api/connections/sync")
async def sync_connections(session: Session = Depends(get_session)):
    connections = session.scalars(select(BankConnection)).all()
    if not connections:
        raise HTTPException(404, "Nenhum banco conectado.")
    results = []
    errors = []
    for connection in connections:
        try:
            results.append(await sync_item(connection.item_id, session))
        except HTTPException as exc:
            errors.append({"item_id": connection.item_id, "error": exc.detail})
    return {"connections_synced": len(results), "transactions_added": sum(r["transactions_added"] for r in results), "errors": errors}


@app.post("/api/pluggy/connect-token")
async def connect_token():
    try:
        token = await PluggyClient(settings).create_connect_token("finance-bro-personal")
    except PluggyConfigurationError as exc:
        raise HTTPException(503, str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(502, "Não foi possível autenticar com a Pluggy.") from exc
    return {"accessToken": token}


@app.post("/api/pluggy/items/{item_id}/sync")
async def sync_item(item_id: str, session: Session = Depends(get_session)):
    try:
        UUID(item_id)
    except ValueError as exc:
        raise HTTPException(422, "Item ID incompleto ou inválido. Copie o ID completo em Dashboard → Aplicações → Demo → Itens Conectados, após conectar o conector MeuPluggy.") from exc
    pluggy = PluggyClient(settings)
    stage = "item"
    try:
        item = await pluggy.get_item(item_id)
        connector = item.get("connector") or {}
        if str(connector.get("id") or item.get("connectorId")) != "200":
            raise HTTPException(422, "Este item não usa o conector MeuPluggy (ID 200). Configure o MeuPluggy no Dashboard.")
        status = item.get("status") or "UNKNOWN"
        consent = item.get("consentExpiresAt")
        connection = session.scalar(select(BankConnection).where(BankConnection.item_id == item_id))
        if connection is None:
            connection = BankConnection(item_id=item_id)
            session.add(connection)
            session.flush()
        connection.institution_name = connector.get("name") or "Meu Pluggy"
        connection.status = status
        connection.updated_at = utc_now()
        if consent and datetime.fromisoformat(consent.replace("Z", "+00:00")) <= datetime.now(timezone.utc):
            connection.status = "CONSENT_EXPIRED"
            session.commit()
            raise HTTPException(409, "Consentimento expirado no Meu Pluggy. Renove a conexão antes de sincronizar.")
        if status not in {"UPDATED", "PARTIAL_SUCCESS", "SUCCESS"}:
            session.commit()
            raise HTTPException(409, f"Conexão {status}. Verifique a conexão no Meu Pluggy e tente novamente.")
        stage = "accounts"
        raw_accounts = await pluggy.get_accounts(item_id)
        rules = {rule.name_key: rule.category for rule in session.scalars(select(CategoryRule)).all()}
        added = 0
        for raw_account in raw_accounts:
            account = session.scalar(select(Account).where(Account.external_id == raw_account["id"]))
            if account is None:
                account = Account(external_id=raw_account["id"], connection=connection, name=raw_account.get("name") or "Conta")
                session.add(account)
                session.flush()
            account.name = raw_account.get("name") or account.name
            account.type = raw_account.get("type") or "BANK"
            account.currency = raw_account.get("currencyCode") or "BRL"
            account.balance = raw_account.get("balance")
            stage = "transactions"
            for raw_tx in await pluggy.get_transactions(raw_account["id"]):
                if not raw_tx.get("id") or (not raw_tx.get("date") and not raw_tx.get("accountingDate")):
                    continue
                values = transaction_values(raw_tx, account.type)
                existing = session.scalar(select(Transaction).where(Transaction.account_id == account.id, Transaction.external_id == values["external_id"])) if values["external_id"] else None
                if existing is None:
                    transaction = Transaction(**values, account_id=account.id)
                    rule_category = rules.get(name_key(transaction_name(transaction)))
                    if rule_category is not None:
                        assign_rule_category(transaction, rule_category)
                    session.add(transaction)
                    added += 1
                else:
                    for field, value in values.items():
                        if field in {"category", "category_source"} and existing.category_source in {"manual", "ai", "rule"}:
                            continue
                        setattr(existing, field, value)
                    rule_category = rules.get(name_key(transaction_name(existing)))
                    if rule_category is not None and existing.category_source != "manual":
                        assign_rule_category(existing, rule_category)
                    elif rule_category is None and existing.category_source == "rule":
                        existing.category = values.get("category", "Uncategorized")
                        existing.category_source = values.get("category_source", "pending")
                        existing.category_confidence = None
                        existing.classification_reason = None
        session.commit()
        return {"connection_id": connection.id, "accounts_synced": len(raw_accounts), "transactions_added": added}
    except PluggyConfigurationError as exc:
        session.rollback()
        raise HTTPException(503, str(exc)) from exc
    except PluggyResponseError as exc:
        session.rollback()
        raise HTTPException(502, str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        session.rollback()
        status_code = exc.response.status_code
        if exc.request.url.path == "/auth" or status_code in {401, 403}:
            raise HTTPException(502, f"A Pluggy recusou as credenciais ou o acesso (HTTP {status_code}). Confira Client ID e Client Secret da mesma aplicação usada no Demo.") from exc
        if stage == "item" and status_code == 404:
            raise HTTPException(404, "Item não encontrado na aplicação Pluggy. Copie o Item ID completo em Aplicações → Demo → Itens Conectados e confira as credenciais dessa aplicação.") from exc
        if status_code == 429:
            raise HTTPException(503, "A Pluggy limitou as requisições (HTTP 429). Tente novamente mais tarde.") from exc
        raise HTTPException(502, f"A Pluggy falhou ao consultar {stage} (HTTP {status_code}).") from exc
    except httpx.TimeoutException as exc:
        session.rollback()
        raise HTTPException(504, f"Tempo esgotado ao consultar {stage} na Pluggy.") from exc
    except httpx.HTTPError as exc:
        session.rollback()
        raise HTTPException(502, f"Falha de comunicação com a Pluggy ao consultar {stage}.") from exc
    except Exception:
        session.rollback()
        raise
