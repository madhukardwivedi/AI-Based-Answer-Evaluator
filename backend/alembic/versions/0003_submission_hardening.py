"""submission data-model hardening

Revision ID: 0003_submission_hardening
Revises: 0002_students_and_answer_sheets
Create Date: 2026-09-14
"""
import uuid

import sqlalchemy as sa
from alembic import op

revision = "0003_submission_hardening"
down_revision = "0002_students_and_answer_sheets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("answer_sheets_student_id_fkey", "answer_sheets", type_="foreignkey")
    op.alter_column("answer_sheets", "student_id", existing_type=sa.Uuid(), nullable=True)
    op.create_foreign_key("fk_answer_sheets_student_id", "answer_sheets", "students", ["student_id"], ["id"], ondelete="SET NULL")

    submission_status = sa.Enum("SUBMITTED", "REVIEW_REQUIRED", "COMPLETED", name="submissionstatus", native_enum=False)
    op.create_table(
        "student_submissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("exam_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("replaces_submission_id", sa.Uuid(), nullable=True),
        sa.Column("status", submission_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["exam_id"], ["exams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["replaces_submission_id"], ["student_submissions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_student_submissions_exam_id", "student_submissions", ["exam_id"], unique=False)
    op.create_index("ix_student_submissions_student_id", "student_submissions", ["student_id"], unique=False)

    op.create_table(
        "submission_files",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("submission_id", sa.Uuid(), nullable=False),
        sa.Column("answer_sheet_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_order", sa.Integer(), nullable=False),
        sa.Column("page_start", sa.Integer(), nullable=True),
        sa.Column("page_end", sa.Integer(), nullable=True),
        sa.Column("file_role", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("sequence_order >= 1", name="ck_submission_files_sequence_order_positive"),
        sa.CheckConstraint("page_start IS NULL OR page_start >= 1", name="ck_submission_files_page_start_positive"),
        sa.CheckConstraint("page_end IS NULL OR page_end >= 1", name="ck_submission_files_page_end_positive"),
        sa.CheckConstraint("page_start IS NULL OR page_end IS NULL OR page_end >= page_start", name="ck_submission_files_page_range"),
        sa.ForeignKeyConstraint(["submission_id"], ["student_submissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["answer_sheet_id"], ["answer_sheets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("submission_id", "answer_sheet_id", "page_start", "page_end", name="uq_submission_files_source_range"),
    )
    op.create_index("ix_submission_files_submission_id", "submission_files", ["submission_id"], unique=False)
    op.create_index("ix_submission_files_answer_sheet_id", "submission_files", ["answer_sheet_id"], unique=False)
    op.execute("CREATE UNIQUE INDEX uq_submission_files_source_range_normalized ON submission_files (submission_id, answer_sheet_id, COALESCE(page_start, -1), COALESCE(page_end, -1))")

    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, exam_id, student_id FROM answer_sheets WHERE student_id IS NOT NULL")).mappings()
    for row in rows:
        submission_id = uuid.uuid4()
        connection.execute(
            sa.text("INSERT INTO student_submissions (id, exam_id, student_id, status) VALUES (:id, :exam_id, :student_id, :status)"),
            {"id": submission_id, "exam_id": row["exam_id"], "student_id": row["student_id"], "status": "SUBMITTED"},
        )
        connection.execute(
            sa.text("INSERT INTO submission_files (id, submission_id, answer_sheet_id, sequence_order, file_role) VALUES (:id, :submission_id, :answer_sheet_id, 1, 'main')"),
            {"id": uuid.uuid4(), "submission_id": submission_id, "answer_sheet_id": row["id"]},
        )


def downgrade() -> None:
    op.drop_index("uq_submission_files_source_range_normalized", table_name="submission_files")
    op.drop_index("ix_submission_files_answer_sheet_id", table_name="submission_files")
    op.drop_index("ix_submission_files_submission_id", table_name="submission_files")
    op.drop_table("submission_files")
    op.drop_index("ix_student_submissions_student_id", table_name="student_submissions")
    op.drop_index("ix_student_submissions_exam_id", table_name="student_submissions")
    op.drop_table("student_submissions")
    op.drop_constraint("fk_answer_sheets_student_id", "answer_sheets", type_="foreignkey")
    op.alter_column("answer_sheets", "student_id", existing_type=sa.Uuid(), nullable=False)
    op.create_foreign_key("answer_sheets_student_id_fkey", "answer_sheets", "students", ["student_id"], ["id"], ondelete="CASCADE")
