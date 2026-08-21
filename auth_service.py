"""
Authentication service and Supabase client integration.
Supports Supabase Auth as the primary Identity Provider,
with an internal JWT provider for local offline testing when Supabase keys are unset.
"""

import os
import time
import uuid
import jwt
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-auth-key-for-local-jwt-verification-12345")
JWT_ALGORITHM = "HS256"

# In-memory local user store for standalone / offline fallback
_local_users_db: Dict[str, Dict[str, Any]] = {}


def is_supabase_configured() -> bool:
    """Check if valid Supabase credentials have been provided."""
    return bool(SUPABASE_URL and SUPABASE_KEY and not SUPABASE_URL.startswith("your_"))


def get_supabase_client():
    """Create and return a Supabase Client if configured."""
    if is_supabase_configured():
        try:
            from supabase import create_client
            return create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception:
            return None
    return None


class AuthService:
    """Manages User Sign Up, Log In, Log Out, and Token Verification."""

    @staticmethod
    def sign_up(email: str, password: str) -> Dict[str, Any]:
        """Sign up a new user via Supabase or local fallback."""
        supabase = get_supabase_client()
        if supabase:
            res = supabase.auth.sign_up({"email": email, "password": password})
            if res.user:
                return {
                    "id": str(res.user.id),
                    "email": res.user.email,
                    "created_at": str(res.user.created_at)
                }
            raise Exception("Sign up failed via Supabase")

        # Local standalone implementation
        if email in _local_users_db:
            # Idempotent or existing user
            user = _local_users_db[email]
            return {"id": user["id"], "email": user["email"], "created_at": user["created_at"]}

        user_id = str(uuid.uuid4())
        created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        _local_users_db[email] = {
            "id": user_id,
            "email": email,
            "password": password,
            "created_at": created_at
        }
        return {"id": user_id, "email": email, "created_at": created_at}

    @staticmethod
    def sign_in(email: str, password: str) -> Dict[str, Any]:
        """Sign in user and return JWT access token."""
        supabase = get_supabase_client()
        if supabase:
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                if res.session and res.user:
                    return {
                        "access_token": res.session.access_token,
                        "token_type": "bearer",
                        "refresh_token": res.session.refresh_token,
                        "user": {
                            "id": str(res.user.id),
                            "email": res.user.email,
                            "created_at": str(res.user.created_at)
                        }
                    }
            except Exception:
                raise Exception("Invalid login credentials")
            raise Exception("Invalid login credentials")

        # Local fallback authentication
        user = _local_users_db.get(email)
        if not user or user["password"] != password:
            raise Exception("Invalid login credentials")

        now = int(time.time())
        payload = {
            "sub": user["id"],
            "email": user["email"],
            "created_at": user["created_at"],
            "iat": now,
            "exp": now + 3600  # 1 hour expiration
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return {
            "access_token": token,
            "token_type": "bearer",
            "refresh_token": f"refresh_{uuid.uuid4().hex}",
            "user": {
                "id": user["id"],
                "email": user["email"],
                "created_at": user["created_at"]
            }
        }

    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """Verify JWT token and extract user metadata."""
        supabase = get_supabase_client()
        if supabase:
            try:
                user_res = supabase.auth.get_user(token)
                if user_res and user_res.user:
                    return {
                        "id": str(user_res.user.id),
                        "email": user_res.user.email,
                        "created_at": str(user_res.user.created_at)
                    }
            except Exception:
                raise Exception("Invalid or expired token")
            raise Exception("Invalid or expired token")

        # Local JWT Verification
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return {
                "id": payload.get("sub"),
                "email": payload.get("email"),
                "created_at": payload.get("created_at")
            }
        except jwt.PyJWTError:
            raise Exception("Invalid or expired token")

    @staticmethod
    def sign_out(token: str) -> None:
        """Sign out user from Supabase session."""
        supabase = get_supabase_client()
        if supabase:
            try:
                supabase.auth.sign_out()
            except Exception:
                pass
