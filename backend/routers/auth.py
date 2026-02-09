from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from database import get_db
from models.user import User
from services.auth_service import get_current_user, get_current_active_user

router = APIRouter()

# Response models
class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    full_name: Optional[str]
    role: str
    tenant_id: Optional[str]
    created_at: datetime


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    """
    Get current user info.
    User is identified via X-Auth-Request-* headers from oauth2-proxy.
    """
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        full_name=current_user.full_name,
        role=current_user.role,
        tenant_id=current_user.tenant_id,
        created_at=current_user.created_at
    )


@router.get("/logout-url")
async def get_logout_url():
    """
    Get the URL for logging out via oauth2-proxy.
    Frontend should redirect to this URL to logout.
    """
    # oauth2-proxy logout endpoint
    return {"logout_url": "/oauth2/sign_out"}
