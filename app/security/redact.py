"""Output redaction - scrubs secrets from responses before they reach users."""

import re
from typing import Optional

# Patterns matching common secret formats
SECRET_PATTERNS = [
    r"sk-[a-zA-Z0-9]{20,}",                      # OpenAI-style keys
    r"sb_secret_[a-zA-Z0-9_\-]{20,}",             # Supabase service role keys
    r"sb_publishable_[a-zA-Z0-9_\-]{20,}",        # Supabase anon keys
    r"eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+",  # JWT tokens
    r"AIza[a-zA-Z0-9_\-]{30,}",                   # Google API keys
    r"postgresql(\+psycopg)?://[^\s]+",            # Database connection strings
    r"SUPABASE_SERVICE_ROLE_KEY\s*=\s*\S+",        # Env var assignments
    r"service_role\s*[=:]\s*\S+",
]

_secret_re = [re.compile(p) for p in SECRET_PATTERNS]


def redact_secrets(text: Optional[str]) -> Optional[str]:
    """Replace any secret patterns found in text with [REDACTED]."""
    if not text:
        return text

    result = text
    for pattern in _secret_re:
        result = pattern.sub("[REDACTED]", result)
    return result
