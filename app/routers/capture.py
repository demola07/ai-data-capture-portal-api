from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from typing import List
from ..services import ai_extraction
from .. import schemas, oauth2

router = APIRouter(
    prefix="/capture",
    tags=['Capture']
)

@router.post("/extract", response_model=List[schemas.ConvertBase])
async def extract_data(
    files: List[UploadFile] = File(...),
    current_user: schemas.UserCreate = Depends(oauth2.get_current_user)
):
    """
    Extracts data from uploaded form images (JPEG, PNG, PDF) using the configured AI model.
    Returns a list of extracted data objects matching the Convert schema.
    """
    # Authorization check (optional: restrict to admin/counsellor?)
    # For now, any authenticated user can extract.
    
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files uploaded"
        )

    # Validate file types
    valid_types = ["image/jpeg", "image/png", "image/webp", "application/pdf"]
    for file in files:
        if file.content_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type: {file.filename}. Only JPEG, PNG, WEBP, and PDF are allowed."
            )

    try:
        # Process files in batch
        results = await ai_extraction.process_batch(files)
        
        # Check for errors in results
        cleaned_results = []
        for res in results:
            if "error" in res:
                # Log error or handle partial failure
                # For now, we include it or skip? 
                # The schema expects ConvertBase, so we can't return the error dict directly if strict.
                # Let's return what we can, or raise if critical.
                # Ideally, we should return a wrapper with status for each file.
                # But to match the plan, we return List[ConvertBase].
                # If extraction failed, we might skip it or return empty defaults.
                continue 
            cleaned_results.append(res)
            
        return cleaned_results

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Extraction failed: {str(e)}"
        )
