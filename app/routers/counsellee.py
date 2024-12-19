from fastapi import Response, status, HTTPException, Depends, APIRouter
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


@router.get("/{id}", response_model=schemas.CounselleeResponseWrapper)
def get_counsellee(id: int, db: Session = Depends(get_db), current_user: schemas.UserCreate = Depends(oauth2.get_current_user)):
    if current_user.role not in ("admin", "super-admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this resource"
        )

    counsellee = db.query(models.Counsellee).filter(models.Counsellee.id == id).first()

    if not counsellee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"counsellee with id: {id} was not found")

    return { "status": "success", "data": counsellee }


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.CounselleeResponseWrapper)
def create_counsellee(counsellee: schemas.CounselleeCreate, db: Session = Depends(get_db), current_user: schemas.UserCreate = Depends(oauth2.get_current_user)):
    if current_user.role not in ("admin", "super-admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this resource"
        )

    new_counsellee = models.Counsellee(**counsellee.model_dump(exclude={"id"}))
    db.add(new_counsellee)
    db.commit()
    db.refresh(new_counsellee)
    return { "status": "success", "data": new_counsellee }


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