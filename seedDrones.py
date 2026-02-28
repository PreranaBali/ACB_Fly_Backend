import os
import random
from pymongo import MongoClient

# Make sure this matches your exact MongoDB URI!
# E.g., MONGO_URI = "mongodb+srv://user:pass@cluster.mongodb.net/AircabDB"
# If you are using localhost, it is usually "mongodb://localhost:27017"

from app.database import db # Import your exact database connection

# Coordinates for major Indian cities
INDIAN_CITIES = [
    {"city": "Chennai", "lat": 13.0827, "lon": 80.2707},
    {"city": "Bangalore", "lat": 12.9716, "lon": 77.5946},
    {"city": "Mumbai", "lat": 19.0760, "lon": 72.8777},
    {"city": "Delhi", "lat": 28.7041, "lon": 77.1025}
]

def seed_database():
    print("🚁 Dropping old drone data to prevent conflicts...")
    db.drones.delete_many({}) # Clear the collection

    new_drones = []
    
    # Generate 3 drones per city
    for i, location in enumerate(INDIAN_CITIES):
        for j in range(3):
            # Add a tiny bit of random scatter so they don't stack on top of each other
            lat_scatter = location["lat"] + (random.uniform(-0.05, 0.05))
            lon_scatter = location["lon"] + (random.uniform(-0.05, 0.05))
            
            # Make the first drone available, the second busy, and third available
            status = "available" if j % 2 == 0 else "on_job"

            drone_doc = {
                "drone_id": f"AC-{location['city'][:3].upper()}-0{j+1}",
                "name": f"Aircab VTOL Mk {j+1}",
                "capabilities": ["Emergency Delivery", "Crop Spraying", "Field Mapping"],
                "battery_level": random.randint(45, 100),
                "current_location": {
                    "lat": float(lat_scatter),
                    "lon": float(lon_scatter)
                },
                "status": status
            }
            new_drones.append(drone_doc)

    print(f"🚁 Inserting {len(new_drones)} perfectly formatted Aircabs...")
    db.drones.insert_many(new_drones)
    print("✅ Database Seeded Successfully!")

if __name__ == "__main__":
    seed_database()