from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# Модель для входных данных
class CapsuleCreate(BaseModel):
    text: str
    date_open: datetime

# Модель для ответа 
class CapsuleResponse(BaseModel):
    id: int
    text: str
    date_open: datetime
    author: str

app = FastAPI()

# Временное хранилище
capsules = []
current_id = 0

@app.get("/status")
async def status():
    return {"status": "running"}

@app.post("/capsules", response_model=CapsuleResponse)
async def create_capsule(capsule: CapsuleCreate):
    global current_id
    current_id += 1
    capsule_data = CapsuleResponse(
        id=current_id,
        text=capsule.text,
        date_open=capsule.date_open,
        author="test_user"
    )
    capsules.append(capsule_data)
    return capsule_data