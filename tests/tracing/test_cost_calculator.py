from __future__ import annotations
"""Tests for cost_calculator.py — provider pricing and cost computation."""

import pytest


class TestCalculateCost:
    """Cost calculation for known and unknown providers/models."""

    def test_openai_gpt4o_mini_cost(self):
        """OpenAI gpt-4o-mini: $0.15/1K input, $0.60/1K output."""
        cost = calculate_cost("openai", "gpt-4o-mini", input_tokens=1500, output_tokens=800)
        expected = (1500 / 1000 * 0.15) + (800 / 1000 * 0.60)
        assert cost == pytest.approx(expected, rel=1e-6)

    def test_openai_gpt4o_cost(self):
        """OpenAI gpt-4o: $2.50/1K input, $10.00/1K output."""
        cost = calculate_cost("openai", "gpt-4o", input_tokens=1000, output_tokens=1000)
        expected = (1000 / 1000 * 2.50) + (1000 / 1000 * 10.00)
        assert cost == pytest.approx(expected, rel=1e-6)

    def test_deepseek_chat_cost(self):
        """DeepSeek chat: $0.27/1K input, $1.10/1K output."""
        cost = calculate_cost("deepseek", "deepseek-chat", input_tokens=2000, output_tokens=500)
        expected = (2000 / 1000 * 0.27) + (500 / 1000 * 1.10)
        assert cost == pytest.approx(expected, rel=1e-6)

    def test_deepseek_reasoner_cost(self):
        """DeepSeek reasoner: $0.55/1K input, $2.19/1K output."""
        cost = calculate_cost("deepseek", "deepseek-reasoner", input_tokens=1000, output_tokens=2000)
        expected = (1000 / 1000 * 0.55) + (2000 / 1000 * 2.19)
        assert cost == pytest.approx(expected, rel=1e-6)

    def test_glm_flash_free(self):
        """GLM-4-Flash is free tier — returns 0.0."""
        cost = calculate_cost("glm", "glm-4-flash", input_tokens=5000, output_tokens=3000)
        assert cost == 0.0

    def test_glm_plus_cost(self):
        """GLM-4-Plus: $7.00/1K both input and output."""
        cost = calculate_cost("glm", "glm-4-plus", input_tokens=1000, output_tokens=1000)
        assert cost == pytest.approx(14.0, rel=1e-6)

    def test_edge_tts_free(self):
        """Edge TTS is always free."""
        cost = calculate_cost("edge_tts", "default", input_tokens=0, output_tokens=0)
        assert cost == 0.0

    def test_gpt_sovits_free(self):
        """GPT-SoVITS is local/free."""
        cost = calculate_cost("gpt_sovits", "default", input_tokens=0, output_tokens=0)
        assert cost == 0.0

    def test_unknown_provider_returns_zero(self):
        """Unknown provider returns 0.0 without error."""
        cost = calculate_cost("nonexistent", "gpt-5", input_tokens=1000, output_tokens=1000)
        assert cost == 0.0

    def test_unknown_model_returns_zero(self):
        """Known provider but unknown model returns 0.0."""
        cost = calculate_cost("openai", "gpt-5-future", input_tokens=1000, output_tokens=1000)
        assert cost == 0.0

    def test_zero_tokens_returns_zero(self):
        """Zero tokens → zero cost even for paid models."""
        cost = calculate_cost("openai", "gpt-4o", input_tokens=0, output_tokens=0)
        assert cost == 0.0

    def test_case_insensitive_provider(self):
        """Provider name is case-insensitive."""
        cost_lower = calculate_cost("openai", "gpt-4o-mini", input_tokens=1000, output_tokens=1000)
        cost_upper = calculate_cost("OPENAI", "gpt-4o-mini", input_tokens=1000, output_tokens=1000)
        assert cost_lower == cost_upper

    def test_partial_model_prefix_match(self):
        """Model prefix match fallback works (e.g. 'gpt-4o-mini-2024-01-01' matches 'gpt-4o-mini')."""
        cost = calculate_cost("openai", "gpt-4o-mini-2024-08-20", input_tokens=1000, output_tokens=1000)
        expected = (1000 / 1000 * 0.15) + (1000 / 1000 * 0.60)
        assert cost == pytest.approx(expected, rel=1e-6)


class TestProviderPricing:
    """Provider pricing table coverage."""

    @pytest.mark.parametrize("provider,model,expected_input,expected_output", [
        ("openai", "gpt-4o", 2.50, 10.00),
        ("openai", "gpt-4o-mini", 0.15, 0.60),
        ("openai", "gpt-4-turbo", 10.00, 30.00),
        ("openai", "gpt-3.5-turbo", 0.50, 1.50),
        ("deepseek", "deepseek-chat", 0.27, 1.10),
        ("deepseek", "deepseek-reasoner", 0.55, 2.19),
        ("glm", "glm-4-flash", 0.00, 0.00),
        ("glm", "glm-4-plus", 7.00, 7.00),
        ("glm", "glm-4-air", 0.50, 0.50),
        ("glm", "glm-4-long", 1.00, 1.00),
        ("edge_tts", "default", 0.00, 0.00),
        ("gpt_sovits", "default", 0.00, 0.00),
    ])
    def test_pricing_entry_exists(self, provider, model, expected_input, expected_output):
        """All required providers and models have pricing entries."""
        assert provider in PROVIDER_PRICING
        assert model in PROVIDER_PRICING[provider]
        actual_input, actual_output = PROVIDER_PRICING[provider][model]
        assert actual_input == expected_input
        assert actual_output == expected_output
