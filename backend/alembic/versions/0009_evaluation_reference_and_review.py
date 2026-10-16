"""evaluation reference data and faculty review hardening

Revision ID: 0009_evaluation_review
Revises: 0008_mapping_status
"""

import sqlalchemy as sa
from alembic import op


revision = "0009_evaluation_review"
down_revision = "0008_mapping_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("questions", sa.Column("key_concepts", sa.Text(), nullable=True))
    op.add_column("questions", sa.Column("acceptable_alternatives", sa.Text(), nullable=True))
    op.add_column("questions", sa.Column("reference_solution", sa.Text(), nullable=True))
    op.add_column("questions", sa.Column("marking_notes", sa.Text(), nullable=True))

    op.add_column("evaluations", sa.Column("evaluation_method", sa.String(40), nullable=False, server_default="overall_reference"))
    op.add_column("evaluations", sa.Column("warnings", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")))
    op.create_check_constraint("ck_evaluations_ai_marks_within_maximum", "evaluations", "ai_marks <= maximum_marks")
    op.create_check_constraint("ck_evaluations_manual_marks_within_maximum", "evaluations", "manual_marks IS NULL OR manual_marks <= maximum_marks")
    op.create_check_constraint("ck_evaluations_final_marks_within_maximum", "evaluations", "final_marks <= maximum_marks")

    op.add_column("evaluation_criteria", sa.Column("faculty_awarded_marks", sa.Numeric(10, 2), nullable=True))
    op.add_column("evaluation_criteria", sa.Column("status", sa.String(30), nullable=False, server_default="missing"))
    op.add_column("evaluation_criteria", sa.Column("reason", sa.Text(), nullable=False, server_default=""))
    op.create_check_constraint("ck_evaluation_criteria_awarded_marks_within_maximum", "evaluation_criteria", "awarded_marks <= maximum_marks")
    op.create_check_constraint("ck_evaluation_criteria_faculty_marks_non_negative", "evaluation_criteria", "faculty_awarded_marks IS NULL OR faculty_awarded_marks >= 0")
    op.create_check_constraint("ck_evaluation_criteria_faculty_marks_within_maximum", "evaluation_criteria", "faculty_awarded_marks IS NULL OR faculty_awarded_marks <= maximum_marks")

    op.add_column("student_submissions", sa.Column("evaluation_status", sa.String(30), nullable=False, server_default="not_started"))
    op.add_column("student_submissions", sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("student_submissions", "finalized_at")
    op.drop_column("student_submissions", "evaluation_status")
    op.drop_constraint("ck_evaluation_criteria_faculty_marks_within_maximum", "evaluation_criteria", type_="check")
    op.drop_constraint("ck_evaluation_criteria_faculty_marks_non_negative", "evaluation_criteria", type_="check")
    op.drop_constraint("ck_evaluation_criteria_awarded_marks_within_maximum", "evaluation_criteria", type_="check")
    op.drop_column("evaluation_criteria", "reason")
    op.drop_column("evaluation_criteria", "status")
    op.drop_column("evaluation_criteria", "faculty_awarded_marks")
    op.drop_constraint("ck_evaluations_final_marks_within_maximum", "evaluations", type_="check")
    op.drop_constraint("ck_evaluations_manual_marks_within_maximum", "evaluations", type_="check")
    op.drop_constraint("ck_evaluations_ai_marks_within_maximum", "evaluations", type_="check")
    op.drop_column("evaluations", "warnings")
    op.drop_column("evaluations", "evaluation_method")
    op.drop_column("questions", "marking_notes")
    op.drop_column("questions", "reference_solution")
    op.drop_column("questions", "acceptable_alternatives")
    op.drop_column("questions", "key_concepts")
