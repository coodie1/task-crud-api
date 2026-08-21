"""
AI-generated version of the Secured Auth API (A4 Stage 7 AI Rematch).
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
import os

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

app = FastAPI(title="Task API AI Auth Version")
security = HTTPBearer()


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


def get_current_user_ai(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    # AI version assumes direct call to Supabase without error formatting fallback
    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        user_res = supabase.auth.get_user(token)
        if not user_res or not user_res.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_res.user
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


@app.get("/public/info")
def public_info():
    return {"message": "Welcome stranger! This info is public."}


@app.post("/auth/signup", status_code=status.HTTP_201_CREATED)
def signup(req: SignUpRequest):
    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        res = supabase.auth.sign_up({"email": req.email, "password": req.password})
        return {"id": res.user.id, "email": res.user.email}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/login")
def login(req: LoginRequest):
    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        res = supabase.auth.sign_in_with_password({"email": req.email, "password": req.password})
        return {"access_token": res.session.access_token, "token_type": "bearer"}
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid login credentials")


@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(user=Depends(get_current_user_ai)):
    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        supabase.auth.sign_out()
    except Exception:
        pass
    return None


@app.get("/protected/profile")
def profile(user=Depends(get_current_user_ai)):
    return {"id": user.id, "email": user.email}
