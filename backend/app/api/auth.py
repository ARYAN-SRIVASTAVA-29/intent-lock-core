import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.dependencies import get_current_user
from app.core.security import create_session_token, hash_password, verify_password
from app.db.session import get_db
from app.models import Merchant, User
from app.schemas.auth import AuthMeResponse, LoginRequest, LogoutResponse, MerchantSession, RegisterRequest

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def _merchant_slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:28] or "store"
    return slug


def _response(user: User, merchant: Merchant) -> AuthMeResponse:
    return AuthMeResponse(
        user_id=user.id,
        email=user.email,
        merchant=MerchantSession(
            merchant_id=merchant.id,
            merchant_name=merchant.name,
            status=merchant.status,
            onboarding_completed=merchant.onboarding_completed,
            environment=merchant.environment,
            discovery_enabled=merchant.discovery_enabled,
        ),
    )


def _set_session_cookie(response: Response, user_id: str) -> None:
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=create_session_token(user_id),
        max_age=settings.auth_session_hours * 60 * 60,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path="/",
    )


@router.post("/register", response_model=AuthMeResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)) -> AuthMeResponse:
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")

    user = User(id=f"usr_{uuid.uuid4().hex[:16]}", email=email, password_hash=hash_password(payload.password))
    merchant = Merchant(
        id=f"merchant_{_merchant_slug(payload.store_name)}_{uuid.uuid4().hex[:8]}",
        owner_user_id=user.id,
        name=payload.store_name,
        status="ONBOARDING",
        onboarding_completed=False,
        payment_test_connected=False,
        discovery_enabled=False,
        identity_active=False,
    )
    db.add(user)
    db.add(merchant)
    db.commit()
    db.refresh(user)
    db.refresh(merchant)
    _set_session_cookie(response, user.id)
    return _response(user, merchant)


@router.post("/login", response_model=AuthMeResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> AuthMeResponse:
    email = payload.email.lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    merchant = db.scalar(select(Merchant).where(Merchant.owner_user_id == user.id))
    if merchant is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Merchant profile is missing")
    _set_session_cookie(response, user.id)
    return _response(user, merchant)


@router.get("/me", response_model=AuthMeResponse)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> AuthMeResponse:
    merchant = db.scalar(select(Merchant).where(Merchant.owner_user_id == user.id))
    if merchant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Merchant profile not found")
    return _response(user, merchant)


@router.post("/logout", response_model=LogoutResponse)
def logout(response: Response) -> LogoutResponse:
    response.delete_cookie(settings.auth_cookie_name, path="/")
    return LogoutResponse(ok=True)
