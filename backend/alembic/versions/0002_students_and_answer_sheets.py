"""students and answer sheets

Revision ID: 0002_students_and_answer_sheets
Revises: 0001_initial_foundation
Create Date: 2026-09-13
"""
import sqlalchemy as sa
from alembic import op

revision = "0002_students_and_answer_sheets"
down_revision = "0001_initial_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    answer_sheet_status = sa.Enum(
        "UPLOADED", "PROCESSING", "EXTRACTED", "EVALUATED", "REVIEW_REQUIRED", "COMPLETED", "FAILED",
        name="answersheetstatus", native_enum=False,
    )
    op.create_table(
        "students",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("exam_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("roll_number", sa.String(length=100), nullable=True),
        sa.Column("external_id", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["exam_id"], ["exams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("exam_id", "roll_number", name="uq_students_exam_roll_number"),
    )
    op.create_index("ix_students_exam_id", "students", ["exam_id"], unique=False)
    op.create_table(
        "answer_sheets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("exam_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("status", answer_sheet_status, nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["exam_id"], ["exams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stored_filename"),
    )
    op.create_index("ix_answer_sheets_exam_id", "answer_sheets", ["exam_id"], unique=False)
    op.create_index("ix_answer_sheets_student_id", "answer_sheets", ["student_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_answer_sheets_student_id", table_name="answer_sheets")
    op.drop_index("ix_answer_sheets_exam_id", table_name="answer_sheets")
    op.drop_table("answer_sheets")
    op.drop_index("ix_students_exam_id", table_name="students")
    op.drop_table("students")
