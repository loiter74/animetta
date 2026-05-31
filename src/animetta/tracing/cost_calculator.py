"""
Cost Calculator — compute LLM cost from provider + model + token counts.

Maintains a PROVIDER_PRICING dictionary with per-model input/output prices.
Call calculate_cost(provider, model, input_tokens, output_tokens) to get USD.

Usage:
    from anima.tracing.cost_calculator import calculate_cost
    cost = calculate_cost("openai", "gpt-4o-mini", input_tokens=1500, output_tokens=800)
"""


from loguru import logger

# TODO: Update pricing as of 2026-05-13
# Prices are per 1,000 tokens (input / output).
# Sources:
#   OpenAI: https://openai.com/api/pricing/
#   DeepSeek: https://api-docs.deepseek.com/quick_start/pricing
#   GLM: https://open.bigmodel.cn/pricing
#   Edge TTS: Free (Microsoft)
#   GPT-SoVITS: Local / free

PROVIDER_PRICING: dict[str, dict[str, tuple[float, float]]] = {
    # ── OpenAI ──
    "openai": {
        "gpt-4o":              (2.50, 10.00),
        "gpt-4o-mini":         (0.15,  0.60),
        "gpt-4-turbo":         (10.00, 30.00),
        "gpt-3.5-turbo":       (0.50,  1.50),
    },
    # ── DeepSeek ──
    "deepseek": {
        "deepseek-chat":       (0.27,  1.10),
        "deepseek-reasoner":   (0.55,  2.19),
    },
    # ── GLM (ZhipuAI) ──
    "glm": {
        "glm-4-flash":         (0.00,  0.00),   # free tier
        "glm-4-plus":          (7.00,  7.00),
        "glm-4-air":           (0.50,  0.50),
        "glm-4-long":          (1.00,  1.00),
    },
    # ── Edge TTS ──
    "edge_tts": {
        "default":             (0.00,  0.00),   # free
    },
    # ── GPT-SoVITS ──
    "gpt_sovits": {
        "default":             (0.00,  0.00),   # local
    },
}


def calculate_cost(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """Calculate the USD cost of an LLM call.

    Args:
        provider: Provider name (e.g., "openai", "deepseek", "glm").
        model: Model name (e.g., "gpt-4o-mini", "deepseek-chat").
        input_tokens: Number of prompt tokens.
        output_tokens: Number of completion tokens.

    Returns:
        Cost in USD. Returns 0.0 if provider/model not in pricing table.
    """
    provider_prices = PROVIDER_PRICING.get(provider.lower())
    if provider_prices is None:
        logger.debug(f"[CostCalc] Unknown provider: {provider}")
        return 0.0

    # Try exact model match first, then fallback to partial match
    prices: tuple[float, float] | None = provider_prices.get(model)
    if prices is None:
        # Partial match: find the longest known prefix that matches the model
        best_match: tuple[float, float] | None = None
        best_len = 0
        for known_model, known_prices in provider_prices.items():
            if model.startswith(known_model) and len(known_model) > best_len:
                best_match = known_prices
                best_len = len(known_model)
        prices = best_match

    if prices is None:
        logger.debug(f"[CostCalc] Unknown model: {provider}/{model}")
        return 0.0

    input_price_per_1k, output_price_per_1k = prices
    input_cost = (input_tokens / 1000.0) * input_price_per_1k
    output_cost = (output_tokens / 1000.0) * output_price_per_1k

    return round(input_cost + output_cost, 6)
