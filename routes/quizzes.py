"""AI Quiz Generator, Evaluation, and Attempt History routes."""

import json
from flask import Blueprint, render_template, request, jsonify
from database.db import db
from models.quiz import Quiz, QuizQuestion, QuizAttempt
from models.document import Document
from routes.auth import login_required, get_current_user
from services.quiz_service import quiz_service

quizzes_bp = Blueprint("quizzes", __name__)


@quizzes_bp.route("/quizzes")
@login_required
def quizzes_view():
    """Render the Quiz Hub view with generator and historical quizzes."""
    user = get_current_user()
    user_quizzes = (
        Quiz.query.filter_by(user_id=user.id)
        .order_by(Quiz.created_at.desc())
        .all()
    )
    user_docs = Document.query.filter_by(user_id=user.id).all()
    recent_attempts = (
        QuizAttempt.query.filter_by(user_id=user.id)
        .order_by(QuizAttempt.attempted_at.desc())
        .limit(10)
        .all()
    )
    return render_template(
        "quiz.html",
        user=user,
        quizzes=user_quizzes,
        documents=user_docs,
        recent_attempts=recent_attempts,
    )


@quizzes_bp.route("/quizzes/take/<int:quiz_id>")
@login_required
def take_quiz_view(quiz_id: int):
    """Render the interactive quiz taking interface."""
    user = get_current_user()
    quiz = Quiz.query.filter_by(id=quiz_id, user_id=user.id).first_or_404()
    return render_template("quiz_take.html", user=user, quiz=quiz)


@quizzes_bp.route("/quizzes/result/<int:attempt_id>")
@login_required
def quiz_result_view(attempt_id: int):
    """Render the score review and question explanation breakdown."""
    user = get_current_user()
    attempt = QuizAttempt.query.filter_by(id=attempt_id, user_id=user.id).first_or_404()
    return render_template("quiz_result.html", user=user, attempt=attempt)


@quizzes_bp.route("/api/quizzes", methods=["GET"])
@login_required
def list_quizzes():
    """List quizzes created by or for the current student."""
    user = get_current_user()
    quizzes = (
        Quiz.query.filter_by(user_id=user.id)
        .order_by(Quiz.created_at.desc())
        .all()
    )
    return jsonify({"quizzes": [q.to_dict() for q in quizzes]})


@quizzes_bp.route("/api/quizzes/<int:quiz_id>", methods=["GET"])
@login_required
def get_quiz(quiz_id: int):
    """Fetch quiz questions. Sensitive correct answers are hidden by default."""
    user = get_current_user()
    quiz = Quiz.query.filter_by(id=quiz_id, user_id=user.id).first()
    if not quiz:
        return jsonify({"error": "Quiz not found or unauthorized."}), 404

    # Hide answers while student is taking the quiz
    return jsonify({"quiz": quiz.to_dict(include_questions=True, hide_answers=True)})


@quizzes_bp.route("/api/quizzes/generate", methods=["POST"])
@login_required
def generate_quiz():
    """Generate a 4-choice multiple-choice quiz from a topic or an uploaded document."""
    user = get_current_user()
    data = request.get_json() or {}

    topic = data.get("topic", "").strip()
    document_id = data.get("document_id")
    num_questions = int(data.get("num_questions", 5))
    num_questions = max(3, min(num_questions, 10))  # limit between 3 and 10

    context_text = None
    doc_record = None

    if document_id:
        doc_record = Document.query.filter_by(id=document_id, user_id=user.id).first()
        if not doc_record:
            return jsonify({"error": "Selected document not found or unauthorized."}), 404
        context_text = doc_record.extracted_text
        if not topic:
            topic = doc_record.filename.rsplit(".", 1)[0].replace("_", " ").title()

    if not topic:
        return jsonify({"error": "Please provide a quiz topic or select an uploaded document."}), 400

    # Call AI quiz generation service
    generated_q_list = quiz_service.generate_quiz_content(
        topic=topic, context_text=context_text, num_questions=num_questions
    )

    if not generated_q_list:
        return jsonify({"error": "Could not generate questions. Please try another topic."}), 500

    # Create Quiz container
    quiz = Quiz(
        user_id=user.id,
        document_id=doc_record.id if doc_record else None,
        title=f"Quiz: {topic}",
        topic=topic,
    )
    db.session.add(quiz)
    db.session.flush()  # obtain quiz.id

    # Create questions with separate correct answers and explanations
    for q in generated_q_list:
        question = QuizQuestion(
            quiz_id=quiz.id,
            question_text=q["question"],
            option_a=q["options"]["A"],
            option_b=q["options"]["B"],
            option_c=q["options"]["C"],
            option_d=q["options"]["D"],
            correct_option=q["correct_option"],
            explanation=q.get("explanation", ""),
        )
        db.session.add(question)

    db.session.commit()

    return jsonify(
        {
            "message": f"Quiz '{quiz.title}' generated successfully!",
            "quiz": quiz.to_dict(include_questions=True, hide_answers=True),
        }
    ), 201


@quizzes_bp.route("/api/quizzes/submit", methods=["POST"])
@login_required
def submit_quiz():
    """Evaluate submitted quiz answers, compute score, save attempt record, and explain mistakes."""
    user = get_current_user()
    data = request.get_json() or {}

    quiz_id = data.get("quiz_id")
    submitted_answers = data.get("answers", {})  # dict of {question_id: 'A'}

    if not quiz_id:
        return jsonify({"error": "Missing quiz_id in submission."}), 400

    quiz = Quiz.query.filter_by(id=quiz_id, user_id=user.id).first()
    if not quiz:
        return jsonify({"error": "Quiz not found or unauthorized."}), 404

    # Run evaluation
    eval_result = quiz_service.evaluate_submission(
        questions=quiz.questions, submitted_answers=submitted_answers
    )

    # Save attempt
    attempt = QuizAttempt(
        quiz_id=quiz.id,
        user_id=user.id,
        score=eval_result["score_percentage"],
        total_questions=eval_result["total_questions"],
        correct_answers=eval_result["correct_answers"],
        user_answers_json=json.dumps(eval_result["details"]),
    )
    db.session.add(attempt)
    db.session.commit()

    return jsonify(
        {
            "message": "Quiz evaluated successfully!",
            "attempt_id": attempt.id,
            "score": attempt.score,
            "correct_answers": attempt.correct_answers,
            "total_questions": attempt.total_questions,
            "details": eval_result["details"],
        }
    )


@quizzes_bp.route("/api/quizzes/attempts/<int:attempt_id>", methods=["GET"])
@login_required
def get_attempt_details(attempt_id: int):
    """Retrieve details for a specific historical quiz attempt."""
    user = get_current_user()
    attempt = QuizAttempt.query.filter_by(id=attempt_id, user_id=user.id).first()
    if not attempt:
        return jsonify({"error": "Attempt record not found or unauthorized."}), 404
    return jsonify({"attempt": attempt.to_dict()})
