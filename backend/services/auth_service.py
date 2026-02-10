"""
Auth service for oauth2-proxy integration.
Gets user info from X-Auth-Request-* headers set by oauth2-proxy.
"""
import logging
from datetime import datetime
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
import uuid

from database import get_db

logger = logging.getLogger("auth_service")


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
    
    # Log all auth-related headers for debugging
    logger.info(f"=== AUTH REQUEST ===")
    logger.info(f"  Path: {request.method} {request.url.path}")
    logger.info(f"  X-Auth-Request-Email: {email}")
    logger.info(f"  X-Auth-Request-User: {request.headers.get('X-Auth-Request-User')}")
    logger.info(f"  X-Auth-Request-Preferred-Username: {request.headers.get('X-Auth-Request-Preferred-Username')}")
    logger.info(f"  X-Auth-Request-Groups: {groups}")
    logger.info(f"  X-Forwarded-User: {request.headers.get('X-Forwarded-User')}")
    logger.info(f"  X-Forwarded-Email: {request.headers.get('X-Forwarded-Email')}")
    logger.info(f"  X-Forwarded-Preferred-Username: {request.headers.get('X-Forwarded-Preferred-Username')}")
    
    # Also try X-Forwarded-* variants (some oauth2-proxy configs use these)
    if not email:
        email = request.headers.get("X-Forwarded-Email")
        if email:
            logger.info(f"  -> Using X-Forwarded-Email: {email}")
    if not username:
        username = request.headers.get("X-Forwarded-Preferred-Username") or request.headers.get("X-Forwarded-User")
        if username:
            logger.info(f"  -> Using X-Forwarded fallback: {username}")
    
    if not email and not username:
        logger.warning(f"  NO AUTH HEADERS FOUND! All auth-related headers:")
        for key, value in request.headers.items():
            if any(x in key.lower() for x in ['auth', 'forward', 'user', 'email', 'proxy', 'cookie']):
                logger.warning(f"    {key}: {value[:100] if len(value) > 100 else value}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Missing X-Auth-Request-* headers from proxy.",
        )
    
    # Find user by email first, then by username
    user = None
    if email:
        user = db.query(User).filter(User.email == email).first()
    if not user and username:
        user = db.query(User).filter(User.username == username).first()
    
    if not user:
        # Auto-create user from oauth2-proxy info
        new_username = username or (email.split("@")[0] if email else str(uuid.uuid4())[:8])
        user = User(
            id=str(uuid.uuid4()),
            email=email or f"{username}@oauth2-proxy",
            username=new_username,
            hashed_password="",  # No local password for SSO users
            full_name=username or (email.split("@")[0] if email else None),
            role="user",
            is_active="true",
            created_at=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"  CREATED new user: id={user.id}, email={user.email}, username={user.username}")
    else:
        logger.info(f"  FOUND existing user: id={user.id}, email={user.email}, username={user.username}")
    
    return user


async def get_current_active_user(current_user = Depends(get_current_user_from_proxy)):
    """Get current active user"""
    if current_user.is_active != "true":
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# Alias for compatibility with existing code
get_current_user = get_current_user_from_proxy
