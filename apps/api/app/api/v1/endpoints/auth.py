from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict, Any

from app.core.security import get_current_user

router = APIRouter()

class UserResponse(BaseModel):
    id: str
    message: str

@router.get("/me", response_model=UserResponse)
def get_me(user_id: str = Depends(get_current_user)) -> Any:
    """
    Returns the authenticated user's ID.
    In a full implementation, this might fetch the profile from the database.
    """
    return {"id": user_id, "message": "Authenticated successfully"}
