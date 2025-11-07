"""
API Router for User Authentication (Register, Login)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.models.database import get_db
from backend.models.schemas import User
from backend.api.schemas import UserCreate, UserResponse, LoginResponse, Token
from backend.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token
from backend.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

def get_user_by_email(db: Session, email: str) -> User | None:
    """Helper function to fetch a user by email."""
    return db.query(User).filter(User.email == email).first()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    user_in: UserCreate, 
    db: Session = Depends(get_db)
):
    """
    Create a new user.
    """
    db_user = get_user_by_email(db, email=user_in.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    hashed_password = get_password_hash(user_in.password)
    
    db_user = User(
        email=user_in.email,
        name=user_in.name,
        hashed_password=hashed_password,
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

@router.post("/login", response_model=LoginResponse)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    """
    User login, returns JWT access and refresh tokens.
    """
    user = get_user_by_email(db, email=form_data.username) # OAuth2 form uses 'username' for email
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user"
        )
    
    token_data = {"user_id": user.id}
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)
    
    token = Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )
    
    return LoginResponse(token=token, user=user)