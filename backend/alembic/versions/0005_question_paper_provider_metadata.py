"""persist question-paper parser provider metadata

Revision ID: 0005_provider_metadata
Revises: 0004_question_papers
"""
import sqlalchemy as sa
from alembic import op

revision = "0005_provider_metadata"
down_revision = "0004_question_papers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("question_papers", sa.Column("parser_provider", sa.String(length=50), nullable=True))
    op.add_column("question_papers", sa.Column("parser_text_model", sa.String(length=100), nullable=True))
    op.add_column("question_papers", sa.Column("parser_vision_model", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("question_papers", "parser_vision_model")
    op.drop_column("question_papers", "parser_text_model")
    op.drop_column("question_papers", "parser_provider")
