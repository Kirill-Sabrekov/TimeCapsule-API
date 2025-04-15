from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from database import Base

class User(Base):
    __tablename__ = "auth_user"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)

class Capsule(Base):
    __tablename__ = "auth_app_capsule"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String)
    date_open = Column(DateTime)
    author_id = Column(Integer, ForeignKey("auth_user.id"))
    created_at = Column(DateTime)