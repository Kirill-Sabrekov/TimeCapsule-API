import os
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import List
from datetime import datetime, timezone
import jwt
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from database import get_db
from models import Capsule, User
from tasks import send_open_notification
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.environ.get('SECRET_KEY')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="http://localhost:8000/login")

class CapsuleCreate(BaseModel):
    text: str
    date_open: datetime

class CapsuleResponse(BaseModel):
    id: int
    text: str
    date_open: datetime
    author: str

    class Config:
        orm_mode = True

class AnalyticsResponse(BaseModel):
    total_capsules: int
    pending_capsules: int
    opened_capsules: int

app = FastAPI(
    title="TimeCapsule API",
    description="API for creating and managing time capsules",
    version="1.0.0"
)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        if isinstance(token, bytes):
            token = token.decode("utf-8")
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        username: str = payload.get("username")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return username
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {str(e)}")

@app.get("/capsules/analytics", response_model=AnalyticsResponse)
async def get_analytics(username: str = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get analytics for user's capsules.
    - **total_capsules**: Total number of capsules.
    - **pending_capsules**: Capsules not yet open.
    - **opened_capsules**: Capsules already open.
    """
    user_query = select(User).where(User.username == username)
    user = db.execute(user_query).scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    result = db.query(
        func.count(Capsule.id).label("total"),
        func.count(Capsule.id).filter(Capsule.date_open > datetime.utcnow()).label("pending"),
        func.count(Capsule.id).filter(Capsule.date_open <= datetime.utcnow()).label("opened")
    ).filter(Capsule.author_id == user.id).first()
    return AnalyticsResponse(
        total_capsules=result.total,
        pending_capsules=result.pending,
        opened_capsules=result.opened
    )

@app.post("/capsules", response_model=CapsuleResponse)
async def create_capsule(capsule: CapsuleCreate, username: str = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Create a new time capsule.
    - **text**: Content of the capsule.
    - **date_open**: Date when the capsule can be opened.
    Returns the created capsule with ID and author.
    """
    try:
        user_query = select(User).where(User.username == username)
        user = db.execute(user_query).scalars().first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        db_capsule = Capsule(
            text=capsule.text,
            date_open=capsule.date_open,
            author_id=user.id,
            created_at=datetime.now()
        )
        db.add(db_capsule)
        db.commit()
        db.refresh(db_capsule)
        delay = (db_capsule.date_open - datetime.now(timezone.utc)).total_seconds()
        if delay > 0:
            send_open_notification.apply_async((db_capsule.id, username), countdown=delay)
        return CapsuleResponse(
            id=db_capsule.id,
            text=db_capsule.text,
            date_open=db_capsule.date_open,
            author=username
        )
    except Exception as e:
        print(f"Error creating capsule: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error: {str(e)}")

@app.get("/capsules", response_model=List[CapsuleResponse])
async def list_capsules(username: str = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    List all capsules for the authenticated user.
    """
    user_query = select(User).where(User.username == username)
    user = db.execute(user_query).scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    capsules_query = select(Capsule).where(Capsule.author_id == user.id)
    capsules = db.execute(capsules_query).scalars().all()
    return [CapsuleResponse(id=c.id, text=c.text, date_open=c.date_open, author=username) for c in capsules]

@app.get("/capsules/{id}", response_model=CapsuleResponse)
async def get_capsule(id: int, username: str = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get a specific capsule by ID.
    Returns 403 if the capsule is not yet open.
    """
    user_query = select(User).where(User.username == username)
    user = db.execute(user_query).scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    capsule = db.query(Capsule).filter(Capsule.id == id, Capsule.author_id == user.id).first()
    if not capsule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capsule not found")
    if capsule.date_open > datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Capsule not yet available")
    return CapsuleResponse(id=capsule.id, text=capsule.text, date_open=capsule.date_open, author=username)

@app.put("/capsules/{id}", response_model=CapsuleResponse)
async def update_capsule(id: int, capsule: CapsuleCreate, username: str = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Update a capsule by ID.
    """
    user_query = select(User).where(User.username == username)
    user = db.execute(user_query).scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    db_capsule = db.query(Capsule).filter(Capsule.id == id, Capsule.author_id == user.id).first()
    if not db_capsule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capsule not found")
    db_capsule.text = capsule.text
    db_capsule.date_open = capsule.date_open
    db.commit()
    db.refresh(db_capsule)
    return CapsuleResponse(id=db_capsule.id, text=db_capsule.text, date_open=db_capsule.date_open, author=username)

@app.delete("/capsules/{id}")
async def delete_capsule(id: int, username: str = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Delete a capsule by ID.
    """
    user_query = select(User).where(User.username == username)
    user = db.execute(user_query).scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    db_capsule = db.query(Capsule).filter(Capsule.id == id, Capsule.author_id == user.id).first()
    if not db_capsule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capsule not found")
    db.delete(db_capsule)
    db.commit()
    return {"message": "Capsule deleted"}