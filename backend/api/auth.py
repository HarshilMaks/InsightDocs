"""
API Router for User Authentication (Register, Login, Google OAuth)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
import logging

from backend.models.database import get_db
from backend.models.schemas import User
from backend.api.schemas import UserCreate, UserResponse, LoginResponse, Token
from backend.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token
from backend.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

def get_user_by_email(db: Session, email: str) -> User | None:
    """Helper function to fetch a user by email."""
    return db.query(User).filter(User.email == email).first()


def _build_login_response(user: User) -> LoginResponse:
    """Create a standard LoginResponse with tokens for a given user."""
    token_data = {"user_id": user.id}
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)
    token = Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )
    return LoginResponse(
        token=token,
        user=user,
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


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
    
    # First user in the system becomes admin automatically
    user_count = db.query(User).count()
    role = "admin" if user_count == 0 else "member"
    
    db_user = User(
        email=user_in.email,
        name=user_in.name,
        hashed_password=hashed_password,
        role=role,
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
    
    return _build_login_response(user)


# ──────────────────────────────────────────────
# Google OAuth
# ──────────────────────────────────────────────

class GoogleAuthRequest(BaseModel):
    """The frontend sends the credential (ID token) from Google's sign-in response."""
    credential: str


@router.post("/google", response_model=LoginResponse)
def google_oauth_login(
    payload: GoogleAuthRequest,
    db: Session = Depends(get_db),
):
    """
    Verify a Google ID token and create or log in the user.

    Flow:
    1. Frontend uses Google Identity Services to get a credential (JWT ID token).
    2. Frontend sends that credential here.
    3. We verify it with Google's public keys.
    4. If valid, we create the user (if new) or find them (if existing).
    5. Return our own JWT, same as the normal login flow.

    Account linking: if someone registered with email/password and later
    clicks "Sign in with Google" with the same email, they get logged into
    the same account.
    """
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured on this server.",
        )

    # Verify the Google ID token
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        idinfo = id_token.verify_oauth2_token(
            payload.credential,
            google_requests.Request(),
            settings.google_client_id,
        )
    except ImportError:
        logger.error("google-auth package not installed. Cannot verify Google tokens.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google auth verification is not available.",
        )
    except ValueError as e:
        logger.warning(f"Google token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google credential. Please try again.",
        )

    # Extract user info from the verified token
    email = idinfo.get("email")
    name = idinfo.get("name", "")
    email_verified = idinfo.get("email_verified", False)

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account has no email address.",
        )

    if not email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google email is not verified.",
        )

    # Find or create the user
    user = get_user_by_email(db, email=email)

    if user is None:
        # New user — create account (no password needed for OAuth users)
        import secrets
        user_count = db.query(User).count()
        role = "admin" if user_count == 0 else "member"

        user = User(
            email=email,
            name=name or email.split("@")[0],
            # Set a random unusable password so the account exists in the DB
            # but cannot be logged into via email/password unless they set one.
            hashed_password=get_password_hash(secrets.token_urlsafe(32)),
            role=role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Created new user via Google OAuth: {email}")
    else:
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This account has been deactivated.",
            )
        logger.info(f"Google OAuth login for existing user: {email}")

    return _build_login_response(user)
