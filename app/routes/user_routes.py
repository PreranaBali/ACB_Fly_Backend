from fastapi import APIRouter, Depends, HTTPException
from app.middleware.firebase_auth import verify_firebase_token
from app.models.user_model import users_collection

router = APIRouter()


# 🔹 GET PROFILE (auto create if first login)
@router.get("/profile")
async def get_profile(decoded=Depends(verify_firebase_token)):
    uid = decoded["uid"]

    user = users_collection.find_one({"firebaseUid": uid}, {"_id": 0})

    if not user:
        user = {
            "firebaseUid": uid,
            "name": decoded.get("name"),
            "email": decoded.get("email"),
            "photoURL": decoded.get("picture"),
            "phone": None,
            "location": None,
            "paymentMethods": []
        }

        users_collection.insert_one(user)
        user.pop("_id", None)

    return user


# 🔹 UPDATE PROFILE (single route for everything)
@router.put("/profile")
async def update_profile(data: dict, decoded=Depends(verify_firebase_token)):
    uid = decoded["uid"]

    # Only allow specific fields to be updated
    allowed_fields = ["name", "phone", "location", "paymentMethods"]

    update_data = {k: v for k, v in data.items() if k in allowed_fields}

    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields provided")

    users_collection.update_one(
        {"firebaseUid": uid},
        {"$set": update_data}
    )

    return {"message": "Profile updated successfully"}