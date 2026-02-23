from fastapi import APIRouter, Depends
from app.middleware.firebase_auth import verify_firebase_token
from app.services.user_service import get_or_create_user

router = APIRouter()

@router.post("/sync")
async def sync_user(decoded=Depends(verify_firebase_token)):
    user = get_or_create_user(decoded)
    return {"user": user}