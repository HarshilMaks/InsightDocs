"""
Security utilities for password hashing, token creation,
and user dependency injection.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.schemas import User
from backend.models.database import get_db
from backend.api.schemas import TokenData

# --- Password Hashing ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed one."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a plain password."""
    return pwd_context.hash(password)

# --- JWT Token Creation ---

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.app.api_prefix}/auth/login")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Creates a new access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.security.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.security.secret_key, 
        algorithm=settings.security.algorithm
    )
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    """Creates a new refresh token."""
    expires = datetime.now(timezone.utc) + timedelta(days=settings.security.refresh_token_expire_days)
    to_encode = data.copy()
    to_encode.update({"exp": expires})
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.security.secret_key, 
        algorithm=settings.security.algorithm
    )
    return encoded_jwt

# --- Token Verification & User Dependency ---

def decode_token(token: str) -> Optional[TokenData]:
    """Decodes a token and returns the payload."""
    try:
        payload = jwt.decode(
            token, 
            settings.security.secret_key, 
            algorithms=[settings.security.algorithm]
        )
        user_id: Optional[str] = payload.get("user_id")
        if user_id is None:
            return None
        return TokenData(user_id=user_id)
    except JWTError:
        return None

async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency to get the current user from a token.
    This will be used to protect all secure routes.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_data = decode_token(token)
    if token_data is None or token_data.user_id is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == token_data.user_id).first()
    
    if user is None or not user.is_active:
        raise credentials_exception
        
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    FastAPI dependency to get the current *active* user.
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user