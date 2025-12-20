"""
Template management endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.database import get_db
from app.oauth2 import get_current_user
from app.models import User, NotificationTemplate
from app.schemas import TemplateCreate, TemplateUpdate, TemplateResponse
from app.services.notifications.template_renderer import TemplateRenderer

router = APIRouter(prefix="/templates", tags=["Templates"])


@router.post("/", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    template: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new notification template"""
    
    # Check if template name already exists
    existing = db.query(NotificationTemplate).filter(
        NotificationTemplate.name == template.name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Template with name '{template.name}' already exists"
        )
    
    # Extract variables from template
    body_vars = TemplateRenderer.extract_variables(template.body)
    html_vars = TemplateRenderer.extract_variables(template.html_body or "")
    all_vars = list(set(body_vars + html_vars))
    
    # Create template
    new_template = NotificationTemplate(
        name=template.name,
        type=template.type,
        subject=template.subject,
        body=template.body,
        html_body=template.html_body,
        header_image=template.header_image,
        description=template.description,
        variables=str(all_vars)  # Store as string representation
    )

    
    db.add(new_template)
    db.commit()
    db.refresh(new_template)
    
    return new_template


@router.get("/", response_model=List[TemplateResponse])
async def list_templates(
    type: str = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all notification templates"""
    query = db.query(NotificationTemplate)
    
    if type:
        query = query.filter(NotificationTemplate.type == type)
    
    if active_only:
        query = query.filter(NotificationTemplate.is_active == True)
    
    templates = query.all()
    return templates


@router.get("/{template_name}", response_model=TemplateResponse)
async def get_template(
    template_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific template by name"""
    template = db.query(NotificationTemplate).filter(
        NotificationTemplate.name == template_name
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_name}' not found"
        )
    
    return template


@router.put("/{template_name}", response_model=TemplateResponse)
async def update_template(
    template_name: str,
    updates: TemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an existing template"""
    template = db.query(NotificationTemplate).filter(
        NotificationTemplate.name == template_name
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_name}' not found"
        )
    
    # Update fields
    if updates.subject is not None:
        template.subject = updates.subject
    if updates.body is not None:
        template.body = updates.body
    if updates.html_body is not None:
        template.html_body = updates.html_body
    if updates.header_image is not None:
        template.header_image = updates.header_image
    if updates.description is not None:
        template.description = updates.description
    if updates.is_active is not None:
        template.is_active = updates.is_active
    
    # Re-extract variables
    body_vars = TemplateRenderer.extract_variables(template.body)
    html_vars = TemplateRenderer.extract_variables(template.html_body or "")
    all_vars = list(set(body_vars + html_vars))
    template.variables = str(all_vars)
    template.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(template)
    
    return template


@router.delete("/{template_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a template (soft delete by setting is_active=False)"""
    template = db.query(NotificationTemplate).filter(
        NotificationTemplate.name == template_name
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_name}' not found"
        )
    
    # Soft delete
    template.is_active = False
    template.updated_at = datetime.utcnow()
    db.commit()
    
    return None


@router.get("/variables/standard")
async def get_standard_variables(
    current_user: User = Depends(get_current_user)
):
    """Get list of standard variables available in all templates"""
    return {
        "standard_variables": TemplateRenderer.get_standard_variables(),
        "usage": "Use {{variable_name}} in your templates"
    }
