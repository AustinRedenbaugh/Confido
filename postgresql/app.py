from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import traceback

from server.queries.insurances import get_insurance_details
from server.queries.appointments import get_available_time_slots

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

app.mount("/static", StaticFiles(directory="static"), name="static")
    
    
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
    

### Appointments ###

# GET endpoint to fetch available appointment slots between start and end times
@app.get("/check_appt_slots")
async def check_appt_slots(
    start_time: datetime = Query(..., description="Start of the time window (ISO 8601 format)"),
    end_time: datetime = Query(..., description="End of the time window (ISO 8601 format)")
):
    try:
        print(f"Checking available slots from {start_time} to {end_time}")
        slots = await get_available_time_slots(start_time, end_time)
        return {"slots": slots}
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
