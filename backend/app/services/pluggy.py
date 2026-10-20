from datetime import date
from decimal import Decimal

import httpx

from app.config import Settings


class PluggyConfigurationError(RuntimeError):
    pass


class PluggyResponseError(RuntimeError):
    pass


class PluggyClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._api_key: str | None = None

    async def _authenticate(self) -> str:
        if self._api_key:
            return self._api_key
        if not self.settings.pluggy_client_id or not self.settings.pluggy_client_secret:
            raise PluggyConfigurationError("Configure PLUGGY_CLIENT_ID e PLUGGY_CLIENT_SECRET no arquivo .env.")
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{self.settings.pluggy_api_url}/auth",
                json={"clientId": self.settings.pluggy_client_id, "clientSecret": self.settings.pluggy_client_secret},
            )
            response.raise_for_status()
        self._api_key = response.json()["apiKey"]
        return self._api_key

    async def _request(self, method: str, path: str, **kwargs):
        api_key = await self._authenticate()
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.request(
                method, f"{self.settings.pluggy_api_url}{path}",
                headers={"X-API-KEY": api_key}, **kwargs,
            )
            response.raise_for_status()
        return response.json()

    async def create_connect_token(self, user_id: str) -> str:
        result = await self._request(
            "POST", "/connect_token",
            json={"options": {"clientUserId": user_id, "avoidDuplicates": True}},
        )
        return result["accessToken"]

    async def get_item(self, item_id: str) -> dict:
        return await self._request("GET", f"/items/{item_id}")

    async def get_accounts(self, item_id: str) -> list[dict]:
        results: list[dict] = []
        page_number = 1
        total_pages = 1
        while page_number <= total_pages:
            page = await self._request("GET", "/accounts", params={"itemId": item_id, "page": page_number, "pageSize": 500})
            results.extend(page.get("results", []))
            total_pages = int(page.get("totalPages") or page_number)
            page_number += 1
        return results

    async def get_transactions(self, account_id: str) -> list[dict]:
        results: list[dict] = []
        path = "/v2/transactions"
        params: dict[str, str] | None = {"accountId": account_id}
        seen_cursors: set[str] = set()
        while True:
            page = await self._request("GET", path, **({"params": params} if params else {}))
            results.extend(page.get("results", []))
            next_query = page.get("next")
            if not next_query:
                break
            if not isinstance(next_query, str) or not next_query.startswith("?") or next_query in seen_cursors:
                raise PluggyResponseError("Resposta de paginação inválida da Pluggy.")
            seen_cursors.add(next_query)
            path = f"/v2/transactions{next_query}"
            params = None
        return results


def to_decimal(value) -> Decimal:
    return Decimal(str(value or 0))


def transaction_values(raw: dict, account_type: str | None = None) -> dict:
    raw_date = raw.get("date") or raw.get("accountingDate")
    normalized_date = date.fromisoformat(raw_date[:10])
    amount = to_decimal(raw.get("amount"))
    transaction_type = (raw.get("type") or "").upper()
    # Normalize expenses as positive and income/credits as negative in the UI.
    if account_type != "CREDIT" and transaction_type in {"CREDIT", "DEBIT"}:
        amount = -abs(amount) if transaction_type == "CREDIT" else abs(amount)
    return {
        "external_id": raw.get("id"),
        "date": normalized_date,
        "description": raw.get("description") or (raw.get("merchant") or {}).get("name") or "Transação",
        "merchant": (raw.get("merchant") or {}).get("name"),
        "amount": amount,
        "currency": raw.get("currencyCode") or "BRL",
        "pending": raw.get("status") == "PENDING",
        "operation_type": raw.get("operationType"),
        **({"category": raw["category"], "category_source": "pluggy"} if raw.get("category") else {}),
    }
