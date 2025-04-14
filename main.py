import os
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import jwt

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

app = FastAPI()
capsules = []
current_id = 0

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        username: str = payload.get("username")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return username
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

@app.get("/status")
async def status():
    return {"status": "running"}

@app.post("/capsules", response_model=CapsuleResponse)
async def create_capsule(capsule: CapsuleCreate, username: str = Depends(get_current_user)):
    global current_id
    current_id += 1
    capsule_data = CapsuleResponse(
        id=current_id,
        text=capsule.text,
        date_open=capsule.date_open,
        author=username
    )
    capsules.append(capsule_data)
    return capsule_data