from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List, Union
from . import utils

class ConvertBase(BaseModel):
    name: str
    gender: str
    email: str
    phone_number: str
    date_of_birth: str
    relationship_status: str
    country: str
    state: str
    address: str
    nearest_bus_stop: str
    is_student: bool = False
    age_group: str
    school: str
    occupation: str
    denomination: str
    availability_for_follow_up: bool = True
    online: bool = False


class ConvertCreate(ConvertBase):
    pass

class ConvertUpdate(ConvertBase):
    pass

class ConvertResponse(ConvertBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

class ConvertResponseWrapper(BaseModel):
    status: Optional[str] = None
    message: Optional[str] = None
    data: Union[ConvertResponse, List[ConvertResponse]]
    total: Optional[int] = 0
    # data: List[ConvertResponse]

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: utils.Role


class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime
    role: utils.Role

    class Config:
        from_attributes = True
        # orm_mode = True


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class TokenData(BaseModel):
    id: Optional[str] = None
    role: utils.Role


class CounsellorBase(BaseModel):
    name: str
    email: str
    phone_number: str
    gender: str
    country: str
    state: str
    date_of_birth: str
    address: str
    years_of_experience: int
    has_certification : bool = False
    denomination: str
    will_attend_ymr_2024 : bool = True
    is_available_for_training : bool = True


class CounsellorCreate(CounsellorBase):
    pass

class CounsellorUpdate(CounsellorBase):
    pass

class CounsellorResponse(CounsellorBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

class CounsellorResponseWrapper(BaseModel):
    status: Optional[str] = None
    message: Optional[str] = None
    data: Union[CounsellorResponse, List[CounsellorResponse]]
    total: Optional[int] = 0

class BulkDelete(BaseModel):
    ids: List[int]

class FileInfo(BaseModel):
    file_name: str
    file_type: str

class PresignedURLResponse(BaseModel):
    upload_urls: List[dict]


class CounselleeBase(BaseModel):
    name: str
    gender: str
    email: str
    phone_number: str
    date_of_birth: str
    relationship_status: str
    country: str
    state: str
    address: str
    nearest_bus_stop: str
    is_student: bool = False
    age_group: str
    school: str
    occupation: str
    denomination: str
    counselling_reason: str
    counsellor_name: str = ""
    counsellor_comments: str = ""
    attended_to: bool = False


class CounselleeCreate(CounselleeBase):
    pass

class CounselleeUpdate(CounselleeBase):
    pass

class CounselleeResponse(CounselleeBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
        # orm_mode = True

class CounselleeResponseWrapper(BaseModel):
    status: Optional[str] = None
    message: Optional[str] = None
    data: Union[CounselleeResponse, List[CounselleeResponse]]
    total: Optional[int] = 0
