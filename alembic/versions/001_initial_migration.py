"""Initial migration

Revision ID: 001
Revises:
Create Date: 2026-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create admins table
    op.create_table(
        'admins',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username')
    )
    op.create_index(op.f('ix_admins_username'), 'admins', ['username'], unique=True)

    # Create questionnaires table
    op.create_table(
        'questionnaires',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_questionnaires_is_active'), 'questionnaires', ['is_active'], unique=False)

    # Create questions table
    op.create_table(
        'questions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('questionnaire_id', sa.Integer(), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('question_type', sa.Enum('rating', 'text', name='questiontype'), nullable=False),
        sa.Column('order_number', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['questionnaire_id'], ['questionnaires.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("question_type IN ('rating', 'text')", name='check_question_type')
    )
    op.create_index('idx_questionnaire_order', 'questions', ['questionnaire_id', 'order_number'], unique=False)
    op.create_index(op.f('ix_questions_questionnaire_id'), 'questions', ['questionnaire_id'], unique=False)

    # Create respondents table
    op.create_table(
        'respondents',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('questionnaire_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('contact', sa.String(length=100), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['questionnaire_id'], ['questionnaires.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_respondents_questionnaire_id'), 'respondents', ['questionnaire_id'], unique=False)
    op.create_index(op.f('ix_respondents_submitted_at'), 'respondents', ['submitted_at'], unique=False)

    # Create answers table
    op.create_table(
        'answers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('respondent_id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('rating_score', sa.Integer(), nullable=True),
        sa.Column('text_answer', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['respondent_id'], ['respondents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("rating_score BETWEEN 1 AND 5", name='check_rating_range')
    )
    op.create_index(op.f('ix_answers_question_id'), 'answers', ['question_id'], unique=False)
    op.create_index(op.f('ix_answers_respondent_id'), 'answers', ['respondent_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_answers_respondent_id'), table_name='answers')
    op.drop_index(op.f('ix_answers_question_id'), table_name='answers')
    op.drop_table('answers')

    op.drop_index(op.f('ix_respondents_submitted_at'), table_name='respondents')
    op.drop_index(op.f('ix_respondents_questionnaire_id'), table_name='respondents')
    op.drop_table('respondents')

    op.drop_index(op.f('ix_questions_questionnaire_id'), table_name='questions')
    op.drop_index('idx_questionnaire_order', table_name='questions')
    op.drop_table('questions')

    op.drop_index(op.f('ix_questionnaires_is_active'), table_name='questionnaires')
    op.drop_table('questionnaires')

    op.drop_index(op.f('ix_admins_username'), table_name='admins')
    op.drop_table('admins')
