"""Dashboard and analytics routes for StudyBuddy."""

from flask import Blueprint, render_template, jsonify, session
from routes.auth import login_required, get_current_user
from models.document import Document
from models.quiz import Quiz, QuizAttempt
from models.prediction import StudentPrediction
from services.recommendation_service import recommendation_service

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def index():
    """Root redirect."""
    if "user_id" in session:
        return render_template("dashboard.html", user=get_current_user())
    return render_template("login.html")


@dashboard_bp.route("/dashboard")
@login_required
def dashboard_view():
    """Main dashboard page."""
    user = get_current_user()
    return render_template("dashboard.html", user=user)


@dashboard_bp.route("/api/dashboard", methods=["GET"])
@login_required
def dashboard_stats():
    """API endpoint providing comprehensive analytics for Chart.js and summary cards."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 404

    # 1. Quizzes & attempts
    attempts = (
        QuizAttempt.query.filter_by(user_id=user.id)
        .order_by(QuizAttempt.attempted_at.asc())
        .all()
    )
    total_quizzes_created = Quiz.query.filter_by(user_id=user.id).count()
    total_attempts = len(attempts)

    avg_score = (
        round(sum(a.score for a in attempts) / total_attempts, 1)
        if total_attempts > 0
        else 0.0
    )

    # 2. Recent attempts (last 5)
    recent_attempts = [
        att.to_dict()
        for att in QuizAttempt.query.filter_by(user_id=user.id)
        .order_by(QuizAttempt.attempted_at.desc())
        .limit(5)
        .all()
    ]

    # 3. Documents
    total_docs = Document.query.filter_by(user_id=user.id).count()

    # 4. Latest ML prediction
    latest_pred = (
        StudentPrediction.query.filter_by(user_id=user.id)
        .order_by(StudentPrediction.created_at.desc())
        .first()
    )
    predicted_grade = latest_pred.to_dict() if latest_pred else None

    # 5. Topic-wise performance aggregation for Chart.js
    topic_data = {}
    for a in attempts:
        topic = a.quiz.topic if a.quiz and a.quiz.topic else "General"
        if topic not in topic_data:
            topic_data[topic] = []
        topic_data[topic].append(a.score)

    topic_labels = []
    topic_scores = []
    for topic, scores in topic_data.items():
        topic_labels.append(topic)
        topic_scores.append(round(sum(scores) / len(scores), 1))

    # 6. Score progression over time for Chart.js Line Chart
    timeline_labels = [a.attempted_at.strftime("%b %d %H:%M") for a in attempts]
    timeline_scores = [round(a.score, 1) for a in attempts]

    # 7. Recommendations
    rec_data = recommendation_service.generate_recommendations(user.id)

    return jsonify(
        {
            "user": user.to_dict(),
            "summary": {
                "total_quizzes_created": total_quizzes_created,
                "total_attempts": total_attempts,
                "average_score": avg_score,
                "total_documents": total_docs,
                "predicted_grade": predicted_grade["predicted_grade"]
                if predicted_grade
                else None,
                "performance_level": predicted_grade["performance_level"]
                if predicted_grade
                else "Not Predicted Yet",
            },
            "charts": {
                "topics": {
                    "labels": topic_labels,
                    "scores": topic_scores,
                },
                "timeline": {
                    "labels": timeline_labels,
                    "scores": timeline_scores,
                },
            },
            "recent_quizzes": recent_attempts,
            "recommendations": rec_data,
        }
    )
