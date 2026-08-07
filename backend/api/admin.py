"""Admin API endpoints for user management (RBAC)."""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
import logging

from backend.models import get_db
from backend.models.schemas import User
from backend.core.security import require_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])


class UserListItem(BaseModel):
    id: str
    email: str
    name: str
    role: str
    is_active: bool
    byok_enabled: bool
    document_count: int = 0

    class Config:
        from_attributes = True


class RoleUpdate(BaseModel):
    role: str = Field(..., pattern="^(admin|member)$")


@router.get("/users", response_model=List[UserListItem])
async def list_users(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """List all users (admin only)."""
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [
        UserListItem(
            id=u.id,
            email=u.email,
            name=u.name,
            role=u.role,
            is_active=u.is_active,
            byok_enabled=u.byok_enabled,
            document_count=len(u.documents),
        )
        for u in users
    ]


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    body: RoleUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Change a user's role (admin only). Cannot demote yourself."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = body.role
    db.commit()
    logger.info(f"Admin {admin.id} changed user {user_id} role to {body.role}")
    return {"message": f"User role updated to {body.role}", "user_id": user_id}


@router.patch("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Deactivate a user (admin only). Cannot deactivate yourself."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    db.commit()
    logger.info(f"Admin {admin.id} deactivated user {user_id}")
    return {"message": "User deactivated", "user_id": user_id}
