"""Test suite for priority rules - deterministic classification."""

import pytest
from app.workflows.rules import compute_priority


class TestPriorityRules:
    """Test deterministic priority computation."""

    def test_payment_deducted_not_confirmed_high(self):
        """Payment with DEDUCTED_NOT_CONFIRMED should be HIGH."""
        result = compute_priority(
            category="PAYMENT",
            sentiment="NEGATIVE",
            model_urgency="MEDIUM",
            description="My payment was deducted but order failed.",
            payment_status="DEDUCTED_NOT_CONFIRMED",
        )
        assert result == "HIGH"

    def test_payment_failed_high(self):
        """Payment with FAILED status should be HIGH."""
        result = compute_priority(
            category="PAYMENT",
            sentiment="NEGATIVE",
            model_urgency="LOW",
            description="My payment failed.",
            payment_status="FAILED",
        )
        assert result == "HIGH"

    def test_payment_keyword_charged(self):
        """Payment with 'charged' keyword should be HIGH."""
        result = compute_priority(
            category="PAYMENT",
            sentiment="NEGATIVE",
            model_urgency="LOW",
            description="I was charged but got no food.",
        )
        assert result == "HIGH"

    def test_safety_allergy_high(self):
        """Allergy mention should be HIGH regardless of category."""
        result = compute_priority(
            category="ORDER",
            sentiment="NEUTRAL",
            model_urgency="LOW",
            description="I have a severe allergy and received the wrong item.",
        )
        assert result == "HIGH"

    def test_safety_food_poisoning_high(self):
        """Food poisoning should be HIGH."""
        result = compute_priority(
            category="ORDER",
            sentiment="NEGATIVE",
            model_urgency="LOW",
            description="I got food poisoning from the food.",
        )
        assert result == "HIGH"

    def test_negative_high_urgency(self):
        """Negative sentiment + high urgency -> HIGH."""
        result = compute_priority(
            category="ORDER",
            sentiment="NEGATIVE",
            model_urgency="HIGH",
            description="Very bad experience.",
        )
        assert result == "HIGH"

    def test_delivery_active_order_medium(self):
        """Delivery issue with active order -> MEDIUM."""
        result = compute_priority(
            category="DELIVERY",
            sentiment="NEUTRAL",
            model_urgency="LOW",
            description="My delivery is very late.",
            order_status="OUT_FOR_DELIVERY",
        )
        assert result == "MEDIUM"

    def test_wrong_items_medium(self):
        """Wrong items should be MEDIUM."""
        result = compute_priority(
            category="ORDER",
            sentiment="NEUTRAL",
            model_urgency="LOW",
            description="I received wrong items in my order.",
        )
        assert result == "MEDIUM"

    def test_low_priority_default(self):
        """Default case should be LOW."""
        result = compute_priority(
            category="OTHER",
            sentiment="NEUTRAL",
            model_urgency="LOW",
            description="How do I change my account email?",
        )
        assert result == "LOW"

    def test_model_cannot_lower_rule_high(self):
        """Model urgency cannot lower a rule-based HIGH."""
        result = compute_priority(
            category="PAYMENT",
            sentiment="NEGATIVE",
            model_urgency="LOW",
            description="Money was charged but order cancelled.",
            payment_status="DEDUCTED_NOT_CONFIRMED",
        )
        assert result == "HIGH"

    def test_model_can_raise_to_high(self):
        """Model urgency can raise to HIGH when combined with negative sentiment."""
        result = compute_priority(
            category="ORDER",
            sentiment="NEGATIVE",
            model_urgency="HIGH",
            description="This is unacceptable service.",
        )
        assert result == "HIGH"
