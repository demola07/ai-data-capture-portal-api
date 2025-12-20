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
        
        user_data = schemas.UserResponse.model_validate(user)
        access_token = oauth2.create_access_token(data={ "user_id": user.id, "user_role": user.role })
        
        return { "access_token": access_token, "token_type": "bearer", "user": user_data.model_dump() }
    
    # Try to find counsellor
    counsellor = db.query(models.Counsellor).filter(
        models.Counsellor.email == user_credentials.username).first()
    
    if counsellor:
        # Counsellor login flow
        if not counsellor.password:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account not set up for login. Please contact administrator.")
        
        if not utils.verify(user_credentials.password, counsellor.password):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=f"Invalid Credentials")
        
        if not counsellor.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is not activated. Please contact administrator.")
        
        counsellor_data = schemas.CounsellorResponse.from_orm(counsellor)
        if counsellor.certificates:
            counsellor_data.certificates = json.loads(counsellor.certificates)
        
        access_token = oauth2.create_access_token(
            data={ "counsellor_id": counsellor.id, "counsellor_email": counsellor.email, "user_role": counsellor.role }
        )
        
        return { "access_token": access_token, "token_type": "bearer", "counsellor": counsellor_data.model_dump() }
    
    # Neither user nor counsellor found
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail=f"Invalid Credentials")