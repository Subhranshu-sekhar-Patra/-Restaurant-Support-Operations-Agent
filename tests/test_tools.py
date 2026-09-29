"""Test suite for tool argument validation."""

import pytest
from pydantic import ValidationError

from app.tools.schemas import (
    GetOrderStatusArgs,
    GetOrderDetailsArgs,
    CreateSupportTicketArgs,
    SearchPolicyArgs,
)


class TestOrderStatusArgs:
    def test_valid_order_code(self):
        args = GetOrderStatusArgs(order_code="ORD-1005")
        assert args.order_code == "ORD-1005"

    def test_valid_6_digit_code(self):
        args = GetOrderStatusArgs(order_code="ORD-123456")
        assert args.order_code == "ORD-123456"

    def test_invalid_format_no_prefix(self):
        with pytest.raises(ValidationError):
            GetOrderStatusArgs(order_code="1005")

    def test_invalid_format_wrong_prefix(self):
        with pytest.raises(ValidationError):
            GetOrderStatusArgs(order_code="ORDER-1005")

    def test_invalid_format_letters(self):
        with pytest.raises(ValidationError):
            GetOrderStatusArgs(order_code="ORD-abc")

    def test_invalid_format_too_short(self):
        with pytest.raises(ValidationError):
            GetOrderStatusArgs(order_code="ORD-12")


class TestCreateSupportTicketArgs:
    def test_valid_description(self):
        args = CreateSupportTicketArgs(description="My order is very late and I need help.")
        assert len(args.description) > 10

    def test_too_short_description(self):
        with pytest.raises(ValidationError):
            CreateSupportTicketArgs(description="Help")

    def test_with_order_code(self):
        args = CreateSupportTicketArgs(
            description="Payment issue with my order",
            order_code="ORD-1005",
        )
        assert args.order_code == "ORD-1005"

    def test_invalid_order_code(self):
        with pytest.raises(ValidationError):
            CreateSupportTicketArgs(
                description="Payment issue with my order",
                order_code="INVALID",
            )


class TestSearchPolicyArgs:
    def test_valid_query(self):
        args = SearchPolicyArgs(query="What is the refund policy?")
        assert args.query == "What is the refund policy?"

    def test_too_short_query(self):
        with pytest.raises(ValidationError):
            SearchPolicyArgs(query="hi")
