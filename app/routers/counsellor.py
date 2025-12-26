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

# ============================================================================
# SELF-SERVICE ENDPOINTS (/me) - Must be before /{id} routes to prevent conflicts
# ============================================================================

@router.get("/me", response_model=schemas.UnifiedUserResponse)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: schemas.UserCreate = Depends(oauth2.get_current_user)
):
    """Get the complete profile of the logged-in user (User or Counsellor)"""
    import json
    
    # Check if user is a counsellor first
    counsellor = db.query(models.Counsellor).filter(
        models.Counsellor.email == current_user.email
    ).first()
    
    if counsellor:
        # Parse certificates JSON for counsellor
        response_data = schemas.UnifiedUserResponse(
            id=counsellor.id,
            email=counsellor.email,
            role=counsellor.role,
            created_at=counsellor.created_at,
            name=counsellor.name,
            phone_number=counsellor.phone_number,
            gender=counsellor.gender,
            country=counsellor.country,
            state=counsellor.state,
            date_of_birth=counsellor.date_of_birth,
            address=counsellor.address,
            years_of_experience=counsellor.years_of_experience,
            has_certification=counsellor.has_certification,
            denomination=counsellor.denomination,
            will_attend_ymr=counsellor.will_attend_ymr,
            is_available_for_training=counsellor.is_available_for_training,
            profile_image_url=counsellor.profile_image_url,
            certificates=json.loads(counsellor.certificates) if counsellor.certificates else None,
            is_active=counsellor.is_active
        )
        return response_data
    
    # Check if regular user
    user = db.query(models.User).filter(
        models.User.email == current_user.email
    ).first()
    
    if user:
        return schemas.UnifiedUserResponse(
            id=user.id,
            email=user.email,
            role=user.role,
            created_at=user.created_at
        )
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User profile not found"
    )


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
    """Update the logged-in user's profile (Counsellor only - Users have limited profile fields)"""
    from app.services.s3_upload import s3_service
    import json
    
    # Check if user is a counsellor (only counsellors have extended profiles to update)
    counsellor_query = db.query(models.Counsellor).filter(
        models.Counsellor.email == current_user.email
    )
    counsellor = counsellor_query.first()
    
    if not counsellor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Only counsellors can update profile via this endpoint. Regular users have limited profile fields."
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
        
        # Update counsellor only if there are fields to update
        if update_dict:
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
    """Change the logged-in user's password"""
    from app import utils
    
    # Check counsellor first
    counsellor = db.query(models.Counsellor).filter(
        models.Counsellor.email == current_user.email
    ).first()
    
    if counsellor:
        # Verify current password
        if not utils.verify(password_data.current_password, counsellor.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Hash and update new password
        counsellor.password = utils.hash(password_data.new_password)
        db.commit()
        
        return {
            "status": "success",
            "message": "Password changed successfully"
        }
    
    # Check regular user
    user = db.query(models.User).filter(
        models.User.email == current_user.email
    ).first()
    
    if user:
        # Verify current password
        if not utils.verify(password_data.current_password, user.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Hash and update new password
        user.password = utils.hash(password_data.new_password)
        db.commit()
        
        return {
            "status": "success",
            "message": "Password changed successfully"
        }
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )


# ============================================================================
# PUBLIC ENDPOINTS - No authentication required
# ============================================================================

@router.post("/check-password-status", status_code=status.HTTP_200_OK)
def check_password_status(
    email_data: dict,
    db: Session = Depends(get_db)
):
    """
    Check if a counsellor needs to set up their password.
    Returns the account status to help guide the user flow.
    """
    email = email_data.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required"
        )
    
    # Find counsellor by email
    counsellor = db.query(models.Counsellor).filter(
        models.Counsellor.email == email
    ).first()
    
    if not counsellor:
        return {
            "status": "not_found",
            "message": "No counsellor account found with this email",
            "needs_password_setup": False,
            "is_active": False
        }
    
    if not counsellor.is_active:
        return {
            "status": "inactive",
            "message": "Account is not yet activated. Please contact the administrator.",
            "needs_password_setup": False,
            "is_active": False
        }
    
    if not counsellor.password:
        return {
            "status": "needs_password",
            "message": "Please set up your password to continue",
            "needs_password_setup": True,
            "is_active": True
        }
    
    return {
        "status": "ready",
        "message": "Account is ready. Please login with your credentials.",
        "needs_password_setup": False,
        "is_active": True
    }


@router.post("/setup-password", status_code=status.HTTP_200_OK)
def setup_password(
    password_data: schemas.PasswordSetupRequest,
    db: Session = Depends(get_db)
):
    """
    Allow activated counsellors without passwords to set their initial password.
    This is a public endpoint for first-time password setup.
    """
    from app import utils
    
    # Find counsellor by email
    counsellor = db.query(models.Counsellor).filter(
        models.Counsellor.email == password_data.email
    ).first()
    
    if not counsellor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No counsellor account found with this email"
        )
    
    # Check if counsellor is activated
    if not counsellor.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is not yet activated. Please contact the administrator."
        )
    
    # Check if password is already set
    if counsellor.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password already set. Please use the login page or reset password if you forgot it."
        )
    
    # Set the password
    counsellor.password = utils.hash(password_data.password)
    db.commit()
    
    return {
        "status": "success",
        "message": "Password set successfully. You can now login with your credentials."
    }


# ============================================================================
# ADMIN ENDPOINTS - Must come after /me routes
# ============================================================================

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
    update_data: schemas.AdminCounsellorUpdate,
    db: Session = Depends(get_db),
    current_user: schemas.UserCreate = Depends(oauth2.get_current_user)
):
    """
    Update counsellor (Admin/Super-admin only).
    Accepts JSON body with counsellor fields including is_active, role, and password.
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
    
    # Build update dict from provided fields (exclude None values)
    update_dict = update_data.model_dump(exclude_unset=True, exclude_none=True)
    
    # Handle role update (super-admin only)
    if "role" in update_dict:
        if current_user.role.value != "super-admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super-admins can change counsellor roles"
            )
        # Validate role
        valid_roles = ["user", "admin", "super-admin"]
        if update_dict["role"] not in valid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
            )
    
    # Handle password update (hash it)
    if "password" in update_dict:
        update_dict["password"] = utils.hash(update_dict["password"])
    
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


# Note: All /me endpoints are defined earlier in the file (before /{id} routes)
# to prevent route matching conflicts

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
