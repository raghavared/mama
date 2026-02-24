"""User management API endpoints — backed by PostgreSQL."""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db, UserORM
from .auth import get_current_user, _user_orm_to_response, UserResponse

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/users")


class RoleUpdateRequest(BaseModel):
    role: str


@router.get("", response_model=list[UserResponse])
async def list_users(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[UserResponse]:
    """List all users. Admin only."""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    result = await db.execute(select(UserORM).order_by(UserORM.created_at.desc()))
    users = result.scalars().all()
    return [_user_orm_to_response(u) for u in users]


@router.patch("/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: str,
    request: RoleUpdateRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Update a user's role. Admin only."""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    if request.role not in ("admin", "content_manager", "reviewer"):
        raise HTTPException(status_code=400, detail="Invalid role")

    import uuid as _uuid
    result = await db.execute(select(UserORM).where(UserORM.id == _uuid.UUID(user_id)))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    target.role = request.role
    await db.flush()

    logger.info("User role updated", user_id=user_id, new_role=request.role, by=user["id"])
    return _user_orm_to_response(target)
