"""
Auth service for oauth2-proxy integration.
Gets user info from X-Auth-Request-* headers set by oauth2-proxy.
"""
from datetime import datetime
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
import uuid

from database import get_db


async def get_current_user_from_proxy(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Get current user from oauth2-proxy headers.
    oauth2-proxy sets these headers after successful authentication:
    - X-Auth-Request-Email: user's email
    - X-Auth-Request-User: username or sub
    - X-Auth-Request-Preferred-Username: preferred username
    - X-Auth-Request-Groups: user groups (comma-separated)
    """
    from models.user import User
    
    # Get user info from oauth2-proxy headers (nginx forwards these)
    email = request.headers.get("X-Auth-Request-Email")
    username = request.headers.get("X-Auth-Request-Preferred-Username") or request.headers.get("X-Auth-Request-User")
    groups = request.headers.get("X-Auth-Request-Groups", "")
    
    # Debug: log received headers
    print(f"Auth headers: email={email}, username={username}, groups={groups}")
    
    if not email and not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Missing X-Auth-Request-* headers from proxy.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Use email as primary identifier, fallback to username
    user_identifier = email or username
    
    # Find user by email first, then by username
    user = None
    if email:
        user = db.query(User).filter(User.email == email).first()
    if not user and username:
        user = db.query(User).filter(User.username == username).first()
    
    if not user:
        # Auto-create user from oauth2-proxy info
        user = User(
            id=str(uuid.uuid4()),
            email=email or f"{username}@oauth2-proxy",
            username=username or email.split("@")[0] if email else str(uuid.uuid4())[:8],
            hashed_password="",  # No local password for SSO users
            full_name=username,
            role="user",
            is_active="true",
            created_at=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"Created new user from oauth2-proxy: {user.email}")
    
    return user


async def get_current_active_user(current_user = Depends(get_current_user_from_proxy)):
    """Get current active user"""
    if current_user.is_active != "true":
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# Alias for compatibility with existing code
get_current_user = get_current_user_from_proxy
