"""Input and output guardrails for the agent."""

import re
from app.observability.logging import get_logger

logger = get_logger(__name__)

# Maximum input message length
MAX_INPUT_LENGTH = 2000

# Patterns that suggest prompt injection attempts
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+(all\s+)?above\s+instructions",
    r"disregard\s+(all\s+)?previous",
    r"forget\s+(all\s+)?previous",
    r"you\s+are\s+now\s+(?:a\s+)?(?:different|new)",
    r"pretend\s+(?:to\s+be|you\s+are)",
    r"(?:print|show|reveal|display|output)\s+(?:your\s+)?(?:system\s+)?(?:prompt|instructions|rules)",
    r"(?:what\s+(?:is|are)\s+your)\s+(?:system\s+)?(?:prompt|instructions|rules)",
    r"(?:what\s*(?:'s|\s+is)\s+|(?:show|reveal|give|tell)\s+(?:me\s+)?)(?:your\s+)?(?:api|secret|service.?role)\s*key",
    r"(?:show|give|list)\s+(?:me\s+)?(?:all|every)\s+(?:customer|user|order)",
    r"i\s*'?\s*m\s+an?\s+admin",
    r"act\s+as\s+(?:an?\s+)?(?:admin|root|superuser)",
    r"sudo\s+",
    r"<\s*(?:script|img|iframe)",
    r"(?:DROP|DELETE|UPDATE|INSERT|ALTER|CREATE)\s+(?:TABLE|DATABASE|INDEX)",
]

# Compiled patterns for efficiency
_injection_re = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


class InputGuardError(Exception):
    """Raised when input fails guardrail checks."""

    def __init__(self, reason: str, message: str = ""):
        self.reason = reason
        self.message = message
        super().__init__(message)


def guard_input(user_message: str) -> None:
    """
    Layer 1 input guardrails.
    Raises InputGuardError if the message fails checks.
    Note: This is heuristic-based. Real protection comes from
    server-injected user_id and ownership-filtered queries.
    """
    if not user_message or not user_message.strip():
        raise InputGuardError("empty_input", "Please enter a message.")

    if len(user_message) > MAX_INPUT_LENGTH:
        raise InputGuardError(
            "too_long",
            f"Message is too long ({len(user_message)} chars). Maximum is {MAX_INPUT_LENGTH}.",
        )

    for pattern in _injection_re:
        if pattern.search(user_message):
            logger.warning(
                "Injection attempt detected",
                extra={"extra_data": {"pattern": pattern.pattern, "input_preview": user_message[:100]}},
            )
            raise InputGuardError(
                "injection_detected",
                "I can't help with that request. I'm here to assist with your restaurant orders, policies, and support tickets.",
            )
