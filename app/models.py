from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Enum as SQLAlchemyEnum
from sqlalchemy.sql.expression import text
from sqlalchemy.sql.sqltypes import TIMESTAMP

from .database import Base
from . import utils
# from enum import Enum

# class Role(str, Enum):
#     USER = "user"
#     ADMIN = "admin"
#     SUPERADMIN = "super-admin"

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
    created_at = Column(TIMESTAMP(timezone=True),
                        nullable=False, server_default=text('now()'))
    
class Counsellor(Base):
    __tablename__ = "counsellors"

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name = Column(String, nullable=False)  # Full Name
    email = Column(String, nullable=False, unique=True)  # Email
    phone_number = Column(String, nullable=True) # Phone Number
    gender = Column(String, nullable=True)     # Gender Enum
    date_of_birth = Column(String, nullable=True)
    address = Column(String, nullable=True)          # Address
    years_of_experience = Column(Integer, nullable=True) # Years of Experience
    has_certification = Column(Boolean, nullable=False, default=False)  # Professional Certification
    denomination = Column(String(100), nullable=True)  # Denomination
    will_attend_ymr_2024 = Column(Boolean, nullable=False, default=True)  # Attendance at Event
    is_available_for_training = Column(Boolean, nullable=False, default=True)  # Availability
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))  # Timestamp



class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True),
                        nullable=False, server_default=text('now()'))
    role = Column(SQLAlchemyEnum(utils.Role), nullable=False)
