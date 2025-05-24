from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import traceback

from server.queries.insurances import get_insurance_details

import os

app = FastAPI()

# Enable CORS for frontend dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"],  # Use exact domain in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root route
@app.get("/")
def read_root():
    return {"message": "GoBidRV backend is running 🚐💨"}
    
    
### Insurance ###

# GET endpoint to fetch insurance acceptance by name
@app.get("/get_insurance_status")
async def get_insurance_status(name: str):
    try:
        print(f"Fetching insurance status for: {name}")
        accepted = await get_insurance_details(name)
        if accepted is None:
            raise HTTPException(status_code=404, detail="Insurance provider not found")
        return {"name": name, "accepted": accepted}
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))