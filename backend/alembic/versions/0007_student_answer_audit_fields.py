"""preserve extracted student answer audit fields

Revision ID: 0007_student_answer_audit_fields
Revises: 0006_evaluation_mvp
"""
import sqlalchemy as sa
from alembic import op

revision = "0007_student_answer_audit_fields"
down_revision = "0006_evaluation_mvp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("student_answers", sa.Column("raw_text", sa.Text()))
    op.add_column("student_answers", sa.Column("edited_text", sa.Text()))
    op.add_column("student_answers", sa.Column("extraction_status", sa.String(30), nullable=False, server_default="extracted"))
    op.add_column("student_answers", sa.Column("warnings", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    op.add_column("student_answers", sa.Column("extraction_method", sa.String(50)))
    op.add_column("student_answers", sa.Column("provider", sa.String(50)))
    op.add_column("student_answers", sa.Column("model_name", sa.String(100)))
    op.execute("UPDATE student_answers SET raw_text = answer_text WHERE raw_text IS NULL")


def downgrade() -> None:
    op.drop_column("student_answers", "model_name")
    op.drop_column("student_answers", "provider")
    op.drop_column("student_answers", "extraction_method")
    op.drop_column("student_answers", "warnings")
    op.drop_column("student_answers", "extraction_status")
    op.drop_column("student_answers", "edited_text")
    op.drop_column("student_answers", "raw_text")
