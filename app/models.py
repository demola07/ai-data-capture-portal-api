from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, TIMESTAMP, text, Text, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship
from .database import Base
from . import utils

class Convert(Base):
    __tablename__ = "converts"

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    date_of_birth = Column(String, nullable=True)
    relationship_status = Column(String, nullable=True)
    country = Column(String, nullable=True)
    state = Column(String, nullable=True)
    address = Column(String, nullable=True)
    nearest_bus_stop = Column(String, nullable=True)
    is_student = Column(Boolean, server_default='FALSE', nullable=True)
    age_group = Column(String, nullable=True)
    school = Column(String, nullable=True)
    occupation = Column(String, nullable=True)
    denomination = Column(String, nullable=True)
    availability_for_follow_up = Column(Boolean, server_default='TRUE', nullable=False)
    online=Column(Boolean, server_default='FALSE', nullable=True)
    created_at = Column(TIMESTAMP(timezone=True),
                        nullable=False, server_default=text('now()'))
    
class Counsellee(Base):
    __tablename__ = "counsellee"

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    email = Column(String, nullable=True, unique=True)
    phone_number = Column(String, nullable=True)
    date_of_birth = Column(String, nullable=True)
    relationship_status = Column(String, nullable=True)
    country = Column(String, nullable=True)
    state = Column(String, nullable=True)
    address = Column(String, nullable=True)
    nearest_bus_stop = Column(String, nullable=True)
    is_student = Column(Boolean, server_default='FALSE', nullable=True)
    age_group = Column(String, nullable=True)
    school = Column(String, nullable=True)
    occupation = Column(String, nullable=True)
    denomination = Column(String, nullable=True)
    counselling_reason= Column(String, nullable=True)
    counsellor_name= Column(String, nullable=True)
    counsellor_comments= Column(String, nullable=True)
    attended_to= Column(Boolean, server_default='FALSE', nullable=True)
    created_at = Column(TIMESTAMP(timezone=True),
                        nullable=False, server_default=text('now()'))
    
class Counsellor(Base):
    __tablename__ = "counsellors"

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name = Column(String, nullable=False)  # Full Name
    email = Column(String, nullable=False, unique=True)  # Email
    password = Column(String, nullable=True)  # Hashed password for authentication
    phone_number = Column(String, nullable=True) # Phone Number
    gender = Column(String, nullable=True)     # Gender Enum
    country = Column(String, nullable=True)
    state = Column(String, nullable=True)
    date_of_birth = Column(String, nullable=True)
    address = Column(String, nullable=True)          # Address
    years_of_experience = Column(Integer, nullable=True) # Years of Experience
    has_certification = Column(Boolean, nullable=False, default=False)  # Professional Certification
    denomination = Column(String(100), nullable=True)  # Denomination
    will_attend_ymr = Column(Boolean, nullable=False, default=True)  # Attendance at Event
    is_available_for_training = Column(Boolean, nullable=False, default=True)  # Availability
    profile_image_url = Column(String, nullable=True)  # S3 URL for profile image
    certificates = Column(String, nullable=True)  # JSON array of certificate S3 URLs
    is_active = Column(Boolean, nullable=False, server_default='FALSE')  # Account activation status
    role = Column(SQLAlchemyEnum(utils.Role, values_callable=lambda x: [e.value for e in x]), nullable=False, server_default='user')  # Access level (user, admin, super-admin)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))  # Timestamp



class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True),
                        nullable=False, server_default=text('now()'))
    role = Column(SQLAlchemyEnum(utils.Role, values_callable=lambda x: [e.value for e in x]), nullable=False)


class NotificationBatch(Base):
    """Tracks batches of notifications sent"""
    __tablename__ = "notification_batches"
    
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    batch_id = Column(String, unique=True, nullable=False, index=True)
    type = Column(String, nullable=False)  # email, sms, whatsapp
    subject = Column(String, nullable=True)
    total_recipients = Column(Integer, nullable=False)
    successful = Column(Integer, server_default='0', nullable=False)
    failed = Column(Integer, server_default='0', nullable=False)
    pending = Column(Integer, server_default='0', nullable=False)
    total_cost = Column(String, server_default='0', nullable=False)  # Store as string to avoid precision issues
    provider = Column(String, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)


class NotificationLog(Base):
    """Tracks individual notification sends"""
    __tablename__ = "notification_logs"
    
    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    batch_id = Column(String, ForeignKey("notification_batches.batch_id"), nullable=False, index=True)
    recipient_type = Column(String, nullable=False)  # email, phone
    recipient = Column(String, nullable=False)  # actual email or phone number
    subject = Column(String, nullable=True)
    message = Column(String, nullable=False)
    status = Column(String, nullable=False)  # sent, failed, pending, delivered, bounced
    provider = Column(String, nullable=False)
    provider_message_id = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    cost = Column(String, server_default='0', nullable=False)  # Store as string
    sent_at = Column(TIMESTAMP(timezone=True), nullable=True)
    delivered_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))


class NotificationTemplate(Base):
    __tablename__ = "notification_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    type = Column(String, nullable=False)  # email, sms, whatsapp
    subject = Column(String, nullable=True)  # For email only
    body = Column(Text, nullable=False)
    html_body = Column(Text, nullable=True)  # For email only
    header_image = Column(String, nullable=True)  # Optional header image URL
    description = Column(String, nullable=True)
    variables = Column(String, nullable=True)  # JSON string of required variables
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    
    creator = relationship("User")
