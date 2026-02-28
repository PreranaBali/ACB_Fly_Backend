import uuid
import math
from fastapi import APIRouter, Depends, HTTPException, status
from app.middleware.firebase_auth import verify_firebase_token
from app.database import db 
from app.models.schemas import BookingRequest, BookingResponse

router = APIRouter(prefix="/api/bookings", tags=["Bookings"])

# 💰 Official Rate Chart (Backend Source of Truth)
PRICE_CHART = {
    "Crop Spraying": {"rate": 600, "unit": "Acres"},
    "Crop Monitoring": {"rate": 400, "unit": "Acres"},
    "Field Mapping": {"rate": 800, "unit": "Acres"},
    "Seed Spreading": {"rate": 500, "unit": "Acres"},
    "Emergency Delivery": {"rate": 300, "unit": "KM"},
    "Medicine Transport": {"rate": 200, "unit": "KM"},
    "Disaster Relief Drop": {"rate": 400, "unit": "KM"},
    "Wedding Shoot": {"rate": 4000, "unit": "Hours"},
    "Property Shoot": {"rate": 3000, "unit": "Hours"}
}

EMERGENCY_SERVICES = ["Emergency Delivery", "Medicine Transport", "Disaster Relief Drop"]

@router.post("", status_code=status.HTTP_201_CREATED)
def create_booking(booking: BookingRequest, decoded_token: dict = Depends(verify_firebase_token)):
    user_uid = decoded_token.get("uid")
    if not user_uid:
        raise HTTPException(status_code=401, detail="Invalid token")

    rate = PRICE_CHART[booking.serviceType]["rate"]
    calculated_price = rate * booking.quantity

    new_booking_id = f"DRONE-{str(uuid.uuid4())[:8].upper()}"
    
    assigned_pilot_id = None
    eta_mins = None
    initial_status = "pending"

    # 🔥 EMERGENCY AUTO-DISPATCH LOGIC
    if booking.serviceType in EMERGENCY_SERVICES:
        # 1. Get all available pilots with a known location
        available_pilots = list(db.pilots.find({
            "status": "available", 
            "current_location": {"$ne": None}
        }))

        if available_pilots:
            def get_distance(pilot):
                p_lat = pilot["current_location"]["lat"]
                p_lon = pilot["current_location"]["lon"]
                return math.sqrt((p_lat - booking.lat)**2 + (p_lon - booking.lon)**2)
            
            nearest_pilot = min(available_pilots, key=get_distance)
            assigned_pilot_id = nearest_pilot["pilot_id"]
            
            dist_deg = get_distance(nearest_pilot)
            eta_mins = max(2, int(dist_deg * 100))
            
            # 🔥 FIX 1: Set to 'Accepted' so it goes straight to 'My Missions'
            initial_status = "Accepted" 

            # Lock the pilot so nobody else can book them
            db.pilots.update_one(
                {"pilot_id": assigned_pilot_id}, 
                {"$set": {
                    "status": "busy",
                    "current_job_id": new_booking_id
                }}
            )

    # Save the booking
    booking_document = {
        "booking_id": new_booking_id,
        "customer_uid": user_uid,
        # 🔥 FIX 2: Ensure pilot_uid is populated instantly for emergencies!
        "pilot_uid": assigned_pilot_id, 
        "drone_id": assigned_pilot_id, # Keeping this just in case other parts of your app use it
        "service_type": booking.serviceType,
        "date": str(booking.date), 
        "time": str(booking.time),
        "quantity": booking.quantity,
        "address": booking.address,
        "location": {"lat": booking.lat, "lon": booking.lon},
        "payment_method": booking.paymentMethod,
        "total_price": calculated_price,
        "status": initial_status 
    }
    
    db.bookings.insert_one(booking_document)

    return {
        "booking_id": new_booking_id,
        "status": initial_status,
        "message": "Emergency Drone Dispatched!" if assigned_pilot_id else "Booking pending.",
        "pilot_uid": assigned_pilot_id,
        "eta": eta_mins
    }

@router.get("/my-bookings")
def get_user_bookings(decoded_token: dict = Depends(verify_firebase_token)):
    """Allows a user to see their bookings and the assigned pilot details."""
    user_uid = decoded_token.get("uid")
    
    # Fetch user's bookings
    bookings = list(db.bookings.find({"customer_uid": user_uid}, {"_id": 0}))

    # Attach pilot details if a pilot has accepted the job
    for booking in bookings:
        if booking.get("pilot_uid"):
            # Fetch pilot details from the users collection (assuming pilots are also in users_collection)
            pilot = db.users_collection.find_one(
                {"firebaseUid": booking["pilot_uid"]}, 
                {"_id": 0, "name": 1, "phone": 1, "photoURL": 1} # Only grab safe fields!
            )
            booking["pilot_details"] = pilot
        else:
            booking["pilot_details"] = None

    return {"bookings": bookings}