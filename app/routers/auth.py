from fastapi import APIRouter, Depends, status, HTTPException, Response
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import database, schemas, models, utils, oauth2

router = APIRouter(tags=['Authentication'])


@router.post('/login', response_model=schemas.Token)
def login(user_credentials: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    import json
    
    # Try to find user first
    user = db.query(models.User).filter(
        models.User.email == user_credentials.username).first()
    
    if user:
        # User login flow
        if not utils.verify(user_credentials.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=f"Invalid Credentials")
        
        # Create unified user response
        unified_user = schemas.UnifiedUserResponse(
            id=user.id,
            email=user.email,
            created_at=user.created_at,
            role=user.role,
            is_active=True
        )
        access_token = oauth2.create_access_token(data={ "user_id": user.id, "user_role": user.role })
        
        return { "access_token": access_token, "token_type": "bearer", "user": unified_user.model_dump() }
    
    # Try to find counsellor
    counsellor = db.query(models.Counsellor).filter(
        models.Counsellor.email == user_credentials.username).first()
    
    if counsellor:
        # Counsellor login flow
        if not counsellor.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is not activated. Please contact administrator.")
        
        if not counsellor.password:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Password not set. Please set up your password first using the setup password option.")
        
        if not utils.verify(user_credentials.password, counsellor.password):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=f"Invalid Credentials")
        
        # Create unified user response with counsellor data
        certificates_list = json.loads(counsellor.certificates) if counsellor.certificates else None
        
        unified_user = schemas.UnifiedUserResponse(
            id=counsellor.id,
            email=counsellor.email,
            created_at=counsellor.created_at,
            role=counsellor.role,
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
            certificates=certificates_list,
            is_active=counsellor.is_active
        )
        
        access_token = oauth2.create_access_token(
            data={ "counsellor_id": counsellor.id, "counsellor_email": counsellor.email, "user_role": counsellor.role }
        )
        
        return { "access_token": access_token, "token_type": "bearer", "user": unified_user.model_dump() }
    
    # Neither user nor counsellor found
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail=f"Invalid Credentials")