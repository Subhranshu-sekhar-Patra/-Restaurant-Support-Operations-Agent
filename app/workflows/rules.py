"""Deterministic priority rules - code wins over the LLM."""

import re
from typing import Optional, Literal

PRIORITY_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
PRIORITY_NAMES = {0: "LOW", 1: "MEDIUM", 2: "HIGH"}

# Safety-critical keyword patterns
SAFETY_KEYWORDS = [
    r"allergy", r"allergi[ce]", r"food\s*poison", r"poisoning",
    r"unsafe", r"injury", r"injur", r"sick", r"hospital",
    r"ambulance", r"emergency", r"choking", r"vomit",
]
_safety_re = [re.compile(p, re.IGNORECASE) for p in SAFETY_KEYWORDS]


def compute_priority(
    category: str,
    sentiment: str,
    model_urgency: str,
    description: str,
    payment_status: Optional[str] = None,
    order_status: Optional[str] = None,
) -> str:
    """
    Deterministic priority rules. Rules can raise priority but the model
    can never lower a rule-based HIGH.

    Returns the final priority.
    """
    rule_priority = 0  # Start at LOW

    # Rule 1: Payment issues with failed/deducted status -> HIGH
    if category == "PAYMENT":
        payment_keywords = r"charged|deducted|debited|money\s*taken|amount\s*cut"
        if (
            payment_status in ("DEDUCTED_NOT_CONFIRMED", "FAILED")
            or re.search(payment_keywords, description, re.IGNORECASE)
        ):
            rule_priority = max(rule_priority, 2)  # HIGH

    # Rule 2: Safety-critical text -> HIGH
    for pattern in _safety_re:
        if pattern.search(description):
            rule_priority = max(rule_priority, 2)  # HIGH
            break

    # Rule 3: Negative sentiment + high urgency -> HIGH
    if sentiment == "NEGATIVE" and model_urgency == "HIGH":
        rule_priority = max(rule_priority, 2)  # HIGH

    # Rule 4: Delivery issues with active orders -> MEDIUM
    if category == "DELIVERY" and order_status and order_status not in ("DELIVERED", "CANCELLED"):
        delay_keywords = r"late|delay|slow|long\s*time|waiting|where|wrong|missing|not\s*received"
        if re.search(delay_keywords, description, re.IGNORECASE):
            rule_priority = max(rule_priority, 1)  # MEDIUM

    # Rule 5: Wrong/missing items -> MEDIUM
    wrong_item_keywords = r"wrong\s*item|missing\s*item|incorrect|not\s*what|different\s*from"
    if re.search(wrong_item_keywords, description, re.IGNORECASE):
        rule_priority = max(rule_priority, 1)  # MEDIUM

    # Final priority = max(rule_priority, model_urgency)
    # Rules can raise but model can never lower a rule-based HIGH
    model_priority_value = PRIORITY_ORDER.get(model_urgency, 0)
    final = max(rule_priority, model_priority_value)

    return PRIORITY_NAMES[final]
