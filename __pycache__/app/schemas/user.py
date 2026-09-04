from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    institute: str
    group_number: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    institute: str
    group_number: str

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str