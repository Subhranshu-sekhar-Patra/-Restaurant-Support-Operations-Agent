"""Authentication dependencies for FastAPI."""

from fastapi import Header, HTTPException, Depends
from uuid import UUID
from typing import Optional
from app.config import settings, DEMO_USERS


class AuthContext:
    """Resolved authentication context for a request."""

    def __init__(self, user_id: UUID, user_name: str, role: str = "CUSTOMER"):
        self.user_id = user_id
        self.user_name = user_name
        self.role = role


async def get_current_user(
    x_demo_user: Optional[str] = Header(None, alias="X-Demo-User"),
    authorization: Optional[str] = Header(None),
) -> AuthContext:
    """
    Resolve user identity based on AUTH_MODE.

    - demo mode: reads X-Demo-User header (alice|bob|carol)
    - jwt mode: validates Supabase JWT from Authorization header
    """
    if settings.AUTH_MODE == "demo":
        if settings.APP_ENV == "production":
            raise HTTPException(status_code=403, detail="Demo auth disabled in production")

        if not x_demo_user:
            raise HTTPException(
                status_code=401,
                detail="Missing X-Demo-User header. Use: alice, bob, or carol",
            )

        user_key = x_demo_user.strip().lower()
        if user_key not in DEMO_USERS:
            raise HTTPException(
                status_code=401,
                detail=f"Unknown demo user '{x_demo_user}'. Use: alice, bob, or carol",
            )

        return AuthContext(
            user_id=UUID(DEMO_USERS[user_key]),
            user_name=user_key.capitalize(),
            role="CUSTOMER",
        )

    elif settings.AUTH_MODE == "jwt":
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

        token = authorization.replace("Bearer ", "")
        try:
            from jose import jwt

            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid token: no sub claim")

            return AuthContext(
                user_id=UUID(user_id),
                user_name=payload.get("email", "Unknown"),
                role=payload.get("role", "CUSTOMER"),
            )
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

    raise HTTPException(status_code=500, detail=f"Unknown AUTH_MODE: {settings.AUTH_MODE}")
