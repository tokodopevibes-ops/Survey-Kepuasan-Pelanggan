"""
SQLAlchemy ORM models for the Kuesioner application.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum,
    CheckConstraint, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class QuestionType(str, enum.Enum):
    """Question type enumeration."""
    RATING = "rating"
    TEXT = "text"


class Admin(Base):
    """
    Admin user model for authentication.
    """
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<Admin(id={self.id}, username='{self.username}')>"


class Questionnaire(Base):
    """
    Questionnaire model representing a survey.
    """
    __tablename__ = "questionnaires"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    questions = relationship(
        "Question",
        back_populates="questionnaire",
        cascade="all, delete-orphan",
        order_by="Question.order_number"
    )
    respondents = relationship(
        "Respondent",
        back_populates="questionnaire",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Questionnaire(id={self.id}, title='{self.title}', is_active={self.is_active})>"


class Question(Base):
    """
    Question model within a questionnaire.
    """
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    questionnaire_id = Column(
        Integer,
        ForeignKey("questionnaires.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    question_text = Column(Text, nullable=False)
    question_type = Column(
        Enum("rating", "text", name="questiontype"),
        nullable=False,
        default="rating"
    )
    order_number = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    questionnaire = relationship("Questionnaire", back_populates="questions")
    answers = relationship(
        "Answer",
        back_populates="question",
        cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (
        CheckConstraint("question_type IN ('rating', 'text')", name="check_question_type"),
        Index("idx_questionnaire_order", "questionnaire_id", "order_number"),
    )

    def __repr__(self) -> str:
        return f"<Question(id={self.id}, text='{self.question_text[:30]}...', type={self.question_type})>"


class Respondent(Base):
    """
    Respondent model representing someone who answered a questionnaire.
    """
    __tablename__ = "respondents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    questionnaire_id = Column(
        Integer,
        ForeignKey("questionnaires.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name = Column(String(100), nullable=True)
    contact = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    submitted_at = Column(DateTime, default=func.now(), nullable=False, index=True)

    # Relationships
    questionnaire = relationship("Questionnaire", back_populates="respondents")
    answers = relationship(
        "Answer",
        back_populates="respondent",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Respondent(id={self.id}, name='{self.name}', submitted_at={self.submitted_at})>"


class Answer(Base):
    """
    Answer model for a respondent's answer to a question.
    """
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    respondent_id = Column(
        Integer,
        ForeignKey("respondents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    question_id = Column(
        Integer,
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    rating_score = Column(Integer, nullable=True)  # 1-5 for rating questions
    text_answer = Column(Text, nullable=True)  # For text questions
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    respondent = relationship("Respondent", back_populates="answers")
    question = relationship("Question", back_populates="answers")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "(rating_score IS NULL AND text_answer IS NOT NULL) OR "
            "(rating_score IS NOT NULL AND text_answer IS NULL) OR "
            "(rating_score IS NOT NULL AND text_answer IS NOT NULL)",
            name="check_answer_exists"
        ),
        CheckConstraint("rating_score BETWEEN 1 AND 5", name="check_rating_range"),
    )

    def __repr__(self) -> str:
        if self.rating_score:
            return f"<Answer(id={self.id}, rating={self.rating_score})>"
        return f"<Answer(id={self.id}, text='{self.text_answer[:20]}...')>"
