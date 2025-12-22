"""restructure_notification_logs_for_bulk_efficiency

Revision ID: 876ab23eb3c0
Revises: 515b7ca1898f
Create Date: 2025-12-22 18:51:54.778231

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '876ab23eb3c0'
down_revision: Union[str, None] = '515b7ca1898f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop old tables if they exist
    op.execute("DROP TABLE IF EXISTS notification_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS notification_batches CASCADE")
    
    # Create new optimized notification_logs table
    op.execute("""
        CREATE TABLE notification_logs (
            id SERIAL PRIMARY KEY,
            batch_id VARCHAR UNIQUE NOT NULL,
            
            -- Notification details
            type VARCHAR NOT NULL,
            channel VARCHAR,
            subject VARCHAR,
            message VARCHAR NOT NULL,
            
            -- Recipient information
            total_recipients INTEGER NOT NULL,
            recipient_sample VARCHAR,
            
            -- Status tracking
            status VARCHAR NOT NULL,
            successful_count INTEGER DEFAULT 0 NOT NULL,
            failed_count INTEGER DEFAULT 0 NOT NULL,
            
            -- Provider details
            provider VARCHAR NOT NULL,
            provider_message_id VARCHAR,
            provider_response VARCHAR,
            
            -- Cost and metadata
            total_cost VARCHAR DEFAULT '0' NOT NULL,
            error_message VARCHAR,
            metadata VARCHAR,
            
            -- User tracking
            created_by INTEGER REFERENCES users(id),
            created_by_email VARCHAR,
            
            -- Timestamps
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            sent_at TIMESTAMP WITH TIME ZONE,
            completed_at TIMESTAMP WITH TIME ZONE
        )
    """)
    
    # Create index on batch_id for faster lookups
    op.execute("CREATE INDEX idx_notification_logs_batch_id ON notification_logs(batch_id)")
    op.execute("CREATE INDEX idx_notification_logs_created_by ON notification_logs(created_by)")
    op.execute("CREATE INDEX idx_notification_logs_type ON notification_logs(type)")
    op.execute("CREATE INDEX idx_notification_logs_created_at ON notification_logs(created_at)")


def downgrade() -> None:
    # Drop new table
    op.execute("DROP TABLE IF EXISTS notification_logs CASCADE")
    
    # Recreate old tables structure (if needed for rollback)
    op.execute("""
        CREATE TABLE notification_batches (
            id SERIAL PRIMARY KEY,
            batch_id VARCHAR UNIQUE NOT NULL,
            type VARCHAR NOT NULL,
            subject VARCHAR,
            total_recipients INTEGER NOT NULL,
            successful INTEGER DEFAULT 0 NOT NULL,
            failed INTEGER DEFAULT 0 NOT NULL,
            pending INTEGER DEFAULT 0 NOT NULL,
            total_cost VARCHAR DEFAULT '0' NOT NULL,
            provider VARCHAR NOT NULL,
            created_by INTEGER REFERENCES users(id),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            completed_at TIMESTAMP WITH TIME ZONE
        )
    """)
    
    op.execute("""
        CREATE TABLE notification_logs (
            id SERIAL PRIMARY KEY,
            batch_id VARCHAR REFERENCES notification_batches(batch_id) NOT NULL,
            recipient_type VARCHAR NOT NULL,
            recipient VARCHAR NOT NULL,
            subject VARCHAR,
            message VARCHAR NOT NULL,
            status VARCHAR NOT NULL,
            provider VARCHAR NOT NULL,
            provider_message_id VARCHAR,
            error_message VARCHAR,
            cost VARCHAR DEFAULT '0' NOT NULL,
            sent_at TIMESTAMP WITH TIME ZONE,
            delivered_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
        )
    """)
