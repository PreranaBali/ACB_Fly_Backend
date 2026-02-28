from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 🔥 Import all your routes
from app.routes import auth_routes, user_routes, bookings_routes, pilot_routes

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Existing routes
app.include_router(auth_routes.router, prefix="/api/auth")
app.include_router(user_routes.router, prefix="/api")
app.include_router(bookings_routes.router)

app.include_router(pilot_routes.router)