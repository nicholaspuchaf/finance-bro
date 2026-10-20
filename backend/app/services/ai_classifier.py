import json

import httpx
from pydantic import ValidationError

from app.config import Settings
from app.schemas import CATEGORIES, CategoryResult


class AIConfigurationError(RuntimeError):
    pass


class AIResponseError(RuntimeError):
    pass


class OpenAIClassifier:
    """Small provider adapter; replaceable without changing API or persistence."""

    def __init__(self, settings: Settings):
        self.settings = settings

    async def classify(self, description: str, amount: str, currency: str) -> CategoryResult:
        if not self.settings.openai_api_key:
            raise AIConfigurationError("Configure OPENAI_API_KEY no arquivo .env para classificar transações.")

        schema = {
            "type": "object",
            "properties": {
                "category": {"type": "string", "enum": CATEGORIES},
                "confidence": {"type": "number"},
                "merchant": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                "reasoning": {"type": "string"},
            },
            "required": ["category", "confidence", "merchant", "reasoning"],
            "additionalProperties": False,
        }
        payload = {
            "model": self.settings.openai_model,
            "input": [
                {"role": "system", "content": "Classifique a transação financeira. Não invente dados. Responda em português."},
                {"role": "user", "content": f"Descrição: {description[:300]}\nValor: {amount} {currency}"},
            ],
            "text": {"format": {"type": "json_schema", "name": "transaction_category", "strict": True, "schema": schema}},
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.openai.com/v1/responses",
                headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
                json=payload,
            )
            response.raise_for_status()
        body = response.json()
        if body.get("status") not in (None, "completed"):
            raise AIResponseError("A classificação não foi concluída. Tente novamente.")
        content = [item for output in body.get("output", []) for item in output.get("content", [])]
        if any(item.get("type") == "refusal" for item in content):
            raise AIResponseError("A IA recusou a classificação desta transação.")
        output_text = body.get("output_text") or next((item.get("text") for item in content if item.get("type") == "output_text"), None)
        if not output_text:
            raise AIResponseError("A IA não retornou uma classificação.")
        try:
            return CategoryResult.model_validate(json.loads(output_text))
        except (ValueError, ValidationError) as exc:
            raise AIResponseError("A IA retornou uma classificação inválida.") from exc
