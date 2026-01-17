from fastapi import Response, status, HTTPException, Depends, APIRouter
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from typing import List, Optional
from sqlalchemy import or_
from .. import models, schemas, oauth2
from ..database import get_db
import csv
import io


router = APIRouter(
    prefix="/converts",
    tags=['Converts']
)

@router.get("/", response_model=schemas.ConvertResponseWrapper)
def get_converts(
    db: Session = Depends(get_db), 
    current_user: schemas.UserCreate = Depends(oauth2.get_current_user), 
    limit: int = 10, 
    skip: int = 0, 
    searchQuery: Optional[str] = "",
    state: Optional[str] = None,
    country: Optional[str] = None,
    address: Optional[str] = None
):
    """
    Get converts with advanced filtering options.
    
    - **searchQuery**: Search by name, email, or phone number
    - **state**: Filter by state (case-insensitive pattern match)
    - **country**: Filter by country (case-insensitive pattern match)
    - **address**: Filter by address (case-insensitive pattern match)
    - **limit**: Number of records per page
    - **skip**: Number of records to skip (pagination)
    """
    try:
        # Authorization check
        if current_user.role not in ("admin", "super-admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to access this resource"
            )

        # Start with base query
        query = db.query(models.Convert)
        
        # Apply general search filter (name, email, phone)
        if searchQuery:
            query = query.filter(
                or_(
                    models.Convert.name.ilike(f"%{searchQuery}%"),
                    models.Convert.email.ilike(f"%{searchQuery}%"),
                    models.Convert.phone_number.ilike(f"%{searchQuery}%")
                )
            )
        
        # Apply state filter
        if state:
            query = query.filter(models.Convert.state.ilike(f"%{state}%"))
        
        # Apply country filter
        if country:
            query = query.filter(models.Convert.country.ilike(f"%{country}%"))
        
        # Apply address filter
        if address:
            query = query.filter(models.Convert.address.ilike(f"%{address}%"))

        # Get the total count of records
        total_count = query.count()

        # Paginate the results
        converts = query.limit(limit).offset(skip).all()

        if not converts:
            return {
                "status": "success",
                "message": "No data found",
                "data": [],
                "total": 0
            }

        # Return the results with the total count
        return schemas.ConvertResponseWrapper(
            status="success",
            total=total_count,
            data=[schemas.ConvertResponse(**convert.__dict__) for convert in converts]
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


@router.get("/{id}", response_model=schemas.ConvertResponseWrapper)
def get_convert(id: int, db: Session = Depends(get_db), current_user: schemas.UserCreate = Depends(oauth2.get_current_user)):
    try:
        # Authorization check
        if current_user.role not in ("admin", "super-admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to access this resource"
            )

        # Query the specific convert record by ID
        convert = db.query(models.Convert).filter(models.Convert.id == id).first()

        if not convert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Convert with id: {id} was not found"
            )

        return {"status": "success", "data": convert}
    
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


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.ConvertResponseWrapper)
def create_convert(convert: schemas.ConvertCreate, db: Session = Depends(get_db)):
    try:
        # Attempt to create a new convert record
        new_convert = models.Convert(**convert.model_dump(exclude={"id"}))
        db.add(new_convert)
        db.commit()
        db.refresh(new_convert)
        return {"status": "success", "data": new_convert}
    
    except IntegrityError as e:
        # Handle database integrity errors (e.g., unique constraint violations)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Integrity error: {str(e.orig)}"
        )
    
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
    

@router.post("/bulk", status_code=status.HTTP_201_CREATED, response_model=schemas.ConvertResponseWrapper)
def create_converts(
    converts: List[schemas.ConvertCreate],
    db: Session = Depends(get_db),
    current_user: schemas.UserCreate = Depends(oauth2.get_current_user)
):
    # Check if the current user is authorized
    if current_user.role not in ("user", "admin", "super-admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this resource"
        )

    # Create a list of `Convert` objects to add to the database
    new_converts = [models.Convert(**convert.model_dump(exclude={"id"})) for convert in converts]
    
    # Add all converts to the database
    db.add_all(new_converts)
    db.commit()
    
    # Refresh all objects to get their IDs
    for convert in new_converts:
        db.refresh(convert)
    
    return { 
        "status": "success", 
        "message": f"Successfully created {len(new_converts)} converts",
        "data": new_converts,
        "total": len(new_converts)
    }



@router.put("/{id}", response_model=schemas.ConvertResponseWrapper)
def update_convert(id: int, updated_convert_data: schemas.ConvertUpdate, db: Session = Depends(get_db), current_user: schemas.UserCreate = Depends(oauth2.get_current_user)):

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


@router.get("/download")
def download_converts(
    db: Session = Depends(get_db),
    current_user: schemas.UserCreate = Depends(oauth2.get_current_user),
    searchQuery: Optional[str] = "",
    state: Optional[str] = None,
    country: Optional[str] = None,
    address: Optional[str] = None,
    columns: Optional[str] = None
):
    """
    Download converts data as CSV with optional column selection.
    
    Filters (same as GET /converts):
    - **searchQuery**: Search by name, email, or phone number
    - **state**: Filter by state (case-insensitive)
    - **country**: Filter by country (case-insensitive)
    - **address**: Filter by address (case-insensitive)
    
    Column Selection:
    - **columns**: Comma-separated list of columns to include (e.g., "name,phone_number,address,state")
    - If not provided, all columns are included
    
    Available columns:
    id, name, gender, email, phone_number, date_of_birth, relationship_status,
    country, state, address, nearest_bus_stop, is_student, age_group, school,
    occupation, denomination, availability_for_follow_up, online, created_at
    
    Example: /api/converts/download?state=Lagos&columns=name,phone_number,address
    """
    try:
        # Authorization check
        if current_user.role not in ("admin", "super-admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to access this resource"
            )

        # Start with base query
        query = db.query(models.Convert)
        
        # Apply general search filter (name, email, phone)
        if searchQuery:
            query = query.filter(
                or_(
                    models.Convert.name.ilike(f"%{searchQuery}%"),
                    models.Convert.email.ilike(f"%{searchQuery}%"),
                    models.Convert.phone_number.ilike(f"%{searchQuery}%")
                )
            )
        
        # Apply state filter
        if state:
            query = query.filter(models.Convert.state.ilike(f"%{state}%"))
        
        # Apply country filter
        if country:
            query = query.filter(models.Convert.country.ilike(f"%{country}%"))
        
        # Apply address filter
        if address:
            query = query.filter(models.Convert.address.ilike(f"%{address}%"))

        # Get all matching records (no pagination for download)
        converts = query.all()

        if not converts:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No converts found matching the filters"
            )

        # Define all available columns
        all_columns = [
            'id', 'name', 'gender', 'email', 'phone_number', 'date_of_birth',
            'relationship_status', 'country', 'state', 'address', 'nearest_bus_stop',
            'is_student', 'age_group', 'school', 'occupation', 'denomination',
            'availability_for_follow_up', 'online', 'created_at'
        ]
        
        # Parse selected columns
        if columns:
            selected_columns = [col.strip() for col in columns.split(',')]
            # Validate columns
            invalid_columns = [col for col in selected_columns if col not in all_columns]
            if invalid_columns:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid columns: {', '.join(invalid_columns)}. Available columns: {', '.join(all_columns)}"
                )
        else:
            selected_columns = all_columns

        # Create CSV in memory
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=selected_columns)
        writer.writeheader()
        
        # Write data rows
        for convert in converts:
            row = {}
            for col in selected_columns:
                value = getattr(convert, col, None)
                # Convert boolean to string for CSV
                if isinstance(value, bool):
                    row[col] = str(value)
                else:
                    row[col] = value if value is not None else ""
            writer.writerow(row)
        
        # Prepare the response
        output.seek(0)
        
        # Generate filename with filters
        filename_parts = ["converts"]
        if state:
            filename_parts.append(f"state_{state}")
        if country:
            filename_parts.append(f"country_{country}")
        if searchQuery:
            filename_parts.append("filtered")
        filename = "_".join(filename_parts) + ".csv"
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    
    except HTTPException:
        raise
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
