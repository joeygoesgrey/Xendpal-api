from fastapi import File, UploadFile
from pydantic import BaseModel, ConfigDict, EmailStr
from typing import List, Optional
from datetime import datetime


class Upload(BaseModel):
    file_type: str


class GoogleLoginRequest(BaseModel):
    code: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[EmailStr] = None


class UserBase(BaseModel):
    name: str
    picture: str
    space: int
    max_space: int

    class Config:
        from_attributes = True


class TokenData(BaseModel):
    email: EmailStr


class UploadModelSchema(BaseModel):
    id: str
    name: str
    path: str
    type: str
    created_at: datetime
    size: int
    owner_id: EmailStr

    class Config:
        from_attributes = True


class ShareUploadSchema(BaseModel):
    upload_id: str
    recipient_email: str
    permission: str = "read"
    description: str = None


class DemoAccount(BaseModel):
    email: EmailStr
    password: str


class HistorySchema(BaseModel):
    id: str
    created_at: datetime
    message: str

    class Config:
        from_attributes = True


class RefreshTokenSchema(BaseModel):
    refresh_token: str
