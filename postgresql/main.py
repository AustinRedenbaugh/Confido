from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import traceback

from server.queries.users import create_user, get_user_by_firebase_uid, get_user_by_email, get_all_users
from server.queries.rvs import get_images_by_rv, get_all_rvs, create_rv
from server.queries.listings import get_all_listings, create_listing
from server.queries.auctions import get_all_auctions

from server.types.User import User
from server.types.Rv import Rv
from server.types.Listing import Listing

import os

app = FastAPI()

# Initialize S3 client using env vars (or your IAM role if running on AWS infra)
s3 = boto3.client(
    "s3",
    region_name=os.getenv("AWS_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    config=botocore.client.Config(signature_version="s3v4")
)

BUCKET_NAME = "gobidrv-b1"

# Enable CORS for frontend dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Use exact domain in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request model for creating a user
class UserRequest(BaseModel):
    email: str
    firebase_uid: str

# Request model for all things rvs
class RvRequest(BaseModel):
    id: str

# Define the request model for adding an RV
class RvPostRequest(BaseModel):
    owner_id: int = Field(..., description="The ID of the user who owns the RV")
    make: str = Field(..., description="The make of the RV")
    model: str = Field(..., description="The model of the RV")
    trim: str = Field(..., description="The trim level of the RV")
    year: int = Field(..., ge=1904, description="The manufacturing year of the RV")
    mileage: int = Field(..., ge=0, description="The mileage of the RV")
    condition: str = Field(..., description="The condition of the RV (e.g., New or Used)")
    reserve: float = Field(..., ge=0.0, description="The reserve price for the auction")
    description: str = Field(..., description="A detailed description of the RV")
    photos: List[str] = Field(default_factory=list, description="List of photo filenames")

# ➕ Define the Listing data model
class ListingRequest(BaseModel):
    rv_id: int
    start_time: datetime
    end_time: datetime
    starting_bid: float
    reserve: float
    min_increment: Optional[float] = 100.00

class PresignRequest(BaseModel):
    filename: str
    content_type: str  # like "image/jpeg" or "image/png"

# Root route
@app.get("/")
def read_root():
    return {"message": "GoBidRV backend is running 🚐💨"}
    
    
### Users ###

# POST endpoint to add a user
@app.post("/add_user")
async def add_user(req: UserRequest):
    try:
        print(f"Creating user with email: {req.email}")
        user = await create_user(
            firebase_uid=req.firebase_uid,
            email=req.email
        )
        return user
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# GET endpoint to fetch all users
@app.get("/get_users")
async def get_users():
    try:
        print("Fetching all users...")
        users = await get_all_users()
        return users
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# GET endpoint to get the user by Firebase UID
@app.post("/login")
async def login(req: UserRequest):
    try:
        print(f"Requesting user with email: {req.email}")
        user = await get_user_by_firebase_uid(
            firebase_uid=req.firebase_uid
        )
        return user
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
# GET endpoint to get the user by email
@app.post("/get_user")
async def get_user(req: UserRequest):
    try:
        print(f"Requesting user with email: {req.email}")
        user = await get_user_by_email(
            email=req.email
        )
        return user
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    


### RVs ###

# GET endpoint to get all rvs
@app.get("/get_rvs")
async def get_rvs():
    try:
        rvs = await get_all_rvs()
        return rvs
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# POST endpoint to add an RV
@app.post("/add_rv")
async def add_rv(request: Request):
    try:
        data = await request.json()
        print("🧾 Raw incoming JSON data:")
        print(data)

        # Manually convert to Pydantic model to test validation
        validated = RvPostRequest(**data)
        print("✅ Validated data:")
        print(validated)

        result = await create_rv(**validated.dict())
        return result

    except Exception as e:
        print("❌ Exception while adding RV:")
        print(e)
        raise HTTPException(status_code=500, detail=str(e))



### Listings ###

# GET endpoint to get the listings
@app.get("/get_listings")
async def get_listings():
    try:
        listings = await get_all_listings()
        return listings
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ➕ Create a new listing endpoint
@app.post("/create_listing")
async def create_listing_endpoint(listing: ListingRequest):
    try:
        # Call the helper function to insert the listing into the database
        new_listing = await create_listing(
            rv_id=listing.rv_id,
            start_time=listing.start_time,
            end_time=listing.end_time,
            starting_bid=listing.starting_bid,
            reserve=listing.reserve,
            min_increment=listing.min_increment
        )
        if new_listing:
            return {"status": "success", "listing": new_listing}
        else: 
            raise HTTPException(status_code=500, detail="Failed to create listing")
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error during listing creation: {error_trace}")

        raise HTTPException(status_code=500, detail=str(e))


### Auctions ###

# GET endpoint to get the joined auctions and RVs
@app.get("/get_auctions")
async def get_auctions():
    try:
        auctions = await get_all_auctions()
        return auctions
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))



### Images ###

@app.post("/generate-presigned-url")
def generate_presigned_url(req: PresignRequest):
    try:
        key = f"uploads/{req.filename}"

        url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": BUCKET_NAME,
                "Key": key,
                "ContentType": req.content_type,
            },
            ExpiresIn=3600  # 1 hour
        )

        return {"url": url, "key": key}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))