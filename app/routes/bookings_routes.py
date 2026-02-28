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
    
    assigned_drone_id = None
    eta_mins = None
    initial_status = "pending"

    # 🔥 EMERGENCY AUTO-DISPATCH LOGIC
    if booking.serviceType in EMERGENCY_SERVICES:
        # 1. Get all available drones with a location
        available_drones = list(db.drones.find({
            "status": "available", 
            "current_location": {"$ne": None}
        }))

        if available_drones:
            # 2. Math to find the nearest drone
            def get_distance(drone):
                d_lat = drone["current_location"]["lat"]
                d_lon = drone["current_location"]["lon"]
                # Basic Pythagorean theorem for quick distance estimation
                return math.sqrt((d_lat - booking.lat)**2 + (d_lon - booking.lon)**2)
            
            nearest_drone = min(available_drones, key=get_distance)
            assigned_drone_id = nearest_drone["drone_id"]
            
            # 3. Calculate ETA (Rough math: 0.01 deg is ~1.1km. Drone flies 1km/min)
            dist_deg = get_distance(nearest_drone)
            eta_mins = max(2, int(dist_deg * 100))
            initial_status = "in_progress" # Instant dispatch!

            # 4. Lock the drone so nobody else can book it
            db.drones.update_one(
                {"drone_id": assigned_drone_id}, 
                {"$set": {"status": "on_job"}}
            )

    # Save the booking
    booking_document = {
        "booking_id": new_booking_id,
        "customer_uid": user_uid,
        "pilot_uid": None,
        "drone_id": assigned_drone_id, # Will be filled if emergency!
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
        "message": "Emergency Drone Dispatched!" if assigned_drone_id else "Booking pending.",
        "drone_id": assigned_drone_id,
        "eta": eta_mins
    }