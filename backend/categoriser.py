import json
import logging
import os
import re

import httpx

logger = logging.getLogger("finsight.categoriser")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# Any OpenRouter chat model id; cheap + JSON-capable is all this needs
LLM_MODEL = os.getenv("LLM_MODEL", "anthropic/claude-haiku-5.5")
LLM_BATCH_SIZE = 25
# Max LLM calls per user per day (each call categorises up to LLM_BATCH_SIZE merchants)
LLM_DAILY_CALL_LIMIT = int(os.getenv("LLM_DAILY_CALL_LIMIT", "20"))

VALID_CATEGORIES = {"Groceries", "Transport", "Dining", "Subscriptions", "Utilities", "Income", "Other"}

RULES = {
    "Groceries": ["tesco", "sainsbury", "asda", "morrisons", "lidl", "aldi", "waitrose", "marks & spencer", "m&s", "co-op", "coop", "spar", "ocado", "iceland"],
    "Transport": ["trainline", "tfl", "uber", "bolt", "national rail", "bus", "tube", "railway", "transport", "parking", "petrol", "fuel", "shell", "bp ", "esso"],
    "Dining": ["mcdonald", "kfc", "subway", "costa", "starbucks", "greggs", "nando", "pizza", "burger", "cafe", "restaurant", "deliveroo", "just eat", "uber eats"],
    "Subscriptions": ["netflix", "spotify", "amazon prime", "disney", "apple", "google", "microsoft", "adobe", "github", "dropbox", "gym", "membership"],
    "Utilities": ["british gas", "octopus", "bulb", "severn trent", "thames water", "bt ", "virgin media", "sky ", "ee ", "vodafone", "o2 ", "three"],
    "Income": ["salary", "payroll", "wages", "bacs", "employer", "hmrc", "dividend", "interest earned"],
}

SYSTEM_PROMPT = (
    "You categorise UK bank card transactions. For each numbered merchant, choose exactly one category from: "
    "Groceries, Transport, Dining, Subscriptions, Utilities, Income, Other. "
    'Reply with JSON only, in the form {"categories": {"1": "Dining", "2": "Other"}}, with one entry per number.'
)


def rule_based_category(merchant_name: str, description: str) -> str | None:
    haystack = f"{merchant_name or ''} {description or ''}".lower()
    for category, keywords in RULES.items():
        for keyword in keywords:
            if keyword in haystack:
                return category
    return None


def normalise_merchant(name: str | None) -> str:
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def _parse_json(content: str) -> dict:
    # Some models wrap JSON in ```json fences despite instructions
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content)
    return json.loads(content)


def llm_categorise_batch(merchants: list[str]) -> dict[str, str] | None:
    """Categorise up to LLM_BATCH_SIZE merchants in one call.

    Returns {merchant: category} (unknown answers become "Other"),
    or None if the call fails so the caller can fall back.
    """
    if not OPENROUTER_API_KEY or not merchants:
        return None
    numbered = "\n".join(f"{i}. {m}" for i, m in enumerate(merchants, start=1))
    try:
        response = httpx.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": LLM_MODEL,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": numbered},
                ],
            },
            timeout=30,
        )
        if response.status_code != 200:
            logger.warning("LLM categorisation failed with status %s", response.status_code)
            return None
        content = response.json()["choices"][0]["message"]["content"]
        answers = _parse_json(content).get("categories", {})
    except Exception as exc:  # network, timeout, bad JSON: all fall back
        logger.warning("LLM categorisation failed: %s", type(exc).__name__)
        return None

    result = {}
    for i, merchant in enumerate(merchants, start=1):
        category = str(answers.get(str(i), "")).strip()
        result[merchant] = category if category in VALID_CATEGORIES else "Other"
    return result
