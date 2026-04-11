"""
Pydantic schemas for request/response validation.
"""
from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field, field_validator


# ============== Enums ==============
class QuestionType(str, Enum):
    """Question type enumeration."""
    RATING = "rating"
    TEXT = "text"


class SatisfactionCategory(str, Enum):
    """Satisfaction category based on index."""
    TIDAK_PUAS = "Tidak Puas"  # 0-60%
    CUKUP = "Cukup"  # 61-80%
    PUAS = "Puas"  # 81-100%


# ============== Admin Schemas ==============
class AdminBase(BaseModel):
    """Base admin schema."""
    username: str = Field(..., min_length=3, max_length=50)


class AdminCreate(AdminBase):
    """Schema for creating an admin."""
    password: str = Field(..., min_length=6)


class AdminResponse(AdminBase):
    """Schema for admin response."""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============== Auth Schemas ==============
class LoginRequest(BaseModel):
    """Schema for login request."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Schema for login response."""
    access_token: str
    token_type: str = "bearer"
    username: str


# ============== Questionnaire Schemas ==============
class QuestionnaireBase(BaseModel):
    """Base questionnaire schema."""
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    is_active: bool = True


class QuestionnaireCreate(QuestionnaireBase):
    """Schema for creating a questionnaire."""
    pass


class QuestionnaireUpdate(QuestionnaireBase):
    """Schema for updating a questionnaire."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class QuestionnaireResponse(QuestionnaireBase):
    """Schema for questionnaire response."""
    id: int
    created_at: datetime
    updated_at: datetime
    question_count: int = 0
    response_count: int = 0

    class Config:
        from_attributes = True


# ============== Question Schemas ==============
class QuestionBase(BaseModel):
    """Base question schema."""
    question_text: str = Field(..., min_length=1)
    question_type: QuestionType = QuestionType.RATING
    order_number: int = Field(default=0, ge=0)


class QuestionCreate(QuestionBase):
    """Schema for creating a question."""
    questionnaire_id: int


class QuestionUpdate(BaseModel):
    """Schema for updating a question."""
    question_text: Optional[str] = Field(None, min_length=1)
    question_type: Optional[QuestionType] = None
    order_number: Optional[int] = Field(None, ge=0)


class QuestionResponse(QuestionBase):
    """Schema for question response."""
    id: int
    questionnaire_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============== Answer Schemas ==============
class AnswerBase(BaseModel):
    """Base answer schema."""
    question_id: int
    rating_score: Optional[int] = Field(None, ge=1, le=5)
    text_answer: Optional[str] = None

    @field_validator('text_answer')
    @classmethod
    def validate_answer(cls, v, info):
        """Ensure at least one type of answer is provided."""
        rating_score = info.data.get('rating_score')
        if v is None and rating_score is None:
            raise ValueError('Either rating_score or text_answer must be provided')
        return v


class AnswerCreate(AnswerBase):
    """Schema for creating an answer."""
    pass


class AnswerResponse(AnswerBase):
    """Schema for answer response."""
    id: int
    respondent_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============== Respondent Schemas ==============
class RespondentBase(BaseModel):
    """Base respondent schema."""
    name: Optional[str] = Field(None, max_length=100)
    contact: Optional[str] = Field(None, max_length=100)
    ip_address: Optional[str] = Field(None, max_length=45)


class RespondentCreate(RespondentBase):
    """Schema for creating a respondent."""
    questionnaire_id: int
    answers: List[AnswerCreate] = Field(..., min_length=1)


class RespondentResponse(RespondentBase):
    """Schema for respondent response."""
    id: int
    questionnaire_id: int
    submitted_at: datetime

    class Config:
        from_attributes = True


# ============== Survey Submission Schemas ==============
class SurveySubmitRequest(BaseModel):
    """Schema for survey submission."""
    questionnaire_id: int
    respondent_name: Optional[str] = Field(None, max_length=100)
    respondent_contact: Optional[str] = Field(None, max_length=100)
    answers: List[AnswerCreate] = Field(..., min_length=1)


class SurveySubmitResponse(BaseModel):
    """Schema for survey submission response."""
    respondent_id: int
    message: str = "Survey submitted successfully"


# ============== Statistics/Dashboard Schemas ==============
class SatisfactionStats(BaseModel):
    """Schema for satisfaction statistics."""
    questionnaire_id: int
    questionnaire_title: str
    total_respondents: int
    total_questions: int
    satisfaction_index: float
    category: SatisfactionCategory
    average_rating: Optional[float] = None
    rating_distribution: dict = Field(default_factory=lambda: {
        "1": 0, "2": 0, "3": 0, "4": 0, "5": 0
    })


class DashboardStats(BaseModel):
    """Schema for dashboard overview."""
    total_questionnaires: int
    active_questionnaires: int
    total_respondents: int
    total_questions: int
    average_satisfaction: float
    recent_responses: List[RespondentResponse]


# ============== Results Schemas ==============
class QuestionResult(BaseModel):
    """Schema for question results."""
    question_id: int
    question_text: str
    question_type: QuestionType
    average_rating: Optional[float] = None
    rating_distribution: dict = Field(default_factory=lambda: {
        "1": 0, "2": 0, "3": 0, "4": 0, "5": 0
    })
    text_responses: List[str] = Field(default_factory=list)


class QuestionnaireResults(BaseModel):
    """Schema for questionnaire results."""
    questionnaire: QuestionnaireResponse
    satisfaction_index: float
    category: SatisfactionCategory
    total_respondents: int
    question_results: List[QuestionResult]
