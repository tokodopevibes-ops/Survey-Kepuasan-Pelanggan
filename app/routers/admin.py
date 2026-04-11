"""
Admin router for questionnaire and question management,
dashboard, and results viewing.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Questionnaire, Question, Respondent, Answer, Admin
from app.schemas import (
    QuestionnaireCreate,
    QuestionnaireUpdate,
    QuestionnaireResponse,
    QuestionCreate,
    QuestionUpdate,
    QuestionResponse,
    SatisfactionStats,
    DashboardStats,
    QuestionnaireResults,
    QuestionResult,
    SatisfactionCategory
)
from app.routers.auth import require_admin

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")


# ============== Helper Functions ==============
def calculate_satisfaction_index(questionnaire_id: int, db: Session) -> tuple[float, SatisfactionCategory]:
    """
    Calculate satisfaction index for a questionnaire.

    Formula: (Total Score / Maximum Possible Score) × 100

    Categories:
    - 0-60%: Tidak Puas
    - 61-80%: Cukup
    - 81-100%: Puas

    Args:
        questionnaire_id: ID of the questionnaire
        db: Database session

    Returns:
        tuple[float, SatisfactionCategory]: (index value, category)
    """
    # Get all rating answers for this questionnaire
    result = db.query(
        func.count(Answer.id).label('count'),
        func.sum(Answer.rating_score).label('total_score')
    ).join(Question).filter(
        Question.questionnaire_id == questionnaire_id,
        Answer.rating_score.isnot(None)
    ).first()

    if not result or result.count == 0:
        return 0.0, SatisfactionCategory.TIDAK_PUAS

    total_score = result.total_score or 0
    max_score = result.count * 5  # Maximum rating is 5

    index = (total_score / max_score * 100) if max_score > 0 else 0

    # Determine category
    if index <= 60:
        category = SatisfactionCategory.TIDAK_PUAS
    elif index <= 80:
        category = SatisfactionCategory.CUKUP
    else:
        category = SatisfactionCategory.PUAS

    return round(index, 2), category


# ============== Dashboard ==============
@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin)
):
    """
    Get dashboard statistics overview.

    Args:
        db: Database session
        current_admin: Authenticated admin (from dependency)

    Returns:
        DashboardStats: Overview statistics
    """
    total_questionnaires = db.query(Questionnaire).count()
    active_questionnaires = db.query(Questionnaire).filter(
        Questionnaire.is_active == True
    ).count()
    total_respondents = db.query(Respondent).count()
    total_questions = db.query(Question).count()

    # Calculate average satisfaction across all questionnaires
    questionnaires = db.query(Questionnaire).all()
    satisfaction_sum = 0
    active_count = 0

    for q in questionnaires:
        if q.is_active:
            idx, _ = calculate_satisfaction_index(q.id, db)
            satisfaction_sum += idx
            active_count += 1

    average_satisfaction = (
        satisfaction_sum / active_count if active_count > 0 else 0
    )

    # Get recent responses
    recent_responses = db.query(Respondent).order_by(
        Respondent.submitted_at.desc()
    ).limit(10).all()

    return DashboardStats(
        total_questionnaires=total_questionnaires,
        active_questionnaires=active_questionnaires,
        total_respondents=total_respondents,
        total_questions=total_questions,
        average_satisfaction=round(average_satisfaction, 2),
        recent_responses=recent_responses
    )


# ============== Questionnaire Management ==============
@router.get("/questionnaires", response_model=List[QuestionnaireResponse])
def list_questionnaires(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin)
):
    """
    List all questionnaires.

    Args:
        db: Database session
        current_admin: Authenticated admin

    Returns:
        List[QuestionnaireResponse]: All questionnaires
    """
    questionnaires = db.query(Questionnaire).order_by(
        Questionnaire.created_at.desc()
    ).all()

    result = []
    for q in questionnaires:
        response_count = db.query(Respondent).filter(
            Respondent.questionnaire_id == q.id
        ).count()
        q_dict = QuestionnaireResponse.model_validate(q).model_copy()
        q_dict.response_count = response_count
        q_dict.question_count = len(q.questions)
        result.append(q_dict)

    return result


@router.post("/questionnaires", response_model=QuestionnaireResponse, status_code=status.HTTP_201_CREATED)
def create_questionnaire(
    questionnaire: QuestionnaireCreate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin)
):
    """
    Create a new questionnaire.

    Args:
        questionnaire: Questionnaire data
        db: Database session
        current_admin: Authenticated admin

    Returns:
        QuestionnaireResponse: Created questionnaire
    """
    db_questionnaire = Questionnaire(**questionnaire.model_dump())
    db.add(db_questionnaire)
    db.commit()
    db.refresh(db_questionnaire)

    return db_questionnaire


@router.get("/questionnaires/{questionnaire_id}", response_model=QuestionnaireResponse)
def get_questionnaire(
    questionnaire_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin)
):
    """
    Get a specific questionnaire.

    Args:
        questionnaire_id: ID of the questionnaire
        db: Database session
        current_admin: Authenticated admin

    Returns:
        QuestionnaireResponse: Questionnaire details

    Raises:
        HTTPException: If questionnaire not found
    """
    questionnaire = db.query(Questionnaire).filter(
        Questionnaire.id == questionnaire_id
    ).first()

    if not questionnaire:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Questionnaire not found"
        )

    response_count = db.query(Respondent).filter(
        Respondent.questionnaire_id == questionnaire_id
    ).count()

    result = QuestionnaireResponse.model_validate(questionnaire).model_copy()
    result.response_count = response_count
    result.question_count = len(questionnaire.questions)

    return result


@router.put("/questionnaires/{questionnaire_id}", response_model=QuestionnaireResponse)
def update_questionnaire(
    questionnaire_id: int,
    questionnaire: QuestionnaireUpdate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin)
):
    """
    Update a questionnaire.

    Args:
        questionnaire_id: ID of the questionnaire
        questionnaire: Updated data
        db: Database session
        current_admin: Authenticated admin

    Returns:
        QuestionnaireResponse: Updated questionnaire

    Raises:
        HTTPException: If questionnaire not found
    """
    db_questionnaire = db.query(Questionnaire).filter(
        Questionnaire.id == questionnaire_id
    ).first()

    if not db_questionnaire:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Questionnaire not found"
        )

    # Update only provided fields
    update_data = questionnaire.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_questionnaire, field, value)

    db.commit()
    db.refresh(db_questionnaire)

    return db_questionnaire


@router.delete("/questionnaires/{questionnaire_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_questionnaire(
    questionnaire_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin)
):
    """
    Delete a questionnaire.

    Args:
        questionnaire_id: ID of the questionnaire
        db: Database session
        current_admin: Authenticated admin

    Raises:
        HTTPException: If questionnaire not found
    """
    db_questionnaire = db.query(Questionnaire).filter(
        Questionnaire.id == questionnaire_id
    ).first()

    if not db_questionnaire:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Questionnaire not found"
        )

    db.delete(db_questionnaire)
    db.commit()

    return None


@router.post("/questionnaires/{questionnaire_id}/toggle", response_model=QuestionnaireResponse)
def toggle_questionnaire(
    questionnaire_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin)
):
    """
    Toggle questionnaire active status.

    Args:
        questionnaire_id: ID of the questionnaire
        db: Database session
        current_admin: Authenticated admin

    Returns:
        QuestionnaireResponse: Updated questionnaire

    Raises:
        HTTPException: If questionnaire not found
    """
    db_questionnaire = db.query(Questionnaire).filter(
        Questionnaire.id == questionnaire_id
    ).first()

    if not db_questionnaire:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Questionnaire not found"
        )

    db_questionnaire.is_active = not db_questionnaire.is_active
    db.commit()
    db.refresh(db_questionnaire)

    return db_questionnaire


# ============== Question Management ==============
@router.get("/questionnaires/{questionnaire_id}/questions", response_model=List[QuestionResponse])
def list_questions(
    questionnaire_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin)
):
    """
    List all questions for a questionnaire.

    Args:
        questionnaire_id: ID of the questionnaire
        db: Database session
        current_admin: Authenticated admin

    Returns:
        List[QuestionResponse]: Questions for the questionnaire

    Raises:
        HTTPException: If questionnaire not found
    """
    questionnaire = db.query(Questionnaire).filter(
        Questionnaire.id == questionnaire_id
    ).first()

    if not questionnaire:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Questionnaire not found"
        )

    questions = db.query(Question).filter(
        Question.questionnaire_id == questionnaire_id
    ).order_by(Question.order_number).all()

    return questions


@router.post("/questions", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
def create_question(
    question: QuestionCreate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin)
):
    """
    Add a new question to a questionnaire.

    Args:
        question: Question data
        db: Database session
        current_admin: Authenticated admin

    Returns:
        QuestionResponse: Created question

    Raises:
        HTTPException: If questionnaire not found
    """
    questionnaire = db.query(Questionnaire).filter(
        Questionnaire.id == question.questionnaire_id
    ).first()

    if not questionnaire:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Questionnaire not found"
        )

    db_question = Question(**question.model_dump())
    db.add(db_question)
    db.commit()
    db.refresh(db_question)

    return db_question


@router.put("/questions/{question_id}", response_model=QuestionResponse)
def update_question(
    question_id: int,
    question: QuestionUpdate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin)
):
    """
    Update a question.

    Args:
        question_id: ID of the question
        question: Updated data
        db: Database session
        current_admin: Authenticated admin

    Returns:
        QuestionResponse: Updated question

    Raises:
        HTTPException: If question not found
    """
    db_question = db.query(Question).filter(
        Question.id == question_id
    ).first()

    if not db_question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )

    update_data = question.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_question, field, value)

    db.commit()
    db.refresh(db_question)

    return db_question


@router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin)
):
    """
    Delete a question.

    Args:
        question_id: ID of the question
        db: Database session
        current_admin: Authenticated admin

    Raises:
        HTTPException: If question not found
    """
    db_question = db.query(Question).filter(
        Question.id == question_id
    ).first()

    if not db_question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )

    db.delete(db_question)
    db.commit()

    return None


# ============== Results & Analytics ==============
@router.get("/results/{questionnaire_id}", response_model=QuestionnaireResults)
def get_questionnaire_results(
    questionnaire_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin)
):
    """
    Get detailed results for a questionnaire.

    Args:
        questionnaire_id: ID of the questionnaire
        db: Database session
        current_admin: Authenticated admin

    Returns:
        QuestionnaireResults: Detailed results including satisfaction index

    Raises:
        HTTPException: If questionnaire not found
    """
    questionnaire = db.query(Questionnaire).filter(
        Questionnaire.id == questionnaire_id
    ).first()

    if not questionnaire:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Questionnaire not found"
        )

    # Calculate satisfaction index
    satisfaction_index, category = calculate_satisfaction_index(questionnaire_id, db)

    # Get total respondents
    total_respondents = db.query(Respondent).filter(
        Respondent.questionnaire_id == questionnaire_id
    ).count()

    # Get question results
    questions = db.query(Question).filter(
        Question.questionnaire_id == questionnaire_id
    ).order_by(Question.order_number).all()

    question_results = []
    for q in questions:
        if q.question_type == "rating":
            # Get rating stats
            rating_result = db.query(
                func.avg(Answer.rating_score).label('avg_rating')
            ).filter(
                Answer.question_id == q.id,
                Answer.rating_score.isnot(None)
            ).first()

            # Get distribution
            distribution_result = db.query(
                Answer.rating_score,
                func.count(Answer.id).label('count')
            ).filter(
                Answer.question_id == q.id,
                Answer.rating_score.isnot(None)
            ).group_by(Answer.rating_score).all()

            distribution = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
            for score, count in distribution_result:
                distribution[str(int(score))] = count

            question_results.append(QuestionResult(
                question_id=q.id,
                question_text=q.question_text,
                question_type=q.question_type,
                average_rating=round(rating_result.avg_rating, 2) if rating_result.avg_rating else None,
                rating_distribution=distribution
            ))
        else:
            # Get text responses
            text_answers = db.query(Answer.text_answer).filter(
                Answer.question_id == q.id,
                Answer.text_answer.isnot(None)
            ).limit(100).all()

            text_responses = [a.text_answer for a in text_answers if a.text_answer]

            question_results.append(QuestionResult(
                question_id=q.id,
                question_text=q.question_text,
                question_type=q.question_type,
                text_responses=text_responses
            ))

    return QuestionnaireResults(
        questionnaire=QuestionnaireResponse.model_validate(questionnaire),
        satisfaction_index=satisfaction_index,
        category=category,
        total_respondents=total_respondents,
        question_results=question_results
    )


@router.get("/satisfaction/{questionnaire_id}", response_model=SatisfactionStats)
def get_satisfaction_stats(
    questionnaire_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin)
):
    """
    Get satisfaction statistics for a questionnaire.

    Args:
        questionnaire_id: ID of the questionnaire
        db: Database session
        current_admin: Authenticated admin

    Returns:
        SatisfactionStats: Satisfaction statistics

    Raises:
        HTTPException: If questionnaire not found
    """
    questionnaire = db.query(Questionnaire).filter(
        Questionnaire.id == questionnaire_id
    ).first()

    if not questionnaire:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Questionnaire not found"
        )

    # Calculate satisfaction index
    satisfaction_index, category = calculate_satisfaction_index(questionnaire_id, db)

    # Get stats
    total_respondents = db.query(Respondent).filter(
        Respondent.questionnaire_id == questionnaire_id
    ).count()

    total_questions = db.query(Question).filter(
        Question.questionnaire_id == questionnaire_id
    ).count()

    # Get average rating
    avg_rating_result = db.query(
        func.avg(Answer.rating_score)
    ).join(Question).filter(
        Question.questionnaire_id == questionnaire_id,
        Answer.rating_score.isnot(None)
    ).first()

    average_rating = round(avg_rating_result[0], 2) if avg_rating_result[0] else None

    # Get rating distribution
    distribution_result = db.query(
        Answer.rating_score,
        func.count(Answer.id).label('count')
    ).join(Question).filter(
        Question.questionnaire_id == questionnaire_id,
        Answer.rating_score.isnot(None)
    ).group_by(Answer.rating_score).all()

    distribution = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
    for score, count in distribution_result:
        distribution[str(int(score))] = count

    return SatisfactionStats(
        questionnaire_id=questionnaire_id,
        questionnaire_title=questionnaire.title,
        total_respondents=total_respondents,
        total_questions=total_questions,
        satisfaction_index=satisfaction_index,
        category=category,
        average_rating=average_rating,
        rating_distribution=distribution
    )
