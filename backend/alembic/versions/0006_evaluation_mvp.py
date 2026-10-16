"""answer extraction and evaluation MVP

Revision ID: 0006_evaluation_mvp
Revises: 0005_provider_metadata
"""
import sqlalchemy as sa
from alembic import op

revision = "0006_evaluation_mvp"
down_revision = "0005_provider_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("answer_sheet_pages", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("answer_sheet_id", sa.Uuid(), sa.ForeignKey("answer_sheets.id", ondelete="CASCADE"), nullable=False), sa.Column("page_number", sa.Integer(), nullable=False), sa.Column("image_path", sa.String(500), nullable=False), sa.Column("extracted_text", sa.Text()), sa.Column("extraction_confidence", sa.Numeric(5, 4)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")), sa.CheckConstraint("page_number >= 1", name="ck_answer_sheet_pages_page_number_positive"))
    op.create_index("ix_answer_sheet_pages_answer_sheet_id", "answer_sheet_pages", ["answer_sheet_id"])
    op.create_table("student_answers", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("student_submission_id", sa.Uuid(), sa.ForeignKey("student_submissions.id", ondelete="CASCADE"), nullable=False), sa.Column("question_id", sa.Uuid(), sa.ForeignKey("questions.id", ondelete="SET NULL")), sa.Column("detected_question_number", sa.String(100)), sa.Column("answer_text", sa.Text(), nullable=False), sa.Column("page_numbers", sa.JSON(), nullable=False), sa.Column("extraction_confidence", sa.Numeric(5, 4)), sa.Column("mapping_confidence", sa.Numeric(5, 4)), sa.Column("manually_corrected", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("reviewed", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")))
    op.create_index("ix_student_answers_student_submission_id", "student_answers", ["student_submission_id"]); op.create_index("ix_student_answers_question_id", "student_answers", ["question_id"])
    op.create_table("evaluations", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("student_answer_id", sa.Uuid(), sa.ForeignKey("student_answers.id", ondelete="CASCADE"), nullable=False, unique=True), sa.Column("ai_marks", sa.Numeric(10, 2), nullable=False), sa.Column("manual_marks", sa.Numeric(10, 2)), sa.Column("final_marks", sa.Numeric(10, 2), nullable=False), sa.Column("maximum_marks", sa.Numeric(10, 2), nullable=False), sa.Column("confidence", sa.Numeric(5, 4), nullable=False), sa.Column("strengths", sa.JSON(), nullable=False), sa.Column("missing_points", sa.JSON(), nullable=False), sa.Column("feedback", sa.Text(), nullable=False), sa.Column("reasoning", sa.Text(), nullable=False), sa.Column("faculty_remarks", sa.Text()), sa.Column("status", sa.String(30), nullable=False), sa.Column("ai_provider", sa.String(50)), sa.Column("ai_model", sa.String(100)), sa.Column("prompt_version", sa.String(100)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")), sa.CheckConstraint("ai_marks >= 0", name="ck_evaluations_ai_marks_non_negative"), sa.CheckConstraint("manual_marks IS NULL OR manual_marks >= 0", name="ck_evaluations_manual_marks_non_negative"), sa.CheckConstraint("final_marks >= 0", name="ck_evaluations_final_marks_non_negative"))
    op.create_index("ix_evaluations_student_answer_id", "evaluations", ["student_answer_id"])
    op.create_table("evaluation_criteria", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("evaluation_id", sa.Uuid(), sa.ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False), sa.Column("rubric_criterion_id", sa.Uuid(), sa.ForeignKey("rubric_criteria.id", ondelete="SET NULL")), sa.Column("criterion_text_snapshot", sa.Text(), nullable=False), sa.Column("maximum_marks", sa.Numeric(10, 2), nullable=False), sa.Column("awarded_marks", sa.Numeric(10, 2), nullable=False), sa.Column("evidence", sa.Text(), nullable=False), sa.CheckConstraint("maximum_marks >= 0", name="ck_evaluation_criteria_maximum_marks_non_negative"), sa.CheckConstraint("awarded_marks >= 0", name="ck_evaluation_criteria_awarded_marks_non_negative"))
    op.create_index("ix_evaluation_criteria_evaluation_id", "evaluation_criteria", ["evaluation_id"])


def downgrade() -> None:
    op.drop_table("evaluation_criteria"); op.drop_table("evaluations"); op.drop_table("student_answers"); op.drop_table("answer_sheet_pages")
