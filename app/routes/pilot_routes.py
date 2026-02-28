import uuid
import hashlib
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from app.database import db 

router = APIRouter(prefix="/api/pilots", tags=["Pilots & Drones"])

# ==========================================
# 1. SCHEMAS (Data Validation)
# ==========================================
class PilotRegister(BaseModel):
    username: str
    password: str
    name: str
    phone: str
    drone_model: str # e.g., "DJI Agras T20"

class PilotLogin(BaseModel):
    username: str
    password: str

class LocationUpdate(BaseModel):
    lat: float
    lon: float
    battery_level: int

# Simple password hashing function
def hash_password(password: str):
    return hashlib.sha256(password.encode()).hexdigest()

# ==========================================
# 2. AUTHENTICATION & REGISTRATION
# ==========================================
@router.post("/register")
def register_pilot(pilot: PilotRegister):
    """Registers a new Pilot+Drone combo."""
    if db.pilots.find_one({"username": pilot.username}):
        raise HTTPException(status_code=400, detail="Username already exists")
    
    pilot_id = f"PLT-{str(uuid.uuid4())[:8].upper()}"
    
    pilot_data = {
        "pilot_id": pilot_id,
        "username": pilot.username,
        "password": hash_password(pilot.password),
        "name": pilot.name,
        "phone": pilot.phone,
        "drone_model": pilot.drone_model,
        "status": "offline", # State Machine: offline -> available -> busy
        "current_location": None,
        "battery_level": 100,
        "current_job_id": None, # Tracks exactly what job they are on!
        "token": None # Will be generated on login
    }
    
    db.pilots.insert_one(pilot_data)
    return {"message": "Pilot registered successfully", "pilot_id": pilot_id}

@router.post("/login")
def login_pilot(creds: PilotLogin):
    """Logs the pilot in, makes them 'available', and returns a session token."""
    pilot = db.pilots.find_one({
        "username": creds.username, 
        "password": hash_password(creds.password)
    })
    
    if not pilot:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # Generate a simple session token
    session_token = str(uuid.uuid4())
    
    # Update token and set status to available so they can receive jobs!
    db.pilots.update_one(
        {"_id": pilot["_id"]}, 
        {"$set": {"token": session_token, "status": "available"}}
    )
    
    return {
        "message": "Login successful", 
        "token": session_token, 
        "pilot_id": pilot["pilot_id"],
        "name": pilot["name"]
    }

# --- Custom Dependency to verify the Pilot's Token ---
def get_current_pilot(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    token = authorization.split(" ")[1]
    pilot = db.pilots.find_one({"token": token})
    
    if not pilot:
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")
    return pilot

# ==========================================
# 3. LIVE TRACKING (The Uber Map Ping)
# ==========================================
@router.put("/telemetry")
def update_telemetry(telemetry: LocationUpdate, current_pilot: dict = Depends(get_current_pilot)):
    """The Pilot App pings this route every 5 seconds while open."""
    db.pilots.update_one(
        {"pilot_id": current_pilot["pilot_id"]},
        {"$set": {
            "current_location": {"lat": telemetry.lat, "lon": telemetry.lon},
            "battery_level": telemetry.battery_level
        }}
    )
    return {"status": "Location updated"}

# ==========================================
# 4. JOB MANAGEMENT (Accepting & Delivering)
# ==========================================
@router.get("/available-jobs")
def get_available_jobs(current_pilot: dict = Depends(get_current_pilot)):
    """Shows all pending jobs."""
    jobs = list(db.bookings.find({"status": "pending", "pilot_uid": None}, {"_id": 0}))
    return {"jobs": jobs}

@router.post("/jobs/{booking_id}/accept")
def accept_job(booking_id: str, current_pilot: dict = Depends(get_current_pilot)):
    """Pilot accepts a job. They become 'busy' and are linked to the job."""
    
    # 1. Check if the pilot is already on a job!
    if current_pilot["status"] == "busy" or current_pilot["current_job_id"]:
        raise HTTPException(status_code=400, detail="You are already on an active job!")

    booking = db.bookings.find_one({"booking_id": booking_id})
    if not booking or booking.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Job no longer available")

    # 2. Update Booking
    db.bookings.update_one(
        {"booking_id": booking_id},
        {"$set": {"status": "Accepted", "pilot_uid": current_pilot["pilot_id"]}}
    )

    # 3. Update Pilot to BUSY and assign the Job ID
    db.pilots.update_one(
        {"pilot_id": current_pilot["pilot_id"]},
        {"$set": {
            "status": "busy", 
            "current_job_id": booking_id
        }}
    )

    return {"message": "Job accepted!", "booking_id": booking_id}

@router.patch("/jobs/{booking_id}/status")
def update_job_status(booking_id: str, status: str, current_pilot: dict = Depends(get_current_pilot)):
    """Updates job status. If Delivered, Pilot becomes 'available' again."""
    valid_statuses = ["in_progress", "Delivered"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")

    # 1. Update Booking
    result = db.bookings.update_one(
        {"booking_id": booking_id, "pilot_uid": current_pilot["pilot_id"]},
        {"$set": {"status": status}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Job not found or unauthorized")

    # 2. If delivered, free up the pilot!
    if status == "Delivered":
        db.pilots.update_one(
            {"pilot_id": current_pilot["pilot_id"]},
            {"$set": {
                "status": "available", 
                "current_job_id": None # Clear the active job tracker
            }}
        )

    return {"message": f"Job marked as {status}"}

# Add these to pilot.py to support the Customer Map!
@router.get("/live")
def get_live_pilots():
    """Fetches all pilots with a known location to render on the customer map."""
    pilots = list(db.pilots.find(
        {"current_location": {"$ne": None}}, 
        {"_id": 0, "password": 0, "token": 0} # Keep passwords hidden!
    ))
    return {"pilots": pilots}

@router.get("/{pilot_id}/location")
def get_pilot_location(pilot_id: str):
    """Used for live-tracking a specifically dispatched pilot."""
    pilot = db.pilots.find_one({"pilot_id": pilot_id}, {"_id": 0, "current_location": 1})
    if not pilot:
        raise HTTPException(status_code=404, detail="Pilot not found")
    return {"pilot": pilot}

@router.get("/my-jobs")
def get_pilot_jobs(current_pilot: dict = Depends(get_current_pilot)):
    """Fetches all missions currently assigned to the logged-in pilot."""
    # Find all bookings where this pilot is the assigned drone/pilot
    jobs = list(db.bookings.find(
        {"pilot_uid": current_pilot["pilot_id"]}, 
        {"_id": 0}
    ))
    
    return {"jobs": jobs}