import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from backend.api.schemas import ApiKeyResponse, ByokStatusResponse
from backend.core.security import get_current_user, encrypt_api_key, decrypt_api_key
from backend.models.database import get_db
from backend.models.schemas import User
from backend.utils.llm_client import probe_gemini_status

router = APIRouter(prefix="/users", tags=["User Settings"])

class APIKeyUpdate(BaseModel):
    api_key: str
    
    @field_validator('api_key')
    @classmethod
    def validate_gemini_key(cls, v: str) -> str:
        """Validate Gemini API key format."""
        if not v:
            raise ValueError("API key cannot be empty")
        
        # Remove whitespace
        v = v.strip()
        
        # Check format: starts with "AIza" and reasonable length
        if not v.startswith("AIza"):
            raise ValueError("Invalid Gemini API key format. Must start with 'AIza'")
        
        # Gemini keys are typically 39 characters (can vary slightly)
        if len(v) < 35 or len(v) > 45:
            raise ValueError(f"Invalid API key length ({len(v)} chars). Expected 35-45 characters")
        
        # Check for valid characters (alphanumeric, dash, underscore)
        if not re.match(r'^[A-Za-z0-9_-]+$', v):
            raise ValueError("API key contains invalid characters. Only alphanumeric, dash, and underscore allowed")
        
        return v

class BYOKSettings(BaseModel):
    enabled: bool

@router.put("/me/api-key", response_model=ApiKeyResponse)
def update_api_key(
    key_data: APIKeyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save or update the user's Gemini API key.
    
    The API key will be encrypted before storage.
    Validation ensures the key matches Gemini's format.
    """
    encrypted = encrypt_api_key(key_data.api_key)
    current_user.gemini_api_key_encrypted = encrypted

    status = probe_gemini_status(key_data.api_key)
    current_user.byok_enabled = status["status"] in {"healthy", "degraded"}
    db.commit()

    message = status["message"]
    if current_user.byok_enabled:
        message = f"API key updated successfully. {message}"

    return {
        "message": message,
        "byok_enabled": current_user.byok_enabled,
        "status": status["status"],
        "model_status": status["model_status"],
        "active_model": status.get("active_model"),
        "fallback_models": status.get("fallback_models", []),
        "available_models": status.get("available_models", []),
        "checked_at": status.get("checked_at"),
    }

@router.delete("/me/api-key")
def remove_api_key(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove the user's Gemini API key."""
    current_user.gemini_api_key_encrypted = None
    current_user.byok_enabled = False
    db.commit()
    return {"message": "API key removed"}

@router.patch("/me/byok-settings")
def update_byok_settings(
    settings: BYOKSettings,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toggle BYOK usage on/off."""
    if settings.enabled:
        if not current_user.gemini_api_key_encrypted:
            raise HTTPException(400, "Cannot enable BYOK without a saved API key")

        api_key = decrypt_api_key(current_user.gemini_api_key_encrypted)
        if not api_key:
            raise HTTPException(400, "Saved API key could not be decrypted")

        status = probe_gemini_status(api_key)
        if status["status"] not in {"healthy", "degraded"}:
            raise HTTPException(400, status["message"])

    current_user.byok_enabled = settings.enabled
    db.commit()
    return {"message": f"BYOK {'enabled' if settings.enabled else 'disabled'}"}

@router.get("/me/byok-status", response_model=ByokStatusResponse)
def get_byok_status(
    current_user: User = Depends(get_current_user)
):
    """Get current BYOK configuration status."""
    status = probe_gemini_status(None)
    if current_user.gemini_api_key_encrypted:
        api_key = decrypt_api_key(current_user.gemini_api_key_encrypted)
        if api_key:
            status = probe_gemini_status(api_key)
        else:
            status = {
                **status,
                "status": "invalid",
                "model_status": "unavailable",
                "message": "Stored API key could not be decrypted.",
                "active_model": None,
                "available_models": [],
            }

    return {
        "byok_enabled": current_user.byok_enabled,
        "has_api_key": bool(current_user.gemini_api_key_encrypted),
        "user_id": current_user.id,
        "email": current_user.email,
        **status,
    }
