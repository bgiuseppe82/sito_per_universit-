from fastapi import FastAPI, APIRouter, HTTPException, File, UploadFile, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timedelta
import base64
import asyncio
import json
from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    picture: Optional[str] = None
    subscription_status: str = "trial"
    referral_code: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    discount_amount: float = 0.0
    preferred_language: str = "en"  # Default to English
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Recording(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: str
    audio_data: str  # Base64 encoded audio
    transcript: Optional[str] = None
    summary: Optional[str] = None
    tags: List[str] = []
    notes: str = ""
    duration: Optional[float] = None
    status: str = "uploaded"  # uploaded, processing, completed, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Session(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    session_token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)

class RecordingCreate(BaseModel):
    title: str
    audio_data: str
    tags: List[str] = []
    notes: str = ""
    duration: Optional[float] = None

class TranscriptionRequest(BaseModel):
    recording_id: str
    type: str = "full"  # full, summary, chapters
    language: str = "en"  # User's preferred language

class ProcessingResponse(BaseModel):
    message: str
    recording_id: str
    status: str

# Helper functions
async def get_current_user(authorization: HTTPAuthorizationCredentials = Depends(security)):
    token = authorization.credentials
    session = await db.sessions.find_one({"session_token": token})
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session token")
    
    session_obj = Session(**session)
    if session_obj.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Session expired")
    
    user = await db.users.find_one({"id": session_obj.user_id})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return User(**user)

async def process_audio_with_ai(recording_id: str, audio_data: str, processing_type: str = "full"):
    """Process audio data with mock AI responses that simulate Claude Sonnet 4"""
    try:
        # Mock realistic AI responses for different processing types
        if processing_type == "full":
            # Mock full transcription
            transcript = """Welcome to today's Physics lecture on Newton's Laws of Motion. 

Today we're going to explore the fundamental principles that govern how objects move and interact with forces. Let's start with Newton's First Law, also known as the Law of Inertia.

Newton's First Law states that an object at rest stays at rest, and an object in motion stays in motion at constant velocity, unless acted upon by an external force. This might seem obvious, but it's actually quite profound when you think about it.

For example, if you're sitting in a car and the car suddenly stops, your body continues moving forward. This is because your body wants to maintain its state of motion - that's inertia in action.

Now, let's move on to Newton's Second Law, which is probably the most famous: F equals ma. Force equals mass times acceleration. This law tells us that the force applied to an object is directly proportional to the mass of the object and its acceleration.

A practical example: if you push a shopping cart with the same force, an empty cart will accelerate much faster than a full cart. Same force, different mass, different acceleration.

Finally, Newton's Third Law states that for every action, there is an equal and opposite reaction. When you walk, you push backward on the ground, and the ground pushes forward on you.

These three laws form the foundation of classical mechanics and help us understand motion in our everyday world. Next class, we'll explore how these laws apply to circular motion and gravity."""
            
            # Update recording with transcript
            await db.recordings.update_one(
                {"id": recording_id},
                {"$set": {"transcript": transcript, "status": "completed"}}
            )
            
        elif processing_type == "summary":
            # Mock smart summary
            summary = """📚 **Physics Lecture Summary: Newton's Laws of Motion**

**🎯 Key Concepts:**
• **Newton's First Law (Law of Inertia)**: Objects maintain their state of motion unless acted upon by external forces
• **Newton's Second Law**: F = ma (Force = mass × acceleration)  
• **Newton's Third Law**: Every action has an equal and opposite reaction

**💡 Main Points:**
1. **Inertia explained**: Objects resist changes in motion - demonstrated by car stopping example
2. **Force-mass relationship**: Same force on different masses produces different accelerations (shopping cart example)
3. **Action-reaction pairs**: Walking involves pushing ground backward, ground pushes you forward

**🔍 Practical Examples:**
- Car stopping → body continues moving forward (inertia)
- Empty vs full shopping cart → different accelerations with same force
- Walking → action-reaction force pairs

**📖 Next Session Preview:**
Application of these laws to circular motion and gravitational forces

**⭐ Study Focus:**
Understand how these three fundamental laws explain everyday motion phenomena"""
            
            # Update recording with summary
            await db.recordings.update_one(
                {"id": recording_id},
                {"$set": {"summary": summary, "status": "completed"}}
            )
            
        elif processing_type == "chapters":
            # Mock chapter detection
            chapters = """📖 **Lecture Structure: Newton's Laws of Motion**

**🎬 Introduction (0:00-2:30)**
- Course overview and today's topic
- Importance of Newton's Laws in physics

**📚 Chapter 1: Newton's First Law - Law of Inertia (2:30-8:45)**
- Definition and explanation
- Real-world examples (car stopping scenario)
- Understanding inertia in daily life

**⚖️ Chapter 2: Newton's Second Law - F=ma (8:45-15:20)**
- Mathematical relationship between force, mass, and acceleration
- Practical demonstration: shopping cart example
- Problem-solving applications

**🔄 Chapter 3: Newton's Third Law - Action-Reaction (15:20-22:10)**
- Equal and opposite reactions principle
- Walking as an example of action-reaction pairs
- Common misconceptions addressed

**🎯 Conclusion & Next Steps (22:10-25:00)**
- Summary of three laws
- Preview of next lecture: circular motion and gravity
- Study recommendations

**💡 Key Takeaways:**
Each law builds upon the previous one to create a complete understanding of motion dynamics"""
            
            # Update recording with structured content
            await db.recordings.update_one(
                {"id": recording_id},
                {"$set": {"summary": chapters, "status": "completed"}}
            )
            
    except Exception as e:
        logging.error(f"Error in mock AI processing: {str(e)}")
        await db.recordings.update_one(
            {"id": recording_id},
            {"$set": {"status": "failed"}}
        )

# Auth Routes
@api_router.get("/auth/profile")
async def get_profile(x_session_id: str = Header(None)):
    """Get user profile from session ID"""
    if not x_session_id:
        raise HTTPException(status_code=401, detail="Session ID required")
    
    # For demo, create a mock user
    user_data = {
        "id": str(uuid.uuid4()),
        "email": "demo@smartnotes.com",
        "name": "Demo User",
        "picture": "https://via.placeholder.com/150",
        "session_token": x_session_id
    }
    
    # Create or update user
    existing_user = await db.users.find_one({"email": user_data["email"]})
    if not existing_user:
        user = User(**user_data)
        await db.users.insert_one(user.dict())
    else:
        user = User(**existing_user)
    
    # Create session
    session = Session(
        user_id=user.id,
        session_token=x_session_id,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    await db.sessions.insert_one(session.dict())
    
    return user_data

# Recording Routes
@api_router.post("/recordings", response_model=Recording)
async def create_recording(recording_data: RecordingCreate, current_user: User = Depends(get_current_user)):
    """Create a new recording"""
    recording = Recording(
        user_id=current_user.id,
        title=recording_data.title,
        audio_data=recording_data.audio_data,
        tags=recording_data.tags,
        notes=recording_data.notes,
        duration=recording_data.duration,
        status="uploaded"
    )
    
    await db.recordings.insert_one(recording.dict())
    return recording

@api_router.get("/recordings", response_model=List[Recording])
async def get_recordings(current_user: User = Depends(get_current_user)):
    """Get all recordings for the current user"""
    recordings = await db.recordings.find({"user_id": current_user.id}).sort("created_at", -1).to_list(100)
    return [Recording(**recording) for recording in recordings]

@api_router.get("/recordings/{recording_id}", response_model=Recording)
async def get_recording(recording_id: str, current_user: User = Depends(get_current_user)):
    """Get a specific recording"""
    recording = await db.recordings.find_one({"id": recording_id, "user_id": current_user.id})
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    return Recording(**recording)

@api_router.post("/recordings/{recording_id}/process", response_model=ProcessingResponse)
async def process_recording(recording_id: str, request: TranscriptionRequest, current_user: User = Depends(get_current_user)):
    """Process recording for transcription/summarization"""
    recording = await db.recordings.find_one({"id": recording_id, "user_id": current_user.id})
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    # Update status to processing
    await db.recordings.update_one(
        {"id": recording_id},
        {"$set": {"status": "processing"}}
    )
    
    # Process in background
    asyncio.create_task(process_audio_with_ai(recording_id, recording["audio_data"], request.type))
    
    return ProcessingResponse(
        message=f"Processing started for {request.type} transcription",
        recording_id=recording_id,
        status="processing"
    )

@api_router.delete("/recordings/{recording_id}")
async def delete_recording(recording_id: str, current_user: User = Depends(get_current_user)):
    """Delete a recording"""
    result = await db.recordings.delete_one({"id": recording_id, "user_id": current_user.id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Recording not found")
    return {"message": "Recording deleted successfully"}

@api_router.put("/recordings/{recording_id}")
async def update_recording(recording_id: str, update_data: dict, current_user: User = Depends(get_current_user)):
    """Update recording metadata"""
    recording = await db.recordings.find_one({"id": recording_id, "user_id": current_user.id})
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    
    # Only allow updating specific fields
    allowed_fields = {"title", "tags", "notes"}
    update_fields = {k: v for k, v in update_data.items() if k in allowed_fields}
    
    if update_fields:
        await db.recordings.update_one(
            {"id": recording_id},
            {"$set": update_fields}
        )
    
    return {"message": "Recording updated successfully"}

# User Routes
@api_router.get("/user/profile", response_model=User)
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return current_user

@api_router.get("/user/referral")
async def get_referral_info(current_user: User = Depends(get_current_user)):
    """Get referral code and discount info"""
    return {
        "referral_code": current_user.referral_code,
        "discount_amount": current_user.discount_amount,
        "monthly_cost": max(2.0 - current_user.discount_amount, 1.0)  # Minimum €1.00
    }

# Health check
@api_router.get("/")
async def root():
    return {"message": "SmartNotes API is running"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()