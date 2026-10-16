"""initial foundation

Revision ID: 0001_initial_foundation
Revises:
Create Date: 2026-09-13
"""
import sqlalchemy as sa
from alembic import op

revision = "0001_initial_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    user_role = sa.Enum("EVALUATOR", name="userrole", native_enum=False)
    exam_status = sa.Enum("DRAFT", "CONFIGURED", "PROCESSING", "COMPLETED", name="examstatus", native_enum=False)
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "exams",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("class_name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("total_marks", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("status", exam_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("total_marks >= 0", name="ck_exams_total_marks_non_negative"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_exams_created_by_id", "exams", ["created_by_id"], unique=False)
    op.create_table(
        "questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("exam_id", sa.Uuid(), nullable=False),
        sa.Column("parent_question_id", sa.Uuid(), nullable=True),
        sa.Column("question_number", sa.String(length=100), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("model_answer", sa.Text(), nullable=True),
        sa.Column("maximum_marks", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("sequence_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("maximum_marks >= 0", name="ck_questions_maximum_marks_non_negative"),
        sa.ForeignKeyConstraint(["exam_id"], ["exams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_question_id"], ["questions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("exam_id", "question_number", name="uq_questions_exam_number"),
        sa.UniqueConstraint("exam_id", "sequence_order", name="uq_questions_exam_sequence"),
    )
    op.create_index("ix_questions_exam_id", "questions", ["exam_id"], unique=False)
    op.create_table(
        "rubric_criteria",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("criterion", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("maximum_marks", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("sequence_order", sa.Integer(), nullable=False),
        sa.CheckConstraint("maximum_marks >= 0", name="ck_rubric_criteria_maximum_marks_non_negative"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("question_id", "sequence_order", name="uq_rubric_criteria_question_sequence"),
    )
    op.create_index("ix_rubric_criteria_question_id", "rubric_criteria", ["question_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_rubric_criteria_question_id", table_name="rubric_criteria")
    op.drop_table("rubric_criteria")
    op.drop_index("ix_questions_exam_id", table_name="questions")
    op.drop_table("questions")
    op.drop_index("ix_exams_created_by_id", table_name="exams")
    op.drop_table("exams")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
