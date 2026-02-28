from fastapi import APIRouter, Depends, HTTPException
from app.middleware.firebase_auth import verify_firebase_token
from app.database import db 

router = APIRouter(prefix="/api/pilots", tags=["Pilots"])

@router.get("/my-jobs")
def get_pilot_jobs(decoded_token: dict = Depends(verify_firebase_token)):
    """Allows a pilot to fetch all bookings assigned to them."""
    pilot_uid = decoded_token.get("uid")
    
    # Find all bookings where this pilot is assigned
    # Exclude MongoDB's internal _id from the response
    jobs = list(db.bookings.find({"pilot_uid": pilot_uid}, {"_id": 0}))
    
    return {"jobs": jobs}

@router.patch("/jobs/{booking_id}/status")
def update_job_status(booking_id: str, status: str, decoded_token: dict = Depends(verify_firebase_token)):
    """Pilot clicks 'Start Job' or 'Complete Job' on their app."""
    pilot_uid = decoded_token.get("uid")
    
    valid_statuses = ["in_progress", "completed"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status update")

    # Update the booking ONLY if it belongs to this pilot
    result = db.bookings.update_one(
        {"booking_id": booking_id, "pilot_uid": pilot_uid},
        {"$set": {"status": status}}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Job not found or unauthorized")

    return {"message": f"Job marked as {status}"}