from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth_routes, user_routes

app = FastAPI()

# 🔥 Add this
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # your React URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router, prefix="/api/auth")
app.include_router(user_routes.router, prefix="/api")