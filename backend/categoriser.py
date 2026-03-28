import os
import httpx

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

VALID_CATEGORIES = {"Groceries", "Transport", "Dining", "Subscriptions", "Utilities", "Income", "Other"}

RULES = {
    "Groceries": ["tesco", "sainsbury", "asda", "morrisons", "lidl", "aldi", "waitrose", "marks & spencer", "m&s", "co-op", "coop", "spar", "ocado", "iceland"],
    "Transport": ["trainline", "tfl", "uber", "bolt", "national rail", "bus", "tube", "railway", "transport", "parking", "petrol", "fuel", "shell", "bp ", "esso"],
    "Dining": ["mcdonald", "kfc", "subway", "costa", "starbucks", "greggs", "nando", "pizza", "burger", "cafe", "restaurant", "deliveroo", "just eat", "uber eats"],
    "Subscriptions": ["netflix", "spotify", "amazon prime", "disney", "apple", "google", "microsoft", "adobe", "github", "dropbox", "gym", "membership"],
    "Utilities": ["british gas", "octopus", "bulb", "severn trent", "thames water", "bt ", "virgin media", "sky ", "ee ", "vodafone", "o2 ", "three"],
    "Income": ["salary", "payroll", "wages", "bacs", "employer", "hmrc", "dividend", "interest earned"],
}


def rule_based_category(merchant_name: str, description: str) -> str | None:
    haystack = f"{merchant_name or ''} {description or ''}".lower()
    for category, keywords in RULES.items():
        for keyword in keywords:
            if keyword in haystack:
                return category
    return None


def llm_category(merchant_name: str, description: str) -> str | None:
    try:
        response = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "mistralai/mistral-7b-instruct:free",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a transaction categoriser. Reply with exactly one word from this list: Groceries, Transport, Dining, Subscriptions, Utilities, Income, Other. No explanation.",
                    },
                    {
                        "role": "user",
                        "content": f"Merchant: {merchant_name}. Description: {description}",
                    },
                ],
            },
            timeout=15,
        )
        result = response.json()["choices"][0]["message"]["content"].strip()
        return result if result in VALID_CATEGORIES else "Other"
    except Exception:
        return "Other"
