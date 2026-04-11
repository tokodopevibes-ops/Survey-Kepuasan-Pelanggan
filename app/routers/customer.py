"""
Customer-facing router for survey display and submission.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db
from app.models import Questionnaire, Question, Respondent, Answer
from app.schemas import (
    QuestionnaireResponse,
    SurveySubmitRequest,
    SurveySubmitResponse
)

router = APIRouter(prefix="", tags=["customer"])
limiter = Limiter(key_func=get_remote_address)
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def list_questionnaires(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Display list of active questionnaires.

    Args:
        request: FastAPI Request object
        db: Database session

    Returns:
        HTMLResponse: Rendered questionnaire list template
    """
    questionnaires = db.query(Questionnaire).filter(
        Questionnaire.is_active == True
    ).order_by(Questionnaire.created_at.desc()).all()

    return templates.TemplateResponse(
        "customer/index.html",
        {
            "request": request,
            "questionnaires": questionnaires
        }
    )


@router.get("/survey/{questionnaire_id}", response_class=HTMLResponse)
def view_survey(
    questionnaire_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Display survey form for a specific questionnaire.

    Args:
        questionnaire_id: ID of the questionnaire
        request: FastAPI Request object
        db: Database session

    Returns:
        HTMLResponse: Rendered survey form

    Raises:
        HTTPException: If questionnaire not found or inactive
    """
    questionnaire = db.query(Questionnaire).filter(
        Questionnaire.id == questionnaire_id
    ).first()

    if not questionnaire:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Questionnaire not found"
        )

    if not questionnaire.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This questionnaire is not currently active"
        )

    # Get questions ordered by order_number
    questions = db.query(Question).filter(
        Question.questionnaire_id == questionnaire_id
    ).order_by(Question.order_number).all()

    if not questions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No questions found for this questionnaire"
        )

    return templates.TemplateResponse(
        "customer/survey.html",
        {
            "request": request,
            "questionnaire": questionnaire,
            "questions": questions
        }
    )


@router.post("/survey/submit", response_model=SurveySubmitResponse)
@limiter.limit("10/minute")
def submit_survey(
    submission: SurveySubmitRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Submit survey answers.

    Rate limited to 10 submissions per minute per IP.

    Args:
        submission: Survey submission data
        request: FastAPI Request object (for IP address)
        db: Database session

    Returns:
        SurveySubmitResponse: Submission confirmation

    Raises:
        HTTPException: If questionnaire not found or validation fails
    """
    # Verify questionnaire exists and is active
    questionnaire = db.query(Questionnaire).filter(
        Questionnaire.id == submission.questionnaire_id,
        Questionnaire.is_active == True
    ).first()

    if not questionnaire:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Questionnaire not found or inactive"
        )

    # Get client IP address
    client_ip = get_remote_address(request)

    # Create respondent
    respondent = Respondent(
        questionnaire_id=submission.questionnaire_id,
        name=submission.respondent_name,
        contact=submission.respondent_contact,
        ip_address=client_ip
    )
    db.add(respondent)
    db.flush()  # Get the ID without committing

    # Verify all questions belong to this questionnaire
    question_ids = {q.id for q in db.query(Question).filter(
        Question.questionnaire_id == submission.questionnaire_id
    ).all()}

    # Create answers
    for answer_data in submission.answers:
        if answer_data.question_id not in question_ids:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Question {answer_data.question_id} does not belong to this questionnaire"
            )

        answer = Answer(
            respondent_id=respondent.id,
            question_id=answer_data.question_id,
            rating_score=answer_data.rating_score,
            text_answer=answer_data.text_answer
        )
        db.add(answer)

    db.commit()

    return SurveySubmitResponse(
        respondent_id=respondent.id,
        message="Survey submitted successfully. Thank you for your feedback!"
    )


@router.get("/api/questionnaires", response_model=List[QuestionnaireResponse])
def get_questionnaires_api(db: Session = Depends(get_db)):
    """
    API endpoint to get list of active questionnaires.

    Args:
        db: Database session

    Returns:
        List[QuestionnaireResponse]: List of active questionnaires
    """
    questionnaires = db.query(Questionnaire).filter(
        Questionnaire.is_active == True
    ).order_by(Questionnaire.created_at.desc()).all()

    # Add response counts
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
