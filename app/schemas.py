from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List, Union, Dict
from . import utils

class ConvertBase(BaseModel):
    name: Optional[str] = None
    gender: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    date_of_birth: Optional[str] = None
    relationship_status: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    address: Optional[str] = None
    nearest_bus_stop: Optional[str] = None
    is_student: bool = False
    age_group: Optional[str] = None
    school: Optional[str] = None
    occupation: Optional[str] = None
    denomination: Optional[str] = None
    availability_for_follow_up: bool = True
    online: bool = False


class ConvertCreate(ConvertBase):
    pass

class ConvertUpdate(ConvertBase):
    pass

class ConvertResponse(ConvertBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}

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


class UnifiedUserResponse(BaseModel):
    """Unified response for both users and counsellors"""
    id: int
    email: EmailStr
    created_at: datetime
    role: utils.Role
    # User-specific fields (will be None for counsellors)
    # Counsellor-specific fields (will be None for users)
    name: Optional[str] = None
    phone_number: Optional[str] = None
    gender: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    date_of_birth: Optional[str] = None
    address: Optional[str] = None
    years_of_experience: Optional[int] = None
    has_certification: Optional[bool] = None
    denomination: Optional[str] = None
    will_attend_ymr: Optional[bool] = None
    is_available_for_training: Optional[bool] = None
    profile_image_url: Optional[str] = None
    certificates: Optional[List[str]] = None
    is_active: Optional[bool] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UnifiedUserResponse


class TokenData(BaseModel):
    id: Optional[str] = None
    role: utils.Role


# Counsellor Schemas
class CounsellorBase(BaseModel):
    name: str
    email: EmailStr
    phone_number: Optional[str] = None
    gender: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    date_of_birth: Optional[str] = None
    address: Optional[str] = None
    years_of_experience: Optional[int] = None
    has_certification: bool = False
    denomination: Optional[str] = None
    will_attend_ymr: bool = True
    is_available_for_training: bool = True

class CounsellorCreate(CounsellorBase):
    password: Optional[str] = None  # Optional for backward compatibility

class CounsellorUpdate(BaseModel):
    name: Optional[str] = None
    phone_number: Optional[str] = None
    gender: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    date_of_birth: Optional[str] = None
    address: Optional[str] = None
    years_of_experience: Optional[int] = None
    has_certification: Optional[bool] = None
    denomination: Optional[str] = None
    will_attend_ymr: Optional[bool] = None
    is_available_for_training: Optional[bool] = None

class CounsellorResponse(CounsellorBase):
    id: int
    profile_image_url: Optional[str] = None
    certificates: Optional[List[str]] = None
    is_active: bool = False
    role: utils.Role
    created_at: datetime

    model_config = {"from_attributes": True}

class CounsellorProfileResponse(CounsellorResponse):
    """Complete profile response with all details"""
    pass

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

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


# Notification Schemas
class EmailRequest(BaseModel):
    to: List[str]
    subject: str
    body: str
    html_body: Optional[str] = None


class SMSRequest(BaseModel):
    to: List[str]
    message: str


class WhatsAppRequest(BaseModel):
    to: List[str]
    message: str
    template_id: Optional[str] = None


class NotificationResponseSchema(BaseModel):
    success: bool
    recipient: str
    message_id: Optional[str] = None
    provider: str
    status: str
    error: Optional[str] = None
    cost: float = 0.0
    sent_at: Optional[datetime] = None


class BatchNotificationResult(BaseModel):
    total: int
    successful: int
    failed: int
    batch_id: str
    summary: dict
    results: List[NotificationResponseSchema]


# Template Schemas
class TemplateCreate(BaseModel):
    name: str
    type: str  # email, sms, whatsapp
    subject: Optional[str] = None
    body: str
    html_body: Optional[str] = None
    header_image: Optional[str] = None
    description: Optional[str] = None


class TemplateUpdate(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None
    html_body: Optional[str] = None
    header_image: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None



class TemplateResponse(BaseModel):
    id: int
    name: str
    type: str
    subject: Optional[str]
    body: str
    html_body: Optional[str]
    header_image: Optional[str]
    description: Optional[str]
    variables: Optional[str]  # JSON string
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = {"from_attributes": True}


class SendWithTemplateRequest(BaseModel):
    template_name: str
    recipients: List[Dict[str, str]]  # [{"email": "...", "name": "...", "custom_var": "..."}]
    common_variables: Optional[Dict[str, str]] = {}  # Variables same for all recipients
