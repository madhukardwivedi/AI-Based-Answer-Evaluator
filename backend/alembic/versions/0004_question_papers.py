"""question paper intelligence foundation

Revision ID: 0004_question_papers
Revises: 0003_submission_hardening
"""
import sqlalchemy as sa
from alembic import op

revision = "0004_question_papers"
down_revision = "0003_submission_hardening"
branch_labels = None
depends_on = None

def upgrade() -> None:
    status = sa.Enum("UPLOADED", "PARSING", "PARSED", "REVIEW_REQUIRED", "FAILED", name="questionpaperstatus", native_enum=False)
    op.create_table(
        "question_papers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("exam_id", sa.Uuid(), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("stored_filename", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("status", status, nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("parsed_at", sa.DateTime(timezone=True)),
        sa.Column("parsing_error", sa.Text()), sa.Column("parser_model", sa.String(100)), sa.Column("prompt_version", sa.String(100)), sa.Column("parse_result", sa.JSON()),
        sa.ForeignKeyConstraint(["exam_id"], ["exams.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("exam_id"), sa.UniqueConstraint("stored_filename"),
    )
    op.create_index("ix_question_papers_exam_id", "question_papers", ["exam_id"])

def downgrade() -> None:
    op.drop_index("ix_question_papers_exam_id", table_name="question_papers")
    op.drop_table("question_papers")
