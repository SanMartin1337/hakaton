from sqlalchemy import Column, Integer, String, Boolean, Text
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    institute = Column(String, nullable=True)
    group = Column(String, nullable=True)

    # --- менторство ---
    is_mentor = Column(Boolean, default=False)
    mentor_bio = Column(Text, nullable=True)
    mentor_skills = Column(String, nullable=True)