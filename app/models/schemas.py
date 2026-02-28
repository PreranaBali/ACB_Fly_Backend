from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, time

# --- DRONE MODEL ---
class Location(BaseModel):
    lat: float
    lon: float

class Drone(BaseModel):
    drone_id: str
    name: str
    capabilities: List[str] # e.g., ["Crop Spraying", "Seed Spreading"]
    battery_level: int = Field(..., ge=0, le=100)
    current_location: Optional[Location] = None
    status: str # "available", "in_flight", "maintenance"

# --- PILOT MODEL ---
class Pilot(BaseModel):
    pilot_id: str # This should map to their Firebase UID
    name: str
    phone: str
    assigned_drone_id: Optional[str] = None
    status: str # "available", "on_job", "off_duty"

# --- BOOKING MODELS ---
class BookingRequest(BaseModel):
    serviceType: str
    date: date
    time: time
    quantity: float = Field(..., gt=0)
    address: str
    paymentMethod: str
    totalPrice: float
    lat: float  # Added to help assign the closest pilot
    lon: float

# The full database document for a booking
class BookingDocument(BaseModel):
    booking_id: str
    customer_uid: str
    pilot_uid: Optional[str] = None   # Starts as None, assigned later
    drone_id: Optional[str] = None    # Starts as None, assigned later
    service_type: str
    date: str
    time: str
    quantity: float
    address: str
    location: Location
    payment_method: str
    total_price: float
    status: str # "pending", "assigned", "in_progress", "completed", "cancelled"

class BookingResponse(BaseModel):
    booking_id: str
    status: str
    message: str
    drone_id: Optional[str] = None
    eta: Optional[int] = None