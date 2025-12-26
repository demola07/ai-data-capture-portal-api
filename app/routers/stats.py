"""
Statistics router - provides database statistics and counts
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.oauth2 import get_current_user
from app.models import Convert, Counsellee, Counsellor, User

router = APIRouter(prefix="/stats", tags=["Statistics"])


@router.get("/counts")
def get_database_counts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get counts of converts, counsellees, and counsellors in the database.
    
    Returns:
        - converts: Total number of converts
        - counsellees: Total number of counsellees
        - counsellors: Total number of counsellors
    """
    converts_count = db.query(Convert).count()
    counsellees_count = db.query(Counsellee).count()
    counsellors_count = db.query(Counsellor).count()
    
    return {
        "converts": converts_count,
        "counsellees": counsellees_count,
        "counsellors": counsellors_count,
        "total": converts_count + counsellees_count + counsellors_count
    }
