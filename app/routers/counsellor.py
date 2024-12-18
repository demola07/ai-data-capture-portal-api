from fastapi import Response, status, HTTPException, Depends, APIRouter
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
    if current_user.role not in ("admin", "super-admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this resource"
        )
    counsellors = db.query(models.Counsellor).filter(
        or_(
                models.Counsellor.name.ilike(f"%{search}%"),
                models.Counsellor.email.ilike(f"%{search}%"),
                models.Counsellor.phone_number.ilike(f"%{search}%")
            )
    ).limit(limit).offset(skip).all()

    if not counsellors:
        return {
            "status": "success",
            "message": "No data found",
            "data": []
        }

    return schemas.CounsellorResponseWrapper(status="success", data=[schemas.CounsellorResponse(**counsellor.__dict__) for counsellor in counsellors])

@router.get("/{id}", response_model=schemas.CounsellorResponseWrapper)
def get_counsellor(id: int, db: Session = Depends(get_db), current_user: schemas.UserCreate = Depends(oauth2.get_current_user)):
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


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.CounsellorResponseWrapper)
def create_counsellor(counsellor: schemas.CounsellorCreate, db: Session = Depends(get_db)):

    new_counsellor = models.Counsellor(**counsellor.model_dump(exclude={"id"}))
    db.add(new_counsellor)
    db.commit()
    db.refresh(new_counsellor)
    return { "status": "success", "data": new_counsellor }


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
