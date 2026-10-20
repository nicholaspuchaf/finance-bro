from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.categories import CATEGORIES


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=40)

    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Informe o nome da tag.")
        return value.strip()


class TagRead(BaseModel):
    id: int
    name: str
    transaction_count: int


class TagBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class TransactionCreate(BaseModel):
    date: date
    description: str = Field(min_length=1, max_length=300)
    amount: Decimal = Field(max_digits=14, decimal_places=2)
    currency: str = Field(default="BRL", pattern="^BRL$")
    category: str = "Uncategorized"
    tag_ids: list[int] = Field(default_factory=list, max_length=20)

    @field_validator("amount")
    @classmethod
    def valid_amount(cls, value: Decimal) -> Decimal:
        if not value.is_finite() or value == 0:
            raise ValueError("Informe um valor finito e diferente de zero.")
        return value

    @field_validator("category")
    @classmethod
    def valid_category(cls, value: str) -> str:
        if value not in CATEGORIES:
            raise ValueError("Categoria não suportada.")
        return value


class TransactionUpdate(BaseModel):
    category: str | None = None
    notes: str | None = Field(default=None, max_length=2000)
    tag_ids: list[int] | None = Field(default=None, max_length=20)

    @field_validator("category")
    @classmethod
    def valid_category(cls, value: str | None) -> str | None:
        if value is not None and value not in CATEGORIES:
            raise ValueError("Categoria não suportada.")
        return value


class CategoryRuleCreate(BaseModel):
    category: str

    @field_validator("category")
    @classmethod
    def valid_category(cls, value: str) -> str:
        if value not in CATEGORIES:
            raise ValueError("Categoria não suportada.")
        return value


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date
    description: str
    merchant: str | None
    amount: Decimal
    currency: str
    category: str
    category_source: str
    category_confidence: float | None
    notes: str | None
    classification_reason: str | None
    operation_type: str | None
    pending: bool
    account_id: int | None
    tags: list[TagBrief]


class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: str
    currency: str
    balance: Decimal | None


class ConnectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    institution_name: str
    status: str
    item_id: str
    accounts: list[AccountRead]


class CategoryResult(BaseModel):
    category: str
    confidence: float = Field(ge=0, le=1)
    merchant: str | None = None
    reasoning: str

    @field_validator("category")
    @classmethod
    def category_must_be_supported(cls, value: str) -> str:
        if value not in CATEGORIES:
            raise ValueError("Categoria não suportada.")
        return value
