"""add explicit student answer mapping status

Revision ID: 0008_mapping_status
Revises: 0007_student_answer_audit_fields
"""
import sqlalchemy as sa
from alembic import op

revision = "0008_mapping_status"
down_revision = "0007_student_answer_audit_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("student_answers", sa.Column("mapping_status", sa.String(30), nullable=False, server_default="unmapped"))
    op.execute("UPDATE student_answers SET mapping_status = CASE WHEN question_id IS NOT NULL THEN CASE WHEN manually_corrected THEN 'manual_mapped' ELSE 'auto_mapped' END ELSE 'unmapped' END")


def downgrade() -> None:
    op.drop_column("student_answers", "mapping_status")
