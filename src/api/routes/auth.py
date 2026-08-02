# -*- coding: utf-8 -*-
"""Authentication routes: register, login, profile."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

from src.api.dependencies import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, example="quant_trader")
    password: str = Field(..., min_length=6, example="mysecurepassword")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(req: UserRegisterRequest):
    """Register a new quant trader account."""
    from src.core.database import SessionLocal, User

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == req.username).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username is already registered.",
            )

        new_user = User(
            username=req.username,
            hashed_password=hash_password(req.password),
        )
        db.add(new_user)
        db.commit()
        return {
            "status": "success",
            "message": (
                f"Successfully registered user '{req.username}'. "
                "You can now login to get a token."
            ),
        }
    finally:
        db.close()


@router.post("/login", response_model=TokenResponse)
def login_user(form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate credentials and return a secure JWT Access Token."""
    from src.core.database import SessionLocal, User

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == form_data.username).first()
        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = create_access_token(data={"sub": user.username})
        return {
            "access_token": token,
            "token_type": "bearer",
            "username": user.username,
        }
    finally:
        db.close()


@router.get("/me")
def get_user_profile(current_user: dict = Depends(get_current_user)):
    """Retrieve details of the currently authenticated trader."""
    return current_user
