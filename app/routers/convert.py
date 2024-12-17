from fastapi import Response, status, HTTPException, Depends, APIRouter
from sqlalchemy.orm import Session
from typing import List, Optional
from sqlalchemy import or_
from .. import models, schemas, oauth2
from ..database import get_db


router = APIRouter(
    prefix="/converts",
    tags=['Converts']
)

@router.get("/", response_model=schemas.ConvertResponseWrapper)
def get_converts(db: Session = Depends(get_db), current_user: schemas.UserCreate = Depends(oauth2.get_current_user), limit: int = 10, skip: int = 0, search: Optional[str] = ""):
    if current_user.role not in ("admin", "super-admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this resource"
        )

    converts = db.query(models.Convert).filter(
        or_(
                models.Convert.name.ilike(f"%{search}%"),
                models.Convert.email.ilike(f"%{search}%"),
                models.Convert.phone_number.ilike(f"%{search}%")
            )
    ).limit(limit).offset(skip).all()

    if not converts:
        return {
            "status": "success",
            "message": "No data found",
            "data": []
        }

    # return { status: "success", "data": converts }
    return schemas.ConvertResponseWrapper(status="success", data=[schemas.ConvertResponse(**convert.__dict__) for convert in converts])


@router.get("/{id}", response_model=schemas.ConvertResponseWrapper)
def get_convert(id: int, db: Session = Depends(get_db), current_user: schemas.UserCreate = Depends(oauth2.get_current_user)):
    if current_user.role not in ("admin", "super-admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this resource"
        )

    convert = db.query(models.Convert).filter(models.Convert.id == id).first()

    if not convert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"convert with id: {id} was not found")

    return { "status": "success", "data": convert }


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.ConvertResponseWrapper)
def create_convert(convert: schemas.ConvertCreate, db: Session = Depends(get_db), current_user: schemas.UserCreate = Depends(oauth2.get_current_user)):
    if current_user.role not in ("admin", "super-admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this resource"
        )

    new_convert = models.Convert(**convert.model_dump(exclude={"id"}))
    db.add(new_convert)
    db.commit()
    db.refresh(new_convert)
    return { "status": "success", "data": new_convert }
    

@router.post("/bulk", status_code=status.HTTP_201_CREATED, response_model=List[schemas.ConvertResponseWrapper])
def create_converts(
    converts: List[schemas.ConvertCreate],
    db: Session = Depends(get_db),
    current_user: schemas.UserCreate = Depends(oauth2.get_current_user)
):
    # Check if the current user is authorized
    if current_user.role not in ("admin", "super-admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this resource"
        )

    # Create a list of `Convert` objects to add to the database
    new_converts = [models.Convert(**convert.model_dump(exclude={"id"})) for convert in converts]
    
    # Add all converts to the database
    db.add_all(new_converts)
    db.commit()
    
    return { "message": "All data have been added successfully.", "status": "success" }



@router.put("/{id}", response_model=schemas.ConvertResponseWrapper)
def update_convert(id: int, updated_convert_data: schemas.ConvertUpdate, db: Session = Depends(get_db), current_user: schemas.UserCreate = Depends(oauth2.get_current_user)):

    print("user", current_user)
    print("user roleee", current_user.role.value)
    if current_user.role.value != "super-admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this resource"
        )

    convert_query = db.query(models.Convert).filter(models.Convert.id == id)

    convert = convert_query.first()

    if convert == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"convert with id: {id} does not exist")

    convert_query.update(updated_convert_data.model_dump(), synchronize_session=False)
    db.commit()
    return { "status": "success", "data": convert_query.first() }

@router.delete("/bulk-delete", status_code=status.HTTP_200_OK)
def delete_multiple_converts(
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
    converts_query = db.query(models.Convert).filter(models.Convert.id.in_(bulk_delete.ids))
    converts = converts_query.all()

    # Check if any of the provided IDs are not found
    if not converts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No matching converts found for the provided IDs."
        )

    # Delete the records
    converts_query.delete(synchronize_session=False)
    db.commit()

    return { "status": "success" }

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_convert(id: int, db: Session = Depends(get_db), current_user: schemas.UserCreate = Depends(oauth2.get_current_user)):

    if current_user.role.value != "super-admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this resource"
        )

    convert_query = db.query(models.Convert).filter(models.Convert.id == id)

    convert = convert_query.first()

    if convert == None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"convert with id: {id} does not exist")

    convert_query.delete(synchronize_session=False)
    db.commit()

    return { "status": "success" }
    # return Response(status_code=status.HTTP_204_NO_CONTENT)
