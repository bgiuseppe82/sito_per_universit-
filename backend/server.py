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
    """Process audio data using Gemini 2.0 Flash for transcription and summarization"""
    try:
        # For demo purposes, we'll simulate audio processing
        # In a real implementation, you'd first convert audio to text using Whisper
        # Then send the text to Gemini for summarization
        
        # Initialize Claude Sonnet 4 chat
        chat = LlmChat(
            api_key=os.environ.get('ANTHROPIC_API_KEY', 'demo-key'),
            session_id=f"audio-processing-{recording_id}",
            system_message="You are an AI assistant that helps students by transcribing and summarizing their lesson recordings."
        ).with_model("anthropic", "claude-sonnet-4-20250514")
        
        # Simulate transcription (in real app, use Whisper API first)
        if processing_type == "full":
            prompt = """This is a simulated transcription request. Please provide a sample transcription of a typical university lecture. Make it educational and realistic, about 200-300 words covering a topic like physics, mathematics, or computer science."""
            
            user_message = UserMessage(text=prompt)
            transcript = await chat.send_message(user_message)
            
            # Update recording with transcript
            await db.recordings.update_one(
                {"id": recording_id},
                {"$set": {"transcript": transcript, "status": "completed"}}
            )
            
        elif processing_type == "summary":
            prompt = """This is a simulated summarization request. Please provide a concise summary of a typical university lecture in bullet points. Make it educational and realistic, covering key concepts, main points, and conclusions."""
            
            user_message = UserMessage(text=prompt)
            summary = await chat.send_message(user_message)
            
            # Update recording with summary
            await db.recordings.update_one(
                {"id": recording_id},
                {"$set": {"summary": summary, "status": "completed"}}
            )
            
        elif processing_type == "chapters":
            prompt = """This is a simulated chapter detection request. Please provide a structured breakdown of a typical university lecture with chapters/sections like: Introduction, Key Concepts, Examples, and Conclusion. Format it as a clear outline."""
            
            user_message = UserMessage(text=prompt)
            chapters = await chat.send_message(user_message)
            
            # Update recording with structured content
            await db.recordings.update_one(
                {"id": recording_id},
                {"$set": {"summary": f"**Chapter Breakdown:**\n{chapters}", "status": "completed"}}
            )
            
    except Exception as e:
        logging.error(f"Error processing audio: {str(e)}")
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