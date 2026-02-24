"""Authentication API endpoints with JWT tokens + PostgreSQL users."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.database import get_db, UserORM

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/auth")
security = HTTPBearer(auto_error=False)

settings = get_settings()
JWT_SECRET = settings.secret_key
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 72  # 3-day tokens


# ─── Schemas ─────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str = "content_manager"


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    avatar: str | None = None
    created_at: str


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


# ─── Password helpers ────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


# ─── JWT helpers ─────────────────────────────────────────────────────────────

def _create_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decode_token(token: str) -> str | None:
    """Decode JWT and return user_id, or None if invalid/expired."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


# ─── ORM to response ────────────────────────────────────────────────────────

def _user_orm_to_response(user: UserORM) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role,
        avatar=user.avatar,
        created_at=user.created_at.isoformat() if user.created_at else datetime.now(timezone.utc).isoformat(),
    )


# ─── Dependency: get current user from JWT ───────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Extract and validate the current user from the Bearer JWT token."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = credentials.credentials
    user_id = _decode_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    result = await db.execute(select(UserORM).where(UserORM.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "avatar": user.avatar,
        "created_at": user.created_at.isoformat() if user.created_at else "",
    }


# ─── Seed admin on startup ──────────────────────────────────────────────────

SEED_ADMIN_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
SEED_ADMIN_EMAIL = "admin@mama.dev"
SEED_ADMIN_PASSWORD = "admin123"


async def seed_admin(db: AsyncSession) -> None:
    """Ensure the default admin user exists in the database."""
    result = await db.execute(select(UserORM).where(UserORM.id == SEED_ADMIN_ID))
    existing = result.scalar_one_or_none()
    if existing:
        logger.info("Admin user already exists", email=SEED_ADMIN_EMAIL)
        return

    admin = UserORM(
        id=SEED_ADMIN_ID,
        email=SEED_ADMIN_EMAIL,
        name="Admin",
        password_hash=_hash_password(SEED_ADMIN_PASSWORD),
        role="admin",
    )
    db.add(admin)
    await db.commit()
    logger.info("Seeded admin user", email=SEED_ADMIN_EMAIL)


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    """Authenticate a user and return a JWT token."""
    result = await db.execute(select(UserORM).where(UserORM.email == request.email))
    user = result.scalar_one_or_none()

    if not user or not _verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = _create_token(str(user.id))
    logger.info("User logged in", email=request.email)
    return AuthResponse(token=token, user=_user_orm_to_response(user))


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    """Register a new user."""
    result = await db.execute(select(UserORM).where(UserORM.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    if request.role not in ("admin", "content_manager", "reviewer"):
        raise HTTPException(status_code=400, detail="Invalid role")

    user = UserORM(
        id=uuid.uuid4(),
        email=request.email,
        name=request.name,
        password_hash=_hash_password(request.password),
        role=request.role,
    )
    db.add(user)
    await db.flush()

    token = _create_token(str(user.id))
    logger.info("User registered", email=request.email, role=request.role)
    return AuthResponse(token=token, user=_user_orm_to_response(user))


@router.get("/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)) -> UserResponse:
    """Get the current authenticated user."""
    return UserResponse(**user)
