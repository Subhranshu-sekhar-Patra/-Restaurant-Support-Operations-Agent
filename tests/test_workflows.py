"""Test suite for complaint workflow schemas and keyword fallback."""

import pytest
from pydantic import ValidationError

from app.workflows.schemas import ComplaintAnalysis
from app.workflows.complaint import keyword_fallback_classify


class TestComplaintAnalysis:
    def test_valid_analysis(self):
        analysis = ComplaintAnalysis(
            category="PAYMENT",
            sentiment="NEGATIVE",
            urgency="HIGH",
            summary="Payment deducted but order not confirmed.",
        )
        assert analysis.category == "PAYMENT"
        assert analysis.needs_human is False

    def test_invalid_category(self):
        with pytest.raises(ValidationError):
            ComplaintAnalysis(
                category="INVALID",
                sentiment="NEGATIVE",
                urgency="HIGH",
                summary="Test",
            )

    def test_invalid_sentiment(self):
        with pytest.raises(ValidationError):
            ComplaintAnalysis(
                category="PAYMENT",
                sentiment="ANGRY",
                urgency="HIGH",
                summary="Test",
            )

    def test_summary_max_length(self):
        with pytest.raises(ValidationError):
            ComplaintAnalysis(
                category="PAYMENT",
                sentiment="NEGATIVE",
                urgency="HIGH",
                summary="x" * 301,
            )

    def test_order_code_pattern(self):
        analysis = ComplaintAnalysis(
            category="ORDER",
            sentiment="NEGATIVE",
            urgency="MEDIUM",
            summary="Order issue",
            order_code="ORD-1005",
        )
        assert analysis.order_code == "ORD-1005"

    def test_invalid_order_code(self):
        with pytest.raises(ValidationError):
            ComplaintAnalysis(
                category="ORDER",
                sentiment="NEGATIVE",
                urgency="MEDIUM",
                summary="Order issue",
                order_code="INVALID",
            )


class TestKeywordFallback:
    def test_payment_classification(self):
        result = keyword_fallback_classify("My payment was deducted but no order.")
        assert result.category == "PAYMENT"
        assert result.needs_human is True

    def test_delivery_classification(self):
        result = keyword_fallback_classify("My delivery is very late and I'm still waiting.")
        assert result.category == "DELIVERY"
        assert result.needs_human is True

    def test_order_code_extraction(self):
        result = keyword_fallback_classify("Problem with ORD-1005, it was cancelled.")
        assert result.order_code == "ORD-1005"

    def test_unknown_category(self):
        result = keyword_fallback_classify("I have a general question about your service and process.")
        assert result.category == "OTHER"
        assert result.needs_human is True

    def test_sentiment_always_negative(self):
        """Fallback always sets NEGATIVE for safety."""
        result = keyword_fallback_classify("Great service but I need a refund.")
        assert result.sentiment == "NEGATIVE"
