/**
 * Survey Form JavaScript
 * Handles form submission and validation for customer surveys
 */

// Store answers
const answers = [];

/**
 * Submit the survey form
 */
async function submitSurvey(event) {
    event.preventDefault();

    const submitBtn = document.getElementById('submitBtn');
    const errorMessage = document.getElementById('errorMessage');

    // Collect answers from all questions
    const collectedAnswers = [];
    const questionBlocks = document.querySelectorAll('.question-block');

    for (const block of questionBlocks) {
        const questionId = parseInt(block.dataset.questionId);
        const questionType = block.dataset.questionType;

        if (questionType === 'rating') {
            const checkedInput = block.querySelector(`input[name="q${questionId}"]:checked`);
            if (!checkedInput) {
                showError('Please answer all questions before submitting.');
                return;
            }
            collectedAnswers.push({
                question_id: questionId,
                rating_score: parseInt(checkedInput.value),
                text_answer: null
            });
        } else {
            const textarea = block.querySelector(`textarea[name="q${questionId}_text"]`);
            const value = textarea.value.trim();
            if (!value) {
                showError('Please answer all questions before submitting.');
                return;
            }
            collectedAnswers.push({
                question_id: questionId,
                rating_score: null,
                text_answer: value
            });
        }
    }

    // Collect respondent info (optional)
    const respondentName = document.getElementById('respondentName').value.trim() || null;
    const respondentContact = document.getElementById('respondentContact').value.trim() || null;
    const questionnaireId = parseInt(document.getElementById('questionnaireId').value);

    // Prepare submission data
    const submissionData = {
        questionnaire_id: questionnaireId,
        respondent_name: respondentName,
        respondent_contact: respondentContact,
        answers: collectedAnswers
    };

    // Disable submit button and show loading state
    submitBtn.disabled = true;
    submitBtn.textContent = 'Submitting...';
    errorMessage.style.display = 'none';

    try {
        const response = await fetch('/survey/submit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(submissionData)
        });

        const result = await response.json();

        if (response.ok) {
            // Hide form and show success message
            document.getElementById('surveyForm').style.display = 'none';
            document.getElementById('successMessage').style.display = 'block';
        } else {
            showError(result.detail || 'Failed to submit survey. Please try again.');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Submit Survey';
        }
    } catch (error) {
        showError('Network error. Please check your connection and try again.');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Submit Survey';
    }
}

/**
 * Show error message
 */
function showError(message) {
    const errorMessage = document.getElementById('errorMessage');
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';

    // Scroll to error message
    errorMessage.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/**
 * Add visual feedback to star ratings
 */
document.addEventListener('DOMContentLoaded', function() {
    // Enhance star rating with hover effects
    const starRatings = document.querySelectorAll('.star-rating');

    starRatings.forEach(rating => {
        const labels = rating.querySelectorAll('label');
        const inputs = rating.querySelectorAll('input');

        labels.forEach(label => {
            label.addEventListener('mouseenter', function() {
                // Highlight this star and all after it (in reverse order)
                const currentLabel = this;
                let found = false;
                labels.forEach(l => {
                    if (l === currentLabel) found = true;
                    if (found) {
                        l.style.color = '#ffdb58';
                    }
                });
            });

            label.addEventListener('mouseleave', function() {
                // Reset to actual checked state
                labels.forEach(l => {
                    l.style.color = '#ddd';
                });

                const checkedInput = rating.querySelector('input:checked');
                if (checkedInput) {
                    const checkedId = checkedInput.id;
                    let found = false;
                    labels.forEach(l => {
                        if (l.getAttribute('for') === checkedId) found = true;
                        if (found) {
                            l.style.color = '#ffc107';
                        }
                    });
                }
            });
        });
    });
});
