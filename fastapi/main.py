import os
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import List
from datetime import datetime
import jwt
from sqlalchemy.orm import Session
from sqlalchemy import select
from database import get_db
from models import Capsule, User
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.environ.get('SECRET_KEY')
print(SECRET_KEY)
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

app = FastAPI()

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        username: str = payload.get("username")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return username
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

@app.post("/capsules", response_model=CapsuleResponse)
async def create_capsule(capsule: CapsuleCreate, username: str = Depends(get_current_user), db: Session = Depends(get_db)):
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
    return CapsuleResponse(
        id=db_capsule.id,
        text=db_capsule.text,
        date_open=db_capsule.date_open,
        author=username
    )

@app.get("/capsules", response_model=List[CapsuleResponse])
async def list_capsules(username: str = Depends(get_current_user), db: Session = Depends(get_db)):
    user_query = select(User).where(User.username == username)
    user = db.execute(user_query).scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    capsules = db.query(Capsule).filter(Capsule.author_id == user.id).all()
    return [CapsuleResponse(id=c.id, text=c.text, date_open=c.date_open, author=username) for c in capsules]

@app.get("/capsules/{id}", response_model=CapsuleResponse)
async def get_capsule(id: int, username: str = Depends(get_current_user), db: Session = Depends(get_db)):
    user_query = select(User).where(User.username == username)
    user = db.execute(user_query).scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    capsule = db.query(Capsule).filter(Capsule.id == id, Capsule.author_id == user.id).first()
    if not capsule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capsule not found")
    if capsule.date_open.timestamp() > datetime.now().timestamp():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Capsule not yet available")
    return CapsuleResponse(id=capsule.id, text=capsule.text, date_open=capsule.date_open, author=username)

@app.put("/capsules/{id}", response_model=CapsuleResponse)
async def update_capsule(id: int, capsule: CapsuleCreate, username: str = Depends(get_current_user), db: Session = Depends(get_db)):
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