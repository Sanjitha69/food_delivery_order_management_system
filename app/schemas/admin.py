from pydantic import BaseModel, EmailStr, Field
from app.models import Role


class AccountCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=7, max_length=20)
    role: Role
