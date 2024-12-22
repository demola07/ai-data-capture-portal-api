from fastapi import Response, status, HTTPException, Depends, APIRouter
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from typing import List, Optional
from sqlalchemy import or_
from .. import models, schemas, oauth2
from ..database import get_db


router = APIRouter(
    prefix="/counsellee",
    tags=['Counsellees']
)

@router.get("/", response_model=schemas.CounselleeResponseWrapper)
def get_counsellees(db: Session = Depends(get_db), current_user: schemas.UserCreate = Depends(oauth2.get_current_user), limit: int = 10, skip: int = 0, searchQuery: Optional[str] = ""):
    try:
        if current_user.role not in ("admin", "super-admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to access this resource"
            )
        
        # Apply filtering
        query = db.query(models.Counsellee).filter(
            or_(
                models.Counsellee.name.ilike(f"%{searchQuery}%"),
                models.Counsellee.email.ilike(f"%{searchQuery}%"),
                models.Counsellee.phone_number.ilike(f"%{searchQuery}%")
            )
        )

        # Get the total count of documents
        total_count = query.count()

        # Paginate the results
        counsellees = query.limit(limit).offset(skip).all()

        if not counsellees:
            return {
                "status": "success",
                "message": "No data found",
                "data": [],
                "total": 0
            }

        return schemas.CounselleeResponseWrapper(
        status="success",
        total=total_count,
        data=[schemas.CounselleeResponse.model_validate(counsellee) for counsellee in counsellees]
        )
    
    except HTTPException as http_exc:
        # Let FastAPI handle HTTP exceptions directly
        raise http_exc
    
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


@router.get("/{param}", response_model=schemas.CounselleeResponseWrapper)
def get_counsellee(
    param: str,
    db: Session = Depends(get_db),
    current_user: Optional[schemas.UserCreate] = Depends(oauth2.get_current_user_if_available),
):
    try:
        # Check if param is an integer (ID)
        if param.isdigit():
            param = int(param)  # Convert to integer
            # Protected route for ID
            if not current_user or current_user.role not in ("admin", "super-admin"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not authorized to access this resource"
                )
            counsellee = db.query(models.Counsellee).filter(models.Counsellee.id == param).first()
        else:
            # Treat param as an email (unprotected route)
            counsellee = db.query(models.Counsellee).filter(models.Counsellee.email == param).first()

        # Handle not found
        if not counsellee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Counsellee with {'id' if isinstance(param, int) else 'email'}: {param} was not found"
            )

        return {"status": "success", "data": counsellee}
    
    except HTTPException as http_exc:
        # Let FastAPI handle HTTP exceptions directly
        raise http_exc

    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error occurred: {str(e)}"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.CounselleeResponseWrapper)
def create_counsellee(counsellee: schemas.CounselleeCreate, db: Session = Depends(get_db)):
    existing_counsellee = db.query(models.Counsellee).filter(models.Counsellee.email == counsellee.email).first()
    if existing_counsellee:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A counsellee with this email already exists."
        )
    try:

        new_counsellee = models.Counsellee(**counsellee.model_dump(exclude={"id"}))
        db.add(new_counsellee)
        db.commit()
        db.refresh(new_counsellee)
        return { "status": "success", "data": new_counsellee }
    except IntegrityError as e:
        # Handle database integrity errors (e.g., unique constraint violations)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Integrity error: {str(e.orig)}"
        )
    
    except HTTPException as http_exc:
        # Let FastAPI handle HTTP exceptions directly
        raise http_exc
    
    except SQLAlchemyError as e:
        # Handle other general SQLAlchemy errors
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the request."
        )
    
    except Exception as e:
        # Handle unexpected errors
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.put("/{id}", response_model=schemas.CounselleeResponseWrapper)
def update_counsellee(id: int, updated_counsellee_data: schemas.CounselleeUpdate, db: Session = Depends(get_db), current_user: schemas.UserCreate = Depends(oauth2.get_current_user)):

    if current_user.role.value != "super-admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this resource"
        )

    counsellee_query = db.query(models.Counsellee).filter(models.Counsellee.id == id)

    counsellee = counsellee_query.first()

    if counsellee == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"counsellee with id: {id} does not exist")

    counsellee_query.update(updated_counsellee_data.model_dump(), synchronize_session=False)
    db.commit()
    return { "status": "success", "data": counsellee_query.first() }


@router.delete("/bulk-delete", status_code=status.HTTP_200_OK)
def delete_multiple_counsellees(
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
    counsellees_query = db.query(models.Counsellee).filter(models.Counsellee.id.in_(bulk_delete.ids))
    counsellees = counsellees_query.all()

    # Check if any of the provided IDs are not found
    if not counsellees:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No matching counsellees found for the provided IDs."
        )

    # Delete the records
    counsellees_query.delete(synchronize_session=False)
    db.commit()

    return { "status": "success" }

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_counsellee(id: int, db: Session = Depends(get_db), current_user: schemas.UserCreate = Depends(oauth2.get_current_user)):

    if current_user.role.value != "super-admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this resource"
        )

    counsellee_query = db.query(models.Counsellee).filter(models.Counsellee.id == id)

    counsellee = counsellee_query.first()

    if counsellee == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"counsellee with id: {id} does not exist")

    counsellee_query.delete(synchronize_session=False)
    db.commit()

    return { "status": "success" }
    # return Response(status_code=status.HTTP_204_NO_CONTENT)
