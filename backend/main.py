# backend/main.py
from fastapi import FastAPI, Depends
from .database import engine, Base
from .auth import routes as auth_routes
from . import models
from fastapi.middleware.cors import CORSMiddleware

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Adaptive Learning Auth")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
