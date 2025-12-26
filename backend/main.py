import os
import base64
import datetime
import json
import uuid
from typing import List, Optional, Any

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles 
from pydantic import BaseModel
from dotenv import load_dotenv

from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship

import analyze_and_summary as analyzer
import scheduler
import interview_manager as interviewer

load_dotenv()

# --- DATABASE SETUP ---
DATABASE_URL = os.environ.get("POSTGRES_DB_URL")

if not DATABASE_URL:
    print("Warning: POSTGRES_DB_URL not found. Using SQLite fallback.")
    DATABASE_URL = "sqlite:///./app.db"

connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- DATABASE MODELS ---

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(String, primary_key=True, index=True) # UUID
    title = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Cascade delete messages when session is deleted
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("chat_sessions.id"))
    role = Column(String)  
    type = Column(String)  
    content = Column(JSON) 
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    session = relationship("ChatSession", back_populates="messages")

# Create Tables
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI(title="SmartHire API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models ---
class ScheduleRequest(BaseModel):
    candidates: List[dict]
    start_time: Optional[str] = None

class ChatRequest(BaseModel):
    user_text: str
    session_id: Optional[str] = None
    job_desc: Optional[str] = ""
    resume_text: Optional[str] = ""

class RenameSessionRequest(BaseModel):
    new_title: str

# --- HELPER: Get or Create Session ---
def get_or_create_session(db: Session, session_id: str = None, title_hint: str = "New Chat"):
    if session_id:
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if session:
            return session
    
    new_id = str(uuid.uuid4())
    safe_title = (title_hint[:30] + '..') if len(title_hint) > 30 else title_hint
    session = ChatSession(id=new_id, title=safe_title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

# --- API Endpoints ---

@app.post("/api/reset")
async def reset_session(db: Session = Depends(get_db)):
    """Deletes ALL sessions."""
    try:
        db.query(ChatSession).delete()
        db.commit()
        return {"status": "reset", "message": "All history cleared"}
    except Exception as e:
        db.rollback()
        # Fallback
        db.query(ChatMessage).delete()
        db.query(ChatSession).delete()
        db.commit()
        return {"status": "reset", "message": "All history cleared (Fallback)"}

@app.get("/api/sessions")
async def get_sessions(db: Session = Depends(get_db)):
    """Get list of chat sessions."""
    sessions = db.query(ChatSession).order_by(ChatSession.created_at.desc()).all()
    return {"sessions": sessions}

@app.get("/api/history/{session_id}")
async def get_session_history(session_id: str, db: Session = Depends(get_db)):
    """Get messages for a specific session."""
    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.timestamp).all()
    return {"history": messages}

# --- NEW: Rename Session ---
@app.put("/api/sessions/{session_id}")
async def rename_session(session_id: str, request: RenameSessionRequest, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.title = request.new_title
    db.commit()
    return {"status": "success", "title": session.title}

# --- NEW: Delete Specific Session ---
@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    db.delete(session)
    db.commit()
    return {"status": "success", "message": "Session deleted"}


@app.post("/api/analyze")
async def analyze_resumes(
    job_description: str = Form(...),
    session_id: str = Form(None),
    resumes: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    try:
        session = get_or_create_session(db, session_id, title_hint=job_description)
        current_session_id = session.id

        if not resumes:
            raise HTTPException(status_code=400, detail="No resumes uploaded")
        
        user_msg = ChatMessage(session_id=current_session_id, role="user", type="text", content=job_description)
        db.add(user_msg)
        db.commit()

        file_objects = [file.file for file in resumes]
        for i, f_obj in enumerate(file_objects):
            if not hasattr(f_obj, 'name'):
                f_obj.name = resumes[i].filename

        results = analyzer.analyze_resumes(job_description, file_objects)

        bot_msg = ChatMessage(session_id=current_session_id, role="bot", type="table", content=results)
        db.add(bot_msg)
        db.commit()

        return {"results": results, "session_id": current_session_id}
    
    except Exception as e:
        print(f"Error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/schedule")
async def schedule_interviews(request: ScheduleRequest):
    try:
        if request.start_time:
            dt_str = request.start_time.replace('Z', '+00:00')
            start_datetime = datetime.datetime.fromisoformat(dt_str)
        else:
            start_datetime = datetime.datetime.now()

        logs = scheduler.batch_schedule_interviews(
            request.candidates, 
            start_datetime
        )
        return {"logs": logs}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/interview/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    try:
        audio_bytes = await audio.read()
        text = interviewer.transcribe_audio(audio_bytes)
        return {"text": text}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/interview/chat")
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        session_title = request.user_text if request.user_text else "Interview Session"
        session = get_or_create_session(db, request.session_id, title_hint=session_title)
        current_session_id = session.id

        recent_msgs = db.query(ChatMessage).filter(ChatMessage.session_id == current_session_id)\
                        .order_by(ChatMessage.timestamp.desc()).limit(10).all()
        
        conversation_history = []
        for msg in reversed(recent_msgs):
            if msg.type == 'text':
                role = "assistant" if msg.role == "bot" or msg.role == "assistant" else "user"
                conversation_history.append({"role": role, "content": str(msg.content)})

        conversation_history.append({"role": "user", "content": request.user_text})
        
        db.add(ChatMessage(session_id=current_session_id, role="user", type="text", content=request.user_text))
        db.commit()

        ai_response = interviewer.generate_interview_question(
            conversation_history, 
            request.resume_text, 
            request.job_desc
        )
        
        db.add(ChatMessage(session_id=current_session_id, role="assistant", type="text", content=ai_response))
        db.commit()
        
        audio_path = interviewer.text_to_speech(ai_response)
        
        if not audio_path:
             return JSONResponse(status_code=500, content={"error": "TTS failed"})

        with open(audio_path, "rb") as audio_f:
            audio_b64 = base64.b64encode(audio_f.read()).decode('utf-8')
        
        os.remove(audio_path)

        return {
            "ai_text": ai_response,
            "audio_base64": audio_b64,
            "session_id": current_session_id
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# SERVE FRONTEND
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
frontend_dir = os.path.join(root_dir, "frontend")

if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
else:
    print(f"Warning: Frontend directory not found at {frontend_dir}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)