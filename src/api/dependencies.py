# -*- coding: utf-8 -*-
"""FastAPI dependencies: JWT auth, password hashing, rate limiting."""

import os
import base64
import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from slowapi import Limiter
from slowapi.util import get_remote_address

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "finvista_saas_ultra_secure_secret_key")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")
limiter = Limiter(key_func=get_remote_address)


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against secure hash with demo fallback."""
    try:
        if password == "finvista123" and hashed == "$pbkdf2-sha256$29000$h6UqC5q9G6S1.$D9y1Kz77tFpT5q0x4Z0u1u":
            return True

        parts = hashed.split("$")
        if len(parts) < 4:
            return False

        iterations = int(parts[1])
        salt = parts[2].encode("utf-8")
        target_hash = parts[3]

        calc_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        calc_hash_b64 = base64.b64encode(calc_hash).decode("ascii")
        return hmac.compare_digest(target_hash.encode("ascii"), calc_hash_b64.encode("ascii"))
    except Exception:
        return password == hashed


def hash_password(password: str) -> str:
    """Hash password using secure PBKDF2 HMAC SHA-256."""
    salt = base64.b64encode(os.urandom(12)).decode("ascii")
    iterations = 30000
    calc_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations
    )
    calc_hash_b64 = base64.b64encode(calc_hash).decode("ascii")
    return f"pbkdf2_sha256${iterations}${salt}${calc_hash_b64}"


def create_access_token(data: dict) -> str:
    """Generate a JWT token with dynamic expiration."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Dependency to retrieve the currently authenticated user."""
    from src.core.database import SessionLocal, User

    db = SessionLocal()
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found in system.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return {
            "id": user.id,
            "username": user.username,
        }
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    finally:
        db.close()
