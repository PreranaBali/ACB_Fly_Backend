from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.database import db 

router = APIRouter(prefix="/api/drones", tags=["Drones"])

class LocationUpdate(BaseModel):
    lat: float
    lon: float
    battery_level: int

@router.put("/{drone_id}/telemetry")
def update_drone_telemetry(drone_id: str, telemetry: LocationUpdate):
    """
    The drone hardware or pilot app pings this route every few seconds 
    to update its live location on the map.
    """
    result = db.drones.update_one(
        {"drone_id": drone_id},
        {"$set": {
            "current_location": {"lat": telemetry.lat, "lon": telemetry.lon},
            "battery_level": telemetry.battery_level
        }}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Drone not found")

    return {"status": "Telemetry updated"}

# 🔥 MOVED THIS UP! Static routes must go BEFORE dynamic {drone_id} routes
@router.get("/live")
def get_live_fleet():
    """
    Fetches ALL drones that have a known location, 
    so the frontend can show both available and busy fleet members.
    """
    try:
        fleet = list(db.drones.find(
            {"current_location": {"$ne": None}}, 
            {"_id": 0} 
        ))
        
        return {"drones": fleet}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch fleet data")
    
# 👇 Dynamic routes go at the bottom
@router.get("/{drone_id}")
def get_drone_location(drone_id: str):
    """Used for live-tracking a specific dispatched drone."""
    drone = db.drones.find_one({"drone_id": drone_id}, {"_id": 0})
    if not drone:
        raise HTTPException(status_code=404, detail="Drone not found")
    return {"drone": drone}