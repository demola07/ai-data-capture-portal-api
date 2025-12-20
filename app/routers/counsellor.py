from fastapi import Response, status, HTTPException, Depends, APIRouter, File, UploadFile
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from typing import List, Optional
from sqlalchemy import or_
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
    counsellor: schemas.CounsellorCreate,
    profile_image: Optional[UploadFile] = File(None),
    certificates: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db)
):
    """
    Create a new counsellor with optional profile image and certificates.
    If password is provided, account can be used for login (requires activation).
    Default role is 'user', is_active defaults to False.
    """
    from app.services.s3_upload import s3_service
    from app import utils
    import json
    
    existing_counsellor = db.query(models.Counsellor).filter(models.Counsellor.email == counsellor.email).first()
    if existing_counsellor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A counsellor with this email already exists."
        )
    try:
        # Prepare counsellor data
        counsellor_data = counsellor.model_dump(exclude={"id", "password"})
        
        # Hash password if provided
        if counsellor.password:
            counsellor_data["password"] = utils.hash(counsellor.password)
        
        # Set default role if not provided
        if "role" not in counsellor_data or counsellor_data.get("role") is None:
            counsellor_data["role"] = utils.Role.USER
        
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
            detail="An error occurred while processing the request."
        )
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.put("/{id}", response_model=schemas.CounsellorResponseWrapper)
def update_counsellor(id: int, updated_counsellor_data: schemas.CounsellorUpdate, db: Session = Depends(get_db), current_user: schemas.UserCreate = Depends(oauth2.get_current_user)):
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

    counsellor_query.update(updated_counsellor_data.model_dump(), synchronize_session=False)
    db.commit()
    return { "status": "success", "data": counsellor_query.first() }


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
    updated_data: schemas.CounsellorUpdate,
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
        # Prepare update data
        update_dict = updated_data.model_dump(exclude_unset=True)
        
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

@router.put("/{id}/activate", response_model=schemas.CounsellorResponseWrapper)
def activate_counsellor(
    id: int,
    db: Session = Depends(get_db),
    current_user: schemas.UserCreate = Depends(oauth2.get_current_user)
):
    """Activate a counsellor account (super-admin only)"""
    import json
    
    if current_user.role.value != "super-admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super-admin can activate counsellors"
        )
    
    counsellor_query = db.query(models.Counsellor).filter(models.Counsellor.id == id)
    counsellor = counsellor_query.first()
    
    if not counsellor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Counsellor with id: {id} not found"
        )
    
    counsellor_query.update({"is_active": True}, synchronize_session=False)
    db.commit()
    db.refresh(counsellor)
    
    # Parse certificates for response
    response_data = schemas.CounsellorResponse.from_orm(counsellor)
    if counsellor.certificates:
        response_data.certificates = json.loads(counsellor.certificates)
    
    return {
        "status": "success",
        "message": "Counsellor activated successfully",
        "data": response_data
    }


@router.put("/{id}/deactivate", response_model=schemas.CounsellorResponseWrapper)
def deactivate_counsellor(
    id: int,
    db: Session = Depends(get_db),
    current_user: schemas.UserCreate = Depends(oauth2.get_current_user)
):
    """Deactivate a counsellor account (super-admin only)"""
    import json
    
    if current_user.role.value != "super-admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super-admin can deactivate counsellors"
        )
    
    counsellor_query = db.query(models.Counsellor).filter(models.Counsellor.id == id)
    counsellor = counsellor_query.first()
    
    if not counsellor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Counsellor with id: {id} not found"
        )
    
    counsellor_query.update({"is_active": False}, synchronize_session=False)
    db.commit()
    db.refresh(counsellor)
    
    # Parse certificates for response
    response_data = schemas.CounsellorResponse.from_orm(counsellor)
    if counsellor.certificates:
        response_data.certificates = json.loads(counsellor.certificates)
    
    return {
        "status": "success",
        "message": "Counsellor deactivated successfully",
        "data": response_data
    }


@router.put("/{id}/role", response_model=schemas.CounsellorResponseWrapper)
def update_counsellor_role(
    id: int,
    role_data: dict,
    db: Session = Depends(get_db),
    current_user: schemas.UserCreate = Depends(oauth2.get_current_user)
):
    """Update a counsellor's role (super-admin only)"""
    import json
    from .. import utils
    
    if current_user.role.value != "super-admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super-admin can update counsellor roles"
        )
    
    # Validate role
    try:
        new_role = utils.Role(role_data.get("role"))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be one of: user, admin, super-admin"
        )
    
    counsellor_query = db.query(models.Counsellor).filter(models.Counsellor.id == id)
    counsellor = counsellor_query.first()
    
    if not counsellor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Counsellor with id: {id} not found"
        )
    
    counsellor_query.update({"role": new_role}, synchronize_session=False)
    db.commit()
    db.refresh(counsellor)
    
    # Parse certificates for response
    response_data = schemas.CounsellorResponse.from_orm(counsellor)
    if counsellor.certificates:
        response_data.certificates = json.loads(counsellor.certificates)
    
    return {
        "status": "success",
        "message": f"Counsellor role updated to {new_role.value}",
        "data": response_data
    }


@router.put("/{id}/password", status_code=status.HTTP_200_OK)
def admin_set_counsellor_password(
    id: int,
    password_data: dict,
    db: Session = Depends(get_db),
    current_user: schemas.UserCreate = Depends(oauth2.get_current_user)
):
    """Set or reset a counsellor's password (super-admin only)"""
    from .. import utils
    
    if current_user.role.value != "super-admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super-admin can set counsellor passwords"
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
