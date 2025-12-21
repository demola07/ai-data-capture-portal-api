from fastapi import Response, status, HTTPException, Depends, APIRouter, File, UploadFile, Form
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from typing import List, Optional
from sqlalchemy import or_
from pydantic import EmailStr
from .. import models, schemas, oauth2
from ..database import get_db


router = APIRouter(
    prefix="/counsellors",
    tags=['Counsellors']
)

@router.get("/", response_model=schemas.CounsellorResponseWrapper)
def get_counsellors(db: Session = Depends(get_db), current_user: schemas.UserCreate = Depends(oauth2.get_current_user), limit: int = 10, skip: int = 0, search: Optional[str] = ""):
    try:
        if current_user.role not in ("admin", "super-admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to access this resource"
            )
        query = db.query(models.Counsellor).filter(
            or_(
                    models.Counsellor.name.ilike(f"%{search}%"),
                    models.Counsellor.email.ilike(f"%{search}%"),
                    models.Counsellor.phone_number.ilike(f"%{search}%")
                )
        )

        # Get the total count of documents
        total_count = query.count()

        counsellors = query.limit(limit).offset(skip).all()

        if not counsellors:
            return {
                "status": "success",
                "message": "No data found",
                "data": [],
                "total": 0
            }

        return schemas.CounsellorResponseWrapper(
            status="success", 
            total= total_count, 
            data=[schemas.CounsellorResponse(**counsellor.__dict__) for counsellor in counsellors]
        )
    
    except SQLAlchemyError as e:
        # Handle SQLAlchemy-specific errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error occurred: {str(e)}"
        )

    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.get("/{id}", response_model=schemas.CounsellorResponseWrapper)
def get_counsellor(id: int, db: Session = Depends(get_db), current_user: schemas.UserCreate = Depends(oauth2.get_current_user)):
    
    try:
        if current_user.role not in ("admin", "super-admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to access this resource"
            )

        counsellor = db.query(models.Counsellor).filter(models.Counsellor.id == id).first()

        if not counsellor:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"counsellor with id: {id} was not found")

        return { "status": "success", "data": counsellor }

    except SQLAlchemyError as e:
        # Handle SQLAlchemy-specific errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error occurred: {str(e)}"
        )

    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.CounsellorResponseWrapper)
async def create_counsellor(
    name: str = Form(...),
    email: EmailStr = Form(...),
    phone_number: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    country: Optional[str] = Form(None),
    state: Optional[str] = Form(None),
    date_of_birth: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    years_of_experience: Optional[int] = Form(None),
    has_certification: bool = Form(False),
    denomination: Optional[str] = Form(None),
    will_attend_ymr: bool = Form(True),
    is_available_for_training: bool = Form(True),
    password: Optional[str] = Form(None),
    profile_image: Optional[UploadFile] = File(None),
    certificates: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db)
):
    """
    Create a new counsellor with optional profile image and certificates.
    All fields are sent as individual form fields.
    If password is provided, account can be used for login (requires activation).
    Default role is 'user', is_active defaults to False.
    """
    from app.services.s3_upload import s3_service
    from app import utils
    import json
    
    existing_counsellor = db.query(models.Counsellor).filter(models.Counsellor.email == email).first()
    if existing_counsellor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A counsellor with this email already exists."
        )
    try:
        # Prepare counsellor data from form fields
        counsellor_data = {
            "name": name,
            "email": email,
            "phone_number": phone_number,
            "gender": gender,
            "country": country,
            "state": state,
            "date_of_birth": date_of_birth,
            "address": address,
            "years_of_experience": years_of_experience,
            "has_certification": has_certification,
            "denomination": denomination,
            "will_attend_ymr": will_attend_ymr,
            "is_available_for_training": is_available_for_training
        }
        
        # Hash password if provided
        if password:
            counsellor_data["password"] = utils.hash(password)
        
        # Set default role if not provided (use string value, not enum)
        if "role" not in counsellor_data or counsellor_data.get("role") is None:
            counsellor_data["role"] = "user"
        
        # Upload profile image if provided
        if profile_image:
            profile_url = await s3_service.upload_file(profile_image, "counsellors/profiles")
            counsellor_data["profile_image_url"] = profile_url
        
        # Upload certificates if provided
        if certificates:
            cert_urls = await s3_service.upload_multiple_files(certificates, "counsellors/certificates")
            counsellor_data["certificates"] = json.dumps(cert_urls)  # Store as JSON string
        
        # Create counsellor (is_active defaults to False)
        new_counsellor = models.Counsellor(**counsellor_data)
        db.add(new_counsellor)
        db.commit()
        db.refresh(new_counsellor)
        
        # Parse certificates JSON for response
        response_data = schemas.CounsellorResponse.from_orm(new_counsellor)
        if new_counsellor.certificates:
            response_data.certificates = json.loads(new_counsellor.certificates)
        
        return { "status": "success", "data": response_data }

    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Integrity error: {str(e.orig)}"
        )
    
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.put("/{id}", response_model=schemas.CounsellorResponseWrapper)
def update_counsellor(
    id: int,
    name: Optional[str] = Form(None),
    phone_number: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    country: Optional[str] = Form(None),
    state: Optional[str] = Form(None),
    date_of_birth: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    years_of_experience: Optional[int] = Form(None),
    has_certification: Optional[bool] = Form(None),
    denomination: Optional[str] = Form(None),
    will_attend_ymr: Optional[bool] = Form(None),
    is_available_for_training: Optional[bool] = Form(None),
    is_active: Optional[bool] = Form(None),
    role: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: schemas.UserCreate = Depends(oauth2.get_current_user)
):
    """
    Update counsellor (Admin/Super-admin only).
    Can update profile fields, activation status, role, and password.
    """
    from app import utils
    
    # Check authorization (admin or super-admin)
    if current_user.role.value not in ["admin", "super-admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this resource"
        )
    
    counsellor_query = db.query(models.Counsellor).filter(models.Counsellor.id == id)
    counsellor = counsellor_query.first()
    
    if counsellor == None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"counsellor with id: {id} does not exist"
        )
    
    # Build update dict from provided fields
    update_dict = {}
    if name is not None:
        update_dict["name"] = name
    if phone_number is not None:
        update_dict["phone_number"] = phone_number
    if gender is not None:
        update_dict["gender"] = gender
    if country is not None:
        update_dict["country"] = country
    if state is not None:
        update_dict["state"] = state
    if date_of_birth is not None:
        update_dict["date_of_birth"] = date_of_birth
    if address is not None:
        update_dict["address"] = address
    if years_of_experience is not None:
        update_dict["years_of_experience"] = years_of_experience
    if has_certification is not None:
        update_dict["has_certification"] = has_certification
    if denomination is not None:
        update_dict["denomination"] = denomination
    if will_attend_ymr is not None:
        update_dict["will_attend_ymr"] = will_attend_ymr
    if is_available_for_training is not None:
        update_dict["is_available_for_training"] = is_available_for_training
    
    # Admin-only fields
    if is_active is not None:
        update_dict["is_active"] = is_active
    
    if role is not None:
        # Only super-admin can change roles
        if current_user.role.value != "super-admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super-admins can change counsellor roles"
            )
        # Validate role
        valid_roles = ["user", "admin", "super-admin"]
        if role not in valid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
            )
        update_dict["role"] = role
    
    if password is not None:
        # Hash the new password
        update_dict["password"] = utils.hash(password)
    
    if update_dict:
        counsellor_query.update(update_dict, synchronize_session=False)
        db.commit()
        db.refresh(counsellor)
    
    return { "status": "success", "data": counsellor }


@router.delete("/bulk-delete", status_code=status.HTTP_200_OK)
def delete_multiple_counsellors(
    bulk_delete: schemas.BulkDelete,
    db: Session = Depends(get_db),
    current_user: schemas.UserCreate = Depends(oauth2.get_current_user)
):
    # Check if the current user is authorized
    if current_user.role.value != "super-admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this resource"
        )

    # Fetch the records to delete
    counsellor_query = db.query(models.Counsellor).filter(models.Counsellor.id.in_(bulk_delete.ids))
    counsellors = counsellor_query.all()

    # Check if any of the provided IDs are not found
    if not counsellors:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No matching counsellors found for the provided IDs."
        )

    # Delete the records
    counsellor_query.delete(synchronize_session=False)
    db.commit()

    return { "status": "success" }

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_counsellor(id: int, db: Session = Depends(get_db), current_user: schemas.UserCreate = Depends(oauth2.get_current_user)):
    if current_user.role.value != "super-admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this resource"
        )

    counsellor_query = db.query(models.Counsellor).filter(models.Counsellor.id == id)

    counsellor = counsellor_query.first()

    if counsellor == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"counsellor with id: {id} does not exist")

    counsellor_query.delete(synchronize_session=False)
    db.commit()

    return { "status": "success" }
    # return Response(status_code=status.HTTP_204_NO_CONTENT)


# ============================================================================
# COUNSELLOR SELF-SERVICE ENDPOINTS
# ============================================================================

@router.get("/me", response_model=schemas.CounsellorProfileResponse)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: schemas.UserCreate = Depends(oauth2.get_current_user)
):
    """Get the complete profile of the logged-in counsellor"""
    import json
    
    if current_user.role.value != "counsellor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only counsellors can access this endpoint"
        )
    
    counsellor = db.query(models.Counsellor).filter(
        models.Counsellor.email == current_user.email
    ).first()
    
    if not counsellor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Counsellor profile not found"
        )
    
    # Parse certificates JSON
    response_data = schemas.CounsellorProfileResponse.from_orm(counsellor)
    if counsellor.certificates:
        response_data.certificates = json.loads(counsellor.certificates)
    
    return response_data


@router.put("/me", response_model=schemas.CounsellorResponseWrapper)
async def update_my_profile(
    name: Optional[str] = Form(None),
    phone_number: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    country: Optional[str] = Form(None),
    state: Optional[str] = Form(None),
    date_of_birth: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    years_of_experience: Optional[int] = Form(None),
    has_certification: Optional[bool] = Form(None),
    denomination: Optional[str] = Form(None),
    will_attend_ymr: Optional[bool] = Form(None),
    is_available_for_training: Optional[bool] = Form(None),
    profile_image: Optional[UploadFile] = File(None),
    certificates: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
    current_user: schemas.UserCreate = Depends(oauth2.get_current_user)
):
    """Update the logged-in counsellor's profile"""
    from app.services.s3_upload import s3_service
    import json
    
    if current_user.role.value != "counsellor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only counsellors can access this endpoint"
        )
    
    counsellor_query = db.query(models.Counsellor).filter(
        models.Counsellor.email == current_user.email
    )
    counsellor = counsellor_query.first()
    
    if not counsellor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Counsellor profile not found"
        )
    
    try:
        # Build update dict from provided fields
        update_dict = {}
        if name is not None:
            update_dict["name"] = name
        if phone_number is not None:
            update_dict["phone_number"] = phone_number
        if gender is not None:
            update_dict["gender"] = gender
        if country is not None:
            update_dict["country"] = country
        if state is not None:
            update_dict["state"] = state
        if date_of_birth is not None:
            update_dict["date_of_birth"] = date_of_birth
        if address is not None:
            update_dict["address"] = address
        if years_of_experience is not None:
            update_dict["years_of_experience"] = years_of_experience
        if has_certification is not None:
            update_dict["has_certification"] = has_certification
        if denomination is not None:
            update_dict["denomination"] = denomination
        if will_attend_ymr is not None:
            update_dict["will_attend_ymr"] = will_attend_ymr
        if is_available_for_training is not None:
            update_dict["is_available_for_training"] = is_available_for_training
        
        # Upload new profile image if provided
        if profile_image:
            # Delete old image if exists
            if counsellor.profile_image_url:
                s3_service.delete_file(counsellor.profile_image_url)
            
            profile_url = await s3_service.upload_file(profile_image, "counsellors/profiles")
            update_dict["profile_image_url"] = profile_url
        
        # Upload new certificates if provided
        if certificates:
            # Delete old certificates if exist
            if counsellor.certificates:
                old_certs = json.loads(counsellor.certificates)
                for cert_url in old_certs:
                    s3_service.delete_file(cert_url)
            
            cert_urls = await s3_service.upload_multiple_files(certificates, "counsellors/certificates")
            update_dict["certificates"] = json.dumps(cert_urls)
        
        # Update counsellor
        counsellor_query.update(update_dict, synchronize_session=False)
        db.commit()
        db.refresh(counsellor)
        
        # Parse certificates for response
        response_data = schemas.CounsellorResponse.from_orm(counsellor)
        if counsellor.certificates:
            response_data.certificates = json.loads(counsellor.certificates)
        
        return { "status": "success", "data": response_data }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )


@router.put("/me/password", status_code=status.HTTP_200_OK)
def change_password(
    password_data: schemas.PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: schemas.UserCreate = Depends(oauth2.get_current_user)
):
    """Change the logged-in counsellor's password"""
    from app import utils
    
    if current_user.role.value != "counsellor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only counsellors can access this endpoint"
        )
    
    # Get user from database
    user = db.query(models.User).filter(models.User.email == current_user.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify current password
    if not utils.verify(password_data.current_password, user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Hash and update new password
    hashed_password = utils.hash(password_data.new_password)
    user.password = hashed_password
    db.commit()
    
    return {
        "status": "success",
        "message": "Password changed successfully"
    }


# ============================================================================
# ADMIN ENDPOINTS - COUNSELLOR ACTIVATION
# ============================================================================

# Removed redundant endpoints - now handled by PUT /{id}
# - activate_counsellor: use PUT /{id} with is_active=true
# - deactivate_counsellor: use PUT /{id} with is_active=false
# - update_counsellor_role: use PUT /{id} with role=<role>
# - admin_set_counsellor_password: use PUT /{id} with password=<password>

@router.put("/{id}/password", status_code=status.HTTP_200_OK)
def admin_set_counsellor_password(
    id: int,
    password_data: dict,
    db: Session = Depends(get_db),
    current_user: schemas.UserCreate = Depends(oauth2.get_current_user)
):
    """
    DEPRECATED: Use PUT /{id} with password field instead.
    Set or reset a counsellor's password (admin only)
    """
    from .. import utils
    
    if current_user.role.value not in ["admin", "super-admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can set counsellor passwords"
        )
    
    if not password_data.get("password"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is required"
        )
    
    counsellor = db.query(models.Counsellor).filter(models.Counsellor.id == id).first()
    
    if not counsellor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Counsellor with id: {id} not found"
        )
    
    # Hash and set new password
    hashed_password = utils.hash(password_data["password"])
    counsellor.password = hashed_password
    db.commit()
    
    return {
        "status": "success",
        "message": "Password updated successfully"
    }
